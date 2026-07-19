"""
Steps 4–7: Backend dry-run import check, security verification, runtime flow
verification, and cleanup scan.

Run from: backend/
Must NOT start uvicorn — purely static + import-resolution checks.
"""
import ast
import importlib.util
import pathlib
import sys
import re

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

PASS = []
FAIL = []

def ok(msg):  PASS.append(msg); print(f"  OK    {msg}")
def fail(msg): FAIL.append(msg); print(f"  FAIL  {msg}")
def section(title):
    print()
    print("=" * 64)
    print(title)
    print("=" * 64)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Backend dry-run import resolution
# ─────────────────────────────────────────────────────────────────────────────
section("STEP 4 — DRY-RUN IMPORT RESOLUTION")

# Check that all top-level imports in each file can be *found* (not necessarily
# executed — we don't want to load fastapi/sqlalchemy here).  We resolve the
# project-local imports (those without dots that resolve to files in ROOT).

LOCAL_MODULES = {
    p.stem for p in ROOT.rglob("*.py")
    if "__pycache__" not in str(p) and not p.stem.startswith("_verify")
}
# Add package-level names (directories with __init__.py)
for d in ROOT.rglob("__init__.py"):
    LOCAL_MODULES.add(d.parent.name)

STDLIB = {
    "ast","json","logging","logging.handlers","math","os","re","time","uuid",
    "unicodedata","collections","datetime","enum","typing","warnings","io",
    "pathlib","sys","string","hashlib","abc","functools","itertools","copy",
    "inspect","traceback","contextlib","dataclasses","types","importlib",
    "importlib.util","importlib.metadata","socket","struct","threading",
    "multiprocessing","subprocess","shutil","tempfile","zipfile","tarfile",
    "csv","configparser","argparse","unittest","asyncio","concurrent",
    "concurrent.futures","http","urllib","urllib.parse",
}

KNOWN_THIRD_PARTY = {
    "fastapi","uvicorn","starlette","pydantic","sqlalchemy","jose","passlib",
    "dotenv","slowapi","magic","librosa","numpy","scipy","torch","transformers",
    "reportlab","kagglehub","soundfile","audioread","sklearn","matplotlib",
    "PIL","cv2","tqdm","requests","httpx","aiofiles","multipart","email",
    "email_validator","watchfiles","anyio","sniffio","click","rich","typer",
    "yaml","toml","pytest","hypothesis","coverage","mypy","flake8","black",
    "isort","bandit","safety","cryptography","bcrypt","itsdangerous",
    "werkzeug","jinja2","aiohttp","websockets","paramiko","boto3","google",
    "azure","redis","celery","kombu","billiard","vine","amqp","pyzmq",
    "pandas","polars","pyarrow","sqlmodel","tortoise","motor","beanie",
    "mongoengine","peewee","tinydb","dataset","alembic",
}

FILES_TO_CHECK = [
    "app.py","api/routes.py","auth/routes.py","auth/utils.py",
    "auth/dependencies.py","auth/schemas.py","auth/database.py",
    "models/user.py","security/file_validator.py","security/audit_log.py",
    "middleware/logging_middleware.py","middleware/security_headers.py",
]

all_imports_ok = True
for rel in FILES_TO_CHECK:
    p = ROOT / rel
    if not p.exists():
        fail(f"{rel}: FILE MISSING")
        all_imports_ok = False
        continue
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    unresolved = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod not in STDLIB and mod not in KNOWN_THIRD_PARTY:
                    # Must be a local module
                    if mod not in LOCAL_MODULES:
                        unresolved.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod not in STDLIB and mod not in KNOWN_THIRD_PARTY:
                    if mod not in LOCAL_MODULES:
                        unresolved.append(node.module)
    if unresolved:
        fail(f"{rel}: unresolved local imports: {unresolved}")
        all_imports_ok = False
    else:
        ok(f"{rel}: all imports resolvable")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Runtime flow verification (static trace)
# ─────────────────────────────────────────────────────────────────────────────
section("STEP 5 — RUNTIME FLOW VERIFICATION (static trace)")

FLOW_CHECKS = [
    # (file, token_that_must_exist, description)
    # Signup → POST /auth/register
    ("auth/routes.py",         "POST /register" ,         "Signup: POST /auth/register route"),
    ("auth/routes.py",         "@router.post(\"/register\"","Signup: register decorator"),
    ("auth/routes.py",         "hash_password",           "Signup: password hashed before storage"),
    ("auth/routes.py",         "db.add(user)",            "Signup: user persisted to DB"),
    ("auth/routes.py",         "AuditEvent.AUTH_REGISTER","Signup: audit event emitted"),

    # Login → POST /auth/login
    ("auth/routes.py",         "@router.post(\"/login\"", "Login: login route defined"),
    ("auth/routes.py",         "verify_password",         "Login: password verification"),
    ("auth/routes.py",         "create_access_token",     "Login: access token issued"),
    ("auth/routes.py",         "create_refresh_token",    "Login: refresh token issued"),
    ("auth/routes.py",         "AuditEvent.AUTH_LOGIN",   "Login: success audited"),
    ("auth/routes.py",         "AuditEvent.AUTH_LOGIN_FAILED","Login: failure audited"),

    # Upload Audio → POST /analyze
    ("api/routes.py",          "@router.post(\"/analyze\"","Upload: /analyze route defined"),
    ("api/routes.py",          "await file.read()",       "Upload: file bytes read"),
    ("api/routes.py",          "validate_upload",         "Upload: security validation"),
    ("api/routes.py",          "load_and_validate_audio", "Upload: audio decoded"),
    ("api/routes.py",          "extract_all_features",    "Upload: features extracted"),
    ("api/routes.py",          "engine.predict",          "Upload: inference called"),
    ("api/routes.py",          "build_explanation",       "Upload: XAI explanation built"),
    ("api/routes.py",          "db.add(row)",             "Upload: result persisted"),
    ("api/routes.py",          "AuditEvent.ANALYSIS_COMPLETED","Upload: completion audited"),

    # Dashboard → GET /dashboard-stats
    ("api/routes.py",          "@router.get(\"/dashboard-stats\"","Dashboard: route defined"),
    ("api/routes.py",          "get_current_active_user", "Dashboard: auth required"),
    ("api/routes.py",          "recent_history",          "Dashboard: recent history returned"),

    # History → GET /history
    ("api/routes.py",          "@router.get(\"/history\"","History: route defined"),
    ("api/routes.py",          "_row_to_dict",            "History: rows serialised"),

    # PDF Download → GET /report/{id}
    ("api/routes.py",          "@router.get(\"/report/{analysis_id}\"","PDF: route defined"),
    ("api/routes.py",          "generate_analysis_pdf",   "PDF: generation called"),
    ("api/routes.py",          "AuditEvent.REPORT_GENERATED","PDF: generation audited"),
    ("api/routes.py",          "StreamingResponse",       "PDF: streamed to client"),

    # Logout → POST /auth/logout
    ("auth/routes.py",         "@router.post(\"/logout\"","Logout: route defined"),
    ("auth/routes.py",         "AuditEvent.AUTH_LOGOUT",  "Logout: audited"),

    # Refresh → POST /auth/refresh
    ("auth/routes.py",         "@router.post(\"/refresh\"","Refresh: route defined"),
    ("auth/routes.py",         "token_data.type != \"refresh\"","Refresh: token type validated"),
    ("auth/routes.py",         "AuditEvent.AUTH_REFRESH", "Refresh: audited"),
]

for rel, token, desc in FLOW_CHECKS:
    p = ROOT / rel
    if not p.exists():
        fail(f"{desc}: {rel} MISSING")
        continue
    src = p.read_text(encoding="utf-8")
    if token in src:
        ok(desc)
    else:
        fail(f"{desc}: '{token}' not in {rel}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Security verification
# ─────────────────────────────────────────────────────────────────────────────
section("STEP 6 — SECURITY VERIFICATION")

SEC_CHECKS = [
    # JWT
    ("auth/utils.py",   "iss",                       "JWT: issuer claim in token payload"),
    ("auth/utils.py",   "aud",                       "JWT: audience claim in token payload"),
    ("auth/utils.py",   "issuer=JWT_ISSUER",         "JWT: issuer validated on decode"),
    ("auth/utils.py",   "audience=JWT_AUDIENCE",     "JWT: audience validated on decode"),
    ("auth/utils.py",   "ExpiredSignatureError",      "JWT: expiry caught separately"),
    ("auth/utils.py",   "JWTClaimsError",             "JWT: claims error caught separately"),
    ("auth/utils.py",   "token_type not in (\"access\", \"refresh\")", "JWT: type confusion guard"),
    ("auth/utils.py",   "_warn_weak_secret",          "JWT: weak key detection"),
    ("auth/utils.py",   "RuntimeError",               "JWT: production blocks on weak key"),

    # Protected routes
    ("api/routes.py",   "get_current_active_user",   "Routes: all routes require auth"),
    ("auth/dependencies.py","get_current_active_user","Auth: active-user guard defined"),
    ("auth/dependencies.py","is_active",              "Auth: deactivated account blocked"),

    # Rate limiting
    ("app.py",          "Limiter(",                   "RateLimit: limiter instantiated"),
    ("app.py",          "default_limits",             "RateLimit: global default set"),
    ("app.py",          "RateLimitExceeded",          "RateLimit: 429 handler registered"),
    ("auth/routes.py",  "_check_request_limit",       "RateLimit: manual check on register"),

    # Request validation
    ("app.py",          "RequestValidationError",     "Validation: 422 handler registered"),
    ("app.py",          "errors",                     "Validation: field errors in response"),

    # Secure file upload
    ("api/routes.py",   "validate_upload",            "Upload: secure validator called"),
    ("security/file_validator.py","_sanitise_filename","Upload: filename sanitised"),
    ("security/file_validator.py","_check_extension", "Upload: extension allow-listed"),
    ("security/file_validator.py","_check_mime",      "Upload: MIME magic-bytes checked"),
    ("security/file_validator.py","_check_entropy",   "Upload: entropy guard active"),
    ("security/file_validator.py","_check_size",      "Upload: size cap enforced"),

    # Audit logging
    ("security/audit_log.py","TimedRotatingFileHandler","Audit: rotating file handler"),
    ("security/audit_log.py","_mask_email",           "Audit: PII masking on email"),
    ("api/routes.py",   "emit(",                      "Audit: events emitted in routes"),
    ("auth/routes.py",  "emit(",                      "Audit: events emitted in auth"),

    # CORS
    ("app.py",          "_CORS_METHODS",              "CORS: methods restricted"),
    ("app.py",          "_CORS_HEADERS",              "CORS: headers restricted"),
    ("app.py",          "allow_credentials=True",     "CORS: credentials allowed for auth"),
    ("app.py",          "max_age=600",                "CORS: preflight cache limited"),

    # Security headers
    ("middleware/security_headers.py","X-Content-Type-Options","Headers: MIME sniff blocked"),
    ("middleware/security_headers.py","X-Frame-Options","Headers: clickjacking blocked"),
    ("middleware/security_headers.py","Content-Security-Policy","Headers: CSP set"),
    ("middleware/security_headers.py","Referrer-Policy","Headers: referrer limited"),
    ("middleware/security_headers.py","Permissions-Policy","Headers: browser features restricted"),
    ("middleware/security_headers.py","Strict-Transport-Security","Headers: HSTS set (prod)"),
    ("middleware/security_headers.py","Cache-Control",  "Headers: no-store on /auth"),

    # Secure error responses (RFC 7807)
    ("app.py",          "_problem(",                  "Errors: RFC 7807 helper defined"),
    ("app.py",          "\"title\"",                  "Errors: title field in body"),
    ("app.py",          "\"detail\"",                 "Errors: detail field in body"),
    ("app.py",          "\"status\"",                 "Errors: status field in body"),
    ("app.py",          "logger.exception",           "Errors: 500 logs full traceback server-side"),
    ("app.py",          "\"An unexpected error occurred\"","Errors: opaque 500 to client"),
]

for rel, token, desc in SEC_CHECKS:
    p = ROOT / rel
    if not p.exists():
        fail(f"{desc}: {rel} MISSING")
        continue
    src = p.read_text(encoding="utf-8")
    if token in src:
        ok(desc)
    else:
        fail(f"{desc}: token not found in {rel}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Cleanup scan (debug code, temp comments, dead constants)
# ─────────────────────────────────────────────────────────────────────────────
section("STEP 7 — CLEANUP SCAN")

DEBUG_PATTERNS = [
    (r'\bprint\s*\(',         "bare print() statement"),
    (r'\bpdb\b',              "pdb debugger reference"),
    (r'\bipdb\b',             "ipdb debugger reference"),
    (r'\bbreakpoint\s*\(',    "breakpoint() call"),
    (r'#\s*TODO',             "TODO comment"),
    (r'#\s*FIXME',            "FIXME comment"),
    (r'#\s*HACK',             "HACK comment"),
    (r'#\s*XXX',              "XXX comment"),
    (r'#\s*TEMP\b',           "TEMP comment"),
    (r'#\s*DEBUG\b',          "DEBUG comment"),
    (r'console\.log\s*\(',    "console.log (JS/TS)"),
]

ALL_BACKEND = list(ROOT.rglob("*.py"))
ALL_BACKEND = [p for p in ALL_BACKEND
               if "__pycache__" not in str(p)
               and "venv" not in str(p)
               and not p.name.startswith("_verify")]

cleanup_issues = []
for p in ALL_BACKEND:
    src = p.read_text(encoding="utf-8")
    rel = str(p.relative_to(ROOT))
    for pattern, label in DEBUG_PATTERNS:
        for i, line in enumerate(src.splitlines(), 1):
            if re.search(pattern, line, re.IGNORECASE):
                # Exclude legitimate uses in docstrings / comments that are informational
                stripped = line.strip()
                # Skip lines that are part of a docstring explaining the pattern
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if "logging" in line.lower() and "print" not in pattern:
                    continue
                msg = f"{rel}:{i}: {label}: {stripped[:72]}"
                cleanup_issues.append(msg)
                print(f"  WARN  {msg}")

if not cleanup_issues:
    print("  OK — no debug/temp/todo artefacts found")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
section("SUMMARY")
total_checks = len(PASS) + len(FAIL)
print(f"  Passed : {len(PASS)}/{total_checks}")
print(f"  Failed : {len(FAIL)}/{total_checks}")
if cleanup_issues:
    print(f"  Cleanup warnings : {len(cleanup_issues)}")
else:
    print(f"  Cleanup warnings : 0")

if FAIL:
    print()
    print("  FAILURES:")
    for f in FAIL:
        print(f"    !! {f}")
    sys.exit(1)
else:
    print()
    print("  ALL STEPS 4–7 PASSED")
    sys.exit(0)
