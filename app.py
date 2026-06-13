from flask import Flask, request, redirect, jsonify, session
from flask_caching import Cache
from flask_cors import CORS
from pylti1p3.contrib.flask import FlaskMessageLaunch, FlaskOIDCLogin, FlaskRequest, FlaskCacheDataStorage
from pylti1p3.tool_config import ToolConfJsonFile
from pylti1p3.deep_link_resource import DeepLinkResource
import jwt
import uuid
import json
import os
import tempfile
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-in-production')

cache_config = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 7200}
app.config.from_mapping(cache_config)
cache = Cache(app)

def setup_keys():
    """Read RSA keys from environment variables and write to /app/keys/ directory."""
    os.makedirs('/app/keys', exist_ok=True)

    private_key = os.environ.get('SECRET_PRIVATE_KEY', '')
    public_key = os.environ.get('SECRET_PUBLIC_KEY', '')

    if private_key:
        with open('/app/keys/private.key', 'w') as f:
            f.write(private_key.replace('\\n', '\n'))

    if public_key:
        with open('/app/keys/public.key', 'w') as f:
            f.write(public_key.replace('\\n', '\n'))

setup_keys()

def build_tool_conf():
    with open('configs/tool.json') as f:
        raw = json.load(f)

    def resolve(value):
        if isinstance(value, str) and value.startswith('ENV:'):
            return os.environ.get(value[4:], '')
        if isinstance(value, list):
            return [resolve(v) for v in value]
        if isinstance(value, dict):
            return {k: resolve(v) for k, v in value.items()}
        return value

    resolved = resolve(raw)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(resolved, tmp)
    tmp.flush()
    return ToolConfJsonFile(tmp.name)

tool_conf = build_tool_conf()

attempts = {}

# ── LTI ENDPOINTS ──────────────────────────────────────────────────────

@app.route('/login/', methods=['GET', 'POST'])
def login():
    flask_request = FlaskRequest()
    target_link_uri = flask_request.get_param('target_link_uri')
    if not target_link_uri:
        raise Exception('Missing target_link_uri')
    launch_data_storage = FlaskCacheDataStorage(cache)
    oidc_login = FlaskOIDCLogin(flask_request, tool_conf,
                                launch_data_storage=launch_data_storage)
    return oidc_login.enable_check_cookies().redirect(target_link_uri)

@app.route('/launch/', methods=['POST'])
def launch():
    flask_request = FlaskRequest()
    launch_data_storage = FlaskCacheDataStorage(cache)
    message_launch = FlaskMessageLaunch(flask_request, tool_conf,
                                        launch_data_storage=launch_data_storage)

    if message_launch.is_deep_link_launch():
        launch_id = message_launch.get_launch_id()
        dashboard_url = os.environ.get(
            'INSTRUCTOR_DASHBOARD_URL',
            'https://sle-workbooks.github.io/instructor-dashboard.html'
        )
        return redirect(f"{dashboard_url}?deeplink_launch_id={launch_id}")

    message_launch_data = message_launch.get_launch_data()

    user_sub = message_launch_data.get('sub')
    context_id = message_launch_data.get(
        'https://purl.imsglobal.org/spec/lti/claim/context', {}
    ).get('id')
    resource_link_id = message_launch_data.get(
        'https://purl.imsglobal.org/spec/lti/claim/resource_link', {}
    ).get('id')

    lineitem_url = None
    if message_launch.has_ags():
        ags = message_launch.get_ags()
        lineitem_url = ags.get_lineitem()

    custom_params = message_launch_data.get(
        'https://purl.imsglobal.org/spec/lti/claim/custom', {}
    )
    workbook_url = custom_params.get('workbook_url', '')
    if not workbook_url or workbook_url.startswith('$'):
        workbook_url = os.environ.get('DEFAULT_WORKBOOK_URL', 'https://sle-workbooks.github.io/test')

    attempt_id = str(uuid.uuid4())
    token_payload = {
        'attempt_id': attempt_id,
        'user_sub': user_sub,
        'exp': datetime.utcnow() + timedelta(hours=2),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(token_payload, app.secret_key, algorithm='HS256')

    attempts[attempt_id] = {
        'attempt_id': attempt_id,
        'user_sub': user_sub,
        'context_id': context_id,
        'resource_link_id': resource_link_id,
        'lineitem_url': lineitem_url,
        'launch_id': message_launch.get_launch_id(),
        'token': token,
        'used': False,
        'created_at': datetime.utcnow().isoformat(),
        'score': None,
        'max_score': None
    }

    redirect_url = f"{workbook_url}?attempt_id={attempt_id}&token={token}"
    return redirect(redirect_url)

@app.route('/deeplink/submit', methods=['POST'])
def deeplink_submit():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    launch_id = data.get('deeplink_launch_id')
    assignments = data.get('assignments', [])
    if not launch_id or not assignments:
        return jsonify({"error": "Missing launch_id or assignments"}), 400
    try:
        flask_request = FlaskRequest()
        launch_data_storage = FlaskCacheDataStorage(cache)
        message_launch = FlaskMessageLaunch.from_cache(
            launch_id, flask_request, tool_conf,
            launch_data_storage=launch_data_storage
        )
        dl = message_launch.get_deep_link()
        resources = []
        for a in assignments:
            nums = a.get('exercises', [])
            label = a.get('label', '')
            nums_str = ', '.join(str(n) for n in nums)
            resource = DeepLinkResource()
            resource.set_url(a['workbook_url'])
            resource.set_title(f"L01 {label} — Exercise{'s' if len(nums) != 1 else ''} {nums_str}")
            resources.append(resource)
        form_html = dl.output_response_form(resources)
        return jsonify({"form_html": form_html})
    except Exception as e:
        print(f"Deep link error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/jwks/', methods=['GET'])
def jwks():
    return jsonify(tool_conf.get_jwks())

@app.route('/config/', methods=['GET'])
def config():
    base_url = 'https://sle-lti-server-950105557003.us-central1.run.app'
    config_data = {
        "title": "Spanish Learning Edge",
        "description": "ACTFL-aligned Spanish courseware with grade passback",
        "oidc_initiation_url": f"{base_url}/login/",
        "target_link_uri": f"{base_url}/launch/",
        "scopes": [
            "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
            "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly",
            "https://purl.imsglobal.org/spec/lti-ags/scope/score"
        ],
        "extensions": [
            {
                "platform": "canvas.instructure.com",
                "settings": {
                    "platform": "canvas.instructure.com",
                    "placements": [
                        {
                            "placement": "assignment_selection",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": f"{base_url}/launch/"
                        },
                        {
                            "placement": "assignment_selection",
                            "message_type": "LtiDeepLinkingRequest",
                            "target_link_uri": f"{base_url}/launch/"
                        }
                    ]
                },
                "privacy_level": "anonymous"
            }
        ],
        "public_jwk_url": f"{base_url}/jwks/",
        "custom_fields": {
            "workbook_url": "$ResourceLink.url"
        }
    }
    return jsonify(config_data)

@app.route('/config/canvas', methods=['GET'])
def config_canvas():
    base_url = 'https://sle-lti-server-950105557003.us-central1.run.app'
    config_data = {
        "title": "Spanish Learning Edge",
        "description": "ACTFL-aligned Spanish courseware with grade passback",
        "oidc_initiation_url": f"{base_url}/login/",
        "target_link_uri": f"{base_url}/launch/",
        "scopes": [
            "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
            "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly",
            "https://purl.imsglobal.org/spec/lti-ags/scope/score"
        ],
        "extensions": [
            {
                "platform": "canvas.instructure.com",
                "settings": {
                    "platform": "canvas.instructure.com",
                    "placements": [
                        {
                            "placement": "assignment_selection",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": f"{base_url}/launch/"
                        },
                        {
                            "placement": "assignment_selection",
                            "message_type": "LtiDeepLinkingRequest",
                            "target_link_uri": f"{base_url}/launch/"
                        }
                    ]
                },
                "privacy_level": "anonymous"
            }
        ],
        "public_jwk_url": f"{base_url}/jwks/",
        "custom_fields": {
            "workbook_url": "$ResourceLink.url"
        },
        "client_id": os.environ.get('CANVAS_CLIENT_ID', ''),
        "deployment_id": os.environ.get('CANVAS_DEPLOYMENT_ID', '')
    }
    return jsonify(config_data)

@app.route('/')
def health():
    return jsonify({"status": "ok", "service": "SLE LTI 1.3", "version": "1.0.0"})

# ── SLE API ─────────────────────────────────────────────────────────────

@app.route('/api/grade', methods=['POST'])
def receive_grade():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    attempt_id = data.get('attempt_id')
    token = data.get('token')
    score = data.get('score')
    max_score = data.get('max_score')
    block_id = data.get('block_id', 'unknown')

    if not all([attempt_id, token, score is not None, max_score]):
        return jsonify({"error": "Missing required fields"}), 400

    attempt = attempts.get(attempt_id)
    if not attempt:
        return jsonify({"error": "Invalid attempt_id"}), 404

    try:
        decoded = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        if decoded.get('attempt_id') != attempt_id:
            return jsonify({"error": "Token mismatch"}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    if attempt.get('used'):
        return jsonify({"error": "Token already used"}), 409

    attempts[attempt_id]['used'] = True
    attempts[attempt_id]['score'] = score
    attempts[attempt_id]['max_score'] = max_score

    lineitem_url = attempt.get('lineitem_url')
    if lineitem_url:
        try:
            launch_id = attempt.get('launch_id')
            flask_request = FlaskRequest()
            launch_data_storage = FlaskCacheDataStorage(cache)
            message_launch = FlaskMessageLaunch.from_cache(
                launch_id, flask_request, tool_conf,
                launch_data_storage=launch_data_storage
            )
            from pylti1p3.grade import Grade
            from pylti1p3.lineitem import LineItem
            ags = message_launch.get_ags()
            grade = Grade()
            grade.set_score_given(score)
            grade.set_score_maximum(max_score)
            grade.set_timestamp(datetime.utcnow().isoformat() + "Z")
            grade.set_activity_progress("Completed")
            grade.set_grading_progress("FullyGraded")
            grade.set_user_id(attempt['user_sub'])
            ags.put_grade(grade)
            return jsonify({"success": True, "passback": "sent",
                           "score": score, "max_score": max_score, "block_id": block_id})
        except Exception as e:
            print(f"AGS error: {e}")
            return jsonify({"success": True, "passback": "failed",
                           "error": str(e), "score": score}), 207
    else:
        return jsonify({"success": True, "passback": "no_lineitem",
                       "score": score, "max_score": max_score, "block_id": block_id})

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        "status": "ok",
        "attempts_in_memory": len(attempts),
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
