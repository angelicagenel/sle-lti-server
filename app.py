from flask import Flask, request, redirect, jsonify, session
from flask_caching import Cache
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
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-in-production')

# CORRECCIÓN 1: Inicializar flask-caching explícitamente con SimpleCache
cache_config = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 7200}
app.config.from_mapping(cache_config)
cache = Cache(app)

def setup_keys():
    """Read RSA keys from environment variables and write to keys/ directory."""
    os.makedirs('keys', exist_ok=True)

    private_key = os.environ.get('SECRET_PRIVATE_KEY', '')
    public_key = os.environ.get('SECRET_PUBLIC_KEY', '')

    if private_key:
        with open('keys/private.key', 'w') as f:
            f.write(private_key.replace('\\n', '\n'))

    if public_key:
        with open('keys/public.key', 'w') as f:
            f.write(public_key.replace('\\n', '\n'))

setup_keys()

# Tool config desde JSON
tool_conf = ToolConfJsonFile('configs/tool.json')

# Storage en memoria para MVP
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
    workbook_url = custom_params.get('workbook_url',
        os.environ.get('DEFAULT_WORKBOOK_URL', 'https://sle-workbooks.github.io/test'))

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

@app.route('/jwks/', methods=['GET'])
def jwks():
    return jsonify(tool_conf.get_jwks())

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
            ags = message_launch.get_ags()
            score_obj = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "scoreGiven": score,
                "scoreMaximum": max_score,
                "activityProgress": "Completed",
                "gradingProgress": "FullyGraded",
                "userId": attempt['user_sub']
            }
            ags.put_grade(score_obj)
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
