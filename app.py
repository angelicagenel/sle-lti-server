from flask import Flask, request, redirect, jsonify, session
import os, json, uuid, tempfile
from datetime import datetime, timedelta

# Minimal app so /ping is always reachable even if LTI imports fail
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-in-production')

@app.route('/ping')
def ping():
    return 'pong', 200

# LTI and optional imports — errors are caught below
_import_error = None
try:
    from flask_caching import Cache
    from flask_cors import CORS
    from pylti1p3.contrib.flask import FlaskMessageLaunch, FlaskOIDCLogin, FlaskRequest, FlaskCacheDataStorage
    from pylti1p3.tool_config import ToolConfJsonFile
    from pylti1p3.deep_link_resource import DeepLinkResource
    import jwt
    print("[startup] all imports OK", flush=True)
except Exception as _e:
    _import_error = str(_e)
    print(f"[startup] IMPORT ERROR: {_import_error}", flush=True)

if not _import_error:
    CORS(app, resources={
        r"/api/*":      {"origins": "*"},
        r"/deeplink/*": {"origins": "https://angelicagenel.github.io"},
    })
    cache_config = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 7200}
    app.config.from_mapping(cache_config)
    cache = Cache(app)

    from pylti1p3.contrib.flask.cookie import FlaskCookieService

    class CacheCookieService(FlaskCookieService):
        """
        Cookie service that mirrors every cookie into the server-side cache.
        When Moodle's iframe blocks browser cookies (Chrome SameSite policy),
        get_cookie() falls back to the cached value so state validation passes.
        """
        def __init__(self, request, cache_obj):
            super().__init__(request)
            self._server_cache = cache_obj

        def set_cookie(self, name, value, exp=3600):
            super().set_cookie(name, value, exp)
            self._server_cache.set(
                f'_ck_{self._get_key(name)}', value, timeout=exp or 3600
            )

        def get_cookie(self, name):
            val = super().get_cookie(name)
            if val is None:
                val = self._server_cache.get(f'_ck_{self._get_key(name)}')
                if val:
                    print(f"[cookie] cache fallback hit for {name}", flush=True)
            return val

    class NoCookieStorage:
        """
        LaunchDataStorage backed by server-side cache only.
        Returns None for get_session_cookie_name() so PyLTI1p3 never tries to
        read a session cookie (which would also be blocked in the iframe).
        Mirrors the _prepare_key() logic from LaunchDataStorage base class.
        """
        _prefix = "lti1p3-"
        _request = None
        _session_id = None

        def __init__(self, cache_obj):
            self._cache = cache_obj

        def set_request(self, request):
            self._request = request

        def get_session_cookie_name(self):
            return None  # skip session-id cookie requirement

        def get_session_id(self):
            return self._session_id

        def set_session_id(self, session_id):
            self._session_id = session_id

        def remove_session_id(self):
            self._session_id = None

        def can_set_keys_expiration(self):
            return True

        def _prepare_key(self, key):
            if self._session_id:
                if key.startswith(self._prefix):
                    key = key[len(self._prefix):]
                return self._prefix + self._session_id + "-" + key
            if not key.startswith(self._prefix):
                key = self._prefix + key
            return key

        def get_value(self, key):
            return self._cache.get(self._prepare_key(key))

        def set_value(self, key, value, exp=None):
            self._cache.set(self._prepare_key(key), value, exp or 86400)

        def check_value(self, key):
            return self._cache.get(self._prepare_key(key)) is not None

STARTUP_ERROR = _import_error

def setup_keys():
    os.makedirs('/app/keys', exist_ok=True)
    private_key = os.environ.get('SECRET_PRIVATE_KEY', '')
    public_key = os.environ.get('SECRET_PUBLIC_KEY', '')
    print(f"[startup] SECRET_PRIVATE_KEY present={bool(private_key)} len={len(private_key)}", flush=True)
    print(f"[startup] SECRET_PUBLIC_KEY  present={bool(public_key)}  len={len(public_key)}", flush=True)
    if private_key:
        with open('/app/keys/private.key', 'w') as f:
            f.write(private_key.replace('\\n', '\n'))
        print("[startup] private.key written", flush=True)
    if public_key:
        with open('/app/keys/public.key', 'w') as f:
            f.write(public_key.replace('\\n', '\n'))
        print("[startup] public.key written", flush=True)

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

    # Drop platform entries whose client_id resolved to an empty string.
    # This prevents PyLTI1p3 from failing with "missing client_id" when
    # optional integrations (Canvas, Blackboard) have no env vars set.
    filtered = {
        platform: [entry for entry in entries if entry.get('client_id')]
        for platform, entries in resolved.items()
    }
    filtered = {k: v for k, v in filtered.items() if v}

    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(filtered, tmp)
    tmp.flush()
    print(f"[startup] tool config written to {tmp.name}", flush=True)
    conf = ToolConfJsonFile(tmp.name)
    print("[startup] ToolConfJsonFile loaded OK", flush=True)
    return conf

tool_conf = None
if not STARTUP_ERROR:
    try:
        setup_keys()
        tool_conf = build_tool_conf()
        print("[startup] startup complete — tool_conf ready", flush=True)
    except Exception as _startup_exc:
        STARTUP_ERROR = str(_startup_exc)
        print(f"[startup] FATAL STARTUP ERROR: {STARTUP_ERROR}", flush=True)

attempts = {}

# ── LTI ENDPOINTS ───────────────────────────────────────────────────────

@app.route('/login/', methods=['GET', 'POST'])
def login():
    print("=== /login/ called ===", flush=True)
    if STARTUP_ERROR:
        return f"LTI server startup error: {STARTUP_ERROR}", 500
    try:
        flask_request = FlaskRequest()
        target_link_uri = flask_request.get_param('target_link_uri')
        if not target_link_uri:
            raise Exception('Missing target_link_uri')
        cookie_service = CacheCookieService(flask_request, cache)
        launch_data_storage = NoCookieStorage(cache)
        oidc_login = FlaskOIDCLogin(flask_request, tool_conf,
                                    cookie_service=cookie_service,
                                    launch_data_storage=launch_data_storage)
        return oidc_login.redirect(target_link_uri)
    except Exception as e:
        print(f"[login] ERROR: {e}", flush=True)
        return f"<pre>LTI login error: {e}</pre>", 500

@app.route('/launch/', methods=['POST'])
def launch():
    print("=== /launch/ called ===", flush=True)
    if STARTUP_ERROR:
        return f"LTI server startup error: {STARTUP_ERROR}", 500
    flask_request = FlaskRequest()
    cookie_service = CacheCookieService(flask_request, cache)
    launch_data_storage = NoCookieStorage(cache)
    try:
        message_launch = FlaskMessageLaunch(flask_request, tool_conf,
                                            cookie_service=cookie_service,
                                            launch_data_storage=launch_data_storage)
    except Exception as e:
        print(f"[launch] FlaskMessageLaunch failed: {e}", flush=True)
        return f"LTI launch error: {e}", 500

    launch_data = message_launch.get_launch_data()
    message_type = launch_data.get('https://purl.imsglobal.org/spec/lti/claim/message_type', 'MISSING')
    print(f"[launch] message_type={message_type}", flush=True)

    is_dl = message_launch.is_deep_link_launch()
    print(f"[launch] is_deep_link_launch={is_dl}", flush=True)

    if is_dl:
        launch_id = message_launch.get_launch_id()
        dashboard_url = os.environ.get(
            'INSTRUCTOR_DASHBOARD_URL',
            'https://angelicagenel.github.io/AI-worksheets/instructor-dashboard.html'
        )
        target = f"{dashboard_url}?deeplink_launch_id={launch_id}"
        print(f"[launch] deep link → redirecting to {target}", flush=True)
        # Use JS redirect so Moodle's iframe navigates correctly even if
        # the platform strips Location headers on cross-origin responses.
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0;url={target}">
<script>window.location.replace("{target}");</script>
</head><body>Loading instructor dashboard…</body></html>"""

    print("[launch] resource link launch – reading launch data", flush=True)
    message_launch_data = message_launch.get_launch_data()

    user_sub = message_launch_data.get('sub')
    context_id = message_launch_data.get(
        'https://purl.imsglobal.org/spec/lti/claim/context', {}
    ).get('id')
    resource_link_id = message_launch_data.get(
        'https://purl.imsglobal.org/spec/lti/claim/resource_link', {}
    ).get('id')

    lineitem_url = None
    has_ags = message_launch.has_ags()
    print(f"[launch] has_ags={has_ags}", flush=True)
    if has_ags:
        ags = message_launch.get_ags()
        lineitem_url = ags.get_lineitem()
        print(f"[launch] lineitem_url={lineitem_url}", flush=True)
    else:
        ags_claim = message_launch_data.get('https://purl.imsglobal.org/spec/lti-ags/claim/endpoint')
        print(f"[launch] AGS claim from JWT={ags_claim}", flush=True)

    custom_params = message_launch_data.get(
        'https://purl.imsglobal.org/spec/lti/claim/custom', {}
    )
    workbook_url = custom_params.get('workbook_url', '')
    if not workbook_url or workbook_url.startswith('$'):
        workbook_url = os.environ.get('DEFAULT_WORKBOOK_URL', 'https://sle-lti-server-950105557003.us-central1.run.app/no-assignment/')

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

    separator = '&' if '?' in workbook_url else '?'
    redirect_url = f"{workbook_url}{separator}attempt_id={attempt_id}&token={token}"
    return redirect(redirect_url)

@app.route('/deeplink/submit', methods=['POST'])
def deeplink_submit():
    print("=== /deeplink/submit called ===", flush=True)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    launch_id = data.get('deeplink_launch_id')
    assignments = data.get('assignments', [])
    print(f"[deeplink/submit] launch_id={launch_id} assignments={len(assignments)}", flush=True)
    if not launch_id or not assignments:
        return jsonify({"error": "Missing launch_id or assignments"}), 400
    try:
        flask_request = FlaskRequest()
        launch_data_storage = NoCookieStorage(cache)
        message_launch = FlaskMessageLaunch.from_cache(
            launch_id, flask_request, tool_conf,
            launch_data_storage=launch_data_storage
        )
        dl = message_launch.get_deep_link()
        resources = []
        lti_launch_url = os.environ.get(
            'LTI_LAUNCH_URL',
            'https://sle-lti-server-950105557003.us-central1.run.app/launch/'
        )
        for a in assignments:
            nums = a.get('exercises', [])
            label = a.get('label', '')
            nums_str = ', '.join(str(n) for n in nums)
            title = f"L01 {label} — Exercise{'s' if len(nums) != 1 else ''} {nums_str}"
            resource = DeepLinkResource()
            resource.set_url(lti_launch_url)
            resource.set_custom_params({'workbook_url': a['workbook_url']})
            resource.set_title(title)
            from pylti1p3.lineitem import LineItem
            lineitem = LineItem()
            lineitem.set_score_maximum(100)
            lineitem.set_label(title)
            lineitem.set_resource_id(f"sle-{label.lower().replace(' ', '-')}")
            resource.set_lineitem(lineitem)
            resources.append(resource)
        form_html = dl.output_response_form(resources)
        print(f"[deeplink/submit] form_html generated, length={len(form_html)}", flush=True)
        return jsonify({"form_html": form_html})
    except Exception as e:
        print(f"[deeplink/submit] error: {e}", flush=True)
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

@app.route('/no-assignment/')
def no_assignment():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Not Configured · Spanish Learning Edge</title>
<style>
  body { font-family: sans-serif; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; margin: 0;
         background: #f0f3f3; }
  .box { background: #fff; border-radius: 12px; padding: 40px 48px;
         text-align: center; max-width: 420px;
         box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  .icon { font-size: 2.5rem; margin-bottom: 16px; }
  h1 { font-size: 1.1rem; color: #2f3437; margin-bottom: 10px; }
  p  { font-size: .9rem; color: #5a6470; line-height: 1.6; margin: 0; }
</style>
</head>
<body>
<div class="box">
  <div class="icon">📋</div>
  <h1>No assignment configured</h1>
  <p>Your instructor hasn't set up this activity yet.<br>
     Please check back later or contact your instructor.</p>
</div>
</body>
</html>""", 200

@app.route('/')
def health():
    if STARTUP_ERROR:
        return jsonify({"status": "error", "startup_error": STARTUP_ERROR}), 500
    return jsonify({"status": "ok", "service": "SLE LTI 1.3", "version": "1.0.0"})

# ── SLE API ────────────────────────────────────────────────────────────

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
    print(f"[grade] attempt_id={attempt_id} score={score}/{max_score} lineitem_url={lineitem_url}", flush=True)
    if lineitem_url:
        try:
            launch_id = attempt.get('launch_id')
            print(f"[grade] restoring launch_id={launch_id}", flush=True)
            flask_request = FlaskRequest()
            launch_data_storage = NoCookieStorage(cache)
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
            print(f"[grade] AGS passback SUCCESS score={score}/{max_score}", flush=True)
            return jsonify({"success": True, "passback": "sent",
                           "score": score, "max_score": max_score, "block_id": block_id})
        except Exception as e:
            print(f"[grade] AGS ERROR: {e}", flush=True)
            return jsonify({"success": True, "passback": "failed",
                           "error": str(e), "score": score}), 207
    else:
        print(f"[grade] no lineitem_url — skipping passback", flush=True)
        return jsonify({"success": True, "passback": "no_lineitem",
                       "score": score, "max_score": max_score, "block_id": block_id})

@app.route('/api/health', methods=['GET'])
def api_health():
    if STARTUP_ERROR:
        return jsonify({
            "status": "error",
            "startup_error": STARTUP_ERROR,
            "timestamp": datetime.utcnow().isoformat()
        }), 500
    return jsonify({
        "status": "ok",
        "attempts_in_memory": len(attempts),
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
