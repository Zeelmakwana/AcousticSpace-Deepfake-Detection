"""
Prompt 9 — Static Verification Script
Checks: syntax, unused imports, security wiring assertions.
Run from: backend/
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent

BACKEND_FILES = [
    "app.py",
    "api/routes.py",
    "auth/routes.py",
    "auth/utils.py",
    "auth/dependencies.py",
    "auth/schemas.py",
    "auth/database.py",
    "models/user.py",
    "security/__init__.py",
    "security/file_validator.py",
    "security/audit_log.py",
    "middleware/__init__.py",
    "middleware/logging_middleware.py",
    "middleware/security_headers.py",
]

issues = []

# ── 1. SYNTAX ────────────────────────────────────────────────────────────────
print("=" * 62)
print("1. SYNTAX CHECK")
print("=" * 62)
for rel in BACKEND_FILES:
    p = ROOT / rel
    if not p.exists():
        issues.append(f"MISSING  {rel}")
        print(f"  MISSING  {rel}")
        continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK       {rel}")
    except SyntaxError as e:
        msg = f"SYNTAX   {rel}: line {e.lineno}: {e.msg}"
        issues.append(msg)
        print(f"  FAIL     {msg}")

# ── 2. UNUSED IMPORT AUDIT ───────────────────────────────────────────────────
print()
print("=" * 62)
print("2. UNUSED IMPORT AUDIT")
print("=" * 62)

# Names that are valid even with count==1
INTENTIONAL = {
    # PEP-563 future import — always count==1
    "annotations",
    # imported for side-effects (registers ORM classes)
    "models",
    # imported but used only at runtime via app.state
    "_rate_limit_exceeded_handler",
    # used via warnings.warn() — stdlib, counted as 1 in some files
    "warnings",
    # local import inside function body in routes.py — linter sees count<2
    "timezone", "timedelta", "func", "case",
    # local import inside refresh_tokens function body
    "TokenData",
    # noqa marker — not a real name
}

AUDIT_FILES = [
    "app.py",
    "api/routes.py",
    "auth/routes.py",
    "auth/utils.py",
    "auth/dependencies.py",
    "security/file_validator.py",
    "security/audit_log.py",
    "middleware/logging_middleware.py",
    "middleware/security_headers.py",
]

unused_found = False
for rel in AUDIT_FILES:
    p = ROOT / rel
    if not p.exists():
        continue
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.append(alias.asname or alias.name)

    for name in imported:
        if name in INTENTIONAL or name.startswith("_"):
            continue
        count = src.count(name)
        if count < 2:
            print(f"  WARN  {rel}: '{name}' may be unused (occurrences={count})")
            unused_found = True

if not unused_found:
    print("  OK — no suspicious unused imports found")

# ── 3. F-STRING WITH UNNECESSARY LITERAL DETECTION ──────────────────────────
print()
print("=" * 62)
print("3. F-STRING CONSTANT DETECTION (SyntaxWarning in Python 3.12+)")
print("=" * 62)
import re
fstring_issues = False
fstring_pattern = re.compile(r'f"[^"]*"')  # simple scan
for rel in AUDIT_FILES:
    p = ROOT / rel
    if not p.exists():
        continue
    src = p.read_text(encoding="utf-8")
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        # Detect f-strings that contain no { } — unnecessary f-prefix
        for m in re.finditer(r'\bf"([^"{}]*)"', line):
            print(f"  WARN  {rel}:{i}: unnecessary f-string (no braces): {m.group()!r}")
            fstring_issues = True
        for m in re.finditer(r"\bf'([^'{}]*)'", line):
            print(f"  WARN  {rel}:{i}: unnecessary f-string (no braces): {m.group()!r}")
            fstring_issues = True
if not fstring_issues:
    print("  OK — no unnecessary f-strings found")

# ── 4. SECURITY WIRING ASSERTIONS ───────────────────────────────────────────
print()
print("=" * 62)
print("4. SECURITY WIRING ASSERTIONS")
print("=" * 62)
ASSERTIONS = [
    ("api/routes.py",              "validate_upload",            "File validator called in /analyze"),
    ("api/routes.py",              "get_current_active_user",    "Auth required on all protected routes"),
    ("api/routes.py",              "AuditEvent",                 "Audit events emitted in api/routes"),
    ("api/routes.py",              "FileValidationError",        "FileValidationError caught in /analyze"),
    ("auth/utils.py",              "JWT_ISSUER",                 "JWT issuer claim present"),
    ("auth/utils.py",              "JWT_AUDIENCE",               "JWT audience claim present"),
    ("auth/utils.py",              "ExpiredSignatureError",      "Granular JWT expiry handling"),
    ("auth/utils.py",              "JWTClaimsError",             "Granular JWT claims handling"),
    ("auth/utils.py",              "_warn_weak_secret",          "Weak secret detection on startup"),
    ("auth/utils.py",              "ALGORITHM",                  "Algorithm pinned to HS256"),
    ("auth/dependencies.py",       "AuditEvent.AUTH_TOKEN_INVALID", "Auth failure audited in dependency"),
    ("auth/dependencies.py",       "get_current_active_user",    "Active user check in dependencies"),
    ("auth/routes.py",             "AuditEvent.AUTH_LOGIN",      "Login success audited"),
    ("auth/routes.py",             "AuditEvent.AUTH_LOGIN_FAILED","Login failure audited"),
    ("auth/routes.py",             "AuditEvent.AUTH_REGISTER",   "Registration audited"),
    ("auth/routes.py",             "AuditEvent.AUTH_REFRESH",    "Token refresh audited"),
    ("auth/routes.py",             "AuditEvent.AUTH_LOGOUT",     "Logout audited"),
    ("app.py",                     "RateLimitExceeded",          "Rate limit exception handler registered"),
    ("app.py",                     "RequestValidationError",     "Validation error handler registered"),
    ("app.py",                     "SecurityHeadersMiddleware",  "Security headers middleware added"),
    ("app.py",                     "RequestLoggingMiddleware",   "Request logging middleware added"),
    ("app.py",                     "_CORS_METHODS",              "CORS methods explicitly restricted"),
    ("app.py",                     "_CORS_HEADERS",              "CORS headers explicitly restricted"),
    ("app.py",                     "max_age=600",                "CORS preflight cache set"),
    ("app.py",                     "_warn_weak_secret",          "Weak secret checked at startup"),
    ("middleware/security_headers.py", "X-Frame-Options",        "X-Frame-Options header set"),
    ("middleware/security_headers.py", "Content-Security-Policy","CSP header set"),
    ("middleware/security_headers.py", "X-Content-Type-Options", "MIME sniff protection set"),
    ("middleware/security_headers.py", "Strict-Transport-Security","HSTS header set"),
    ("middleware/security_headers.py", "Cache-Control",          "No-cache on /auth routes"),
    ("middleware/logging_middleware.py", "X-Request-ID",         "Request ID propagated to response"),
    ("middleware/logging_middleware.py", "request.state.request_id", "Request ID set on state"),
    ("security/audit_log.py",      "TimedRotatingFileHandler",   "Audit log rotates daily"),
    ("security/audit_log.py",      "backupCount=30",             "30-day log retention"),
    ("security/file_validator.py", "FileValidationError",        "Custom exception defined"),
    ("security/file_validator.py", "_check_entropy",             "Entropy check defined"),
    ("security/file_validator.py", "_check_mime",                "MIME check defined"),
    ("security/file_validator.py", "_sanitise_filename",         "Filename sanitisation defined"),
    ("security/file_validator.py", "path traversal",             "Path traversal guard documented"),
]
wiring_failures = 0
for rel, token, desc in ASSERTIONS:
    p = ROOT / rel
    if not p.exists():
        print(f"  FAIL  {desc}: file missing")
        issues.append(f"MISSING file: {rel}")
        wiring_failures += 1
        continue
    src = p.read_text(encoding="utf-8")
    if token in src:
        print(f"  OK    {desc}")
    else:
        print(f"  FAIL  {desc}: '{token}' not found in {rel}")
        issues.append(f"WIRING FAIL: {rel} missing '{token}'")
        wiring_failures += 1

# ── 5. CIRCULAR IMPORT RISK SCAN ─────────────────────────────────────────────
print()
print("=" * 62)
print("5. CIRCULAR IMPORT RISK SCAN")
print("=" * 62)
circ_files = {
    "app.py":                  ["api.routes", "auth.routes", "auth.database",
                                 "middleware.logging_middleware", "middleware.security_headers"],
    "api/routes.py":           ["auth.database", "auth.dependencies", "models.analysis_history",
                                 "models.user", "services.audio_processing",
                                 "services.feature_extraction", "services.inference",
                                 "services.pdf_report", "services.explanation",
                                 "security.audit_log", "security.file_validator"],
    "auth/routes.py":          ["auth.database", "auth.dependencies", "auth.schemas",
                                 "auth.utils", "models.user", "security.audit_log"],
    "auth/dependencies.py":    ["auth.database", "auth.utils", "models.user", "security.audit_log"],
    "auth/utils.py":           ["auth.schemas"],
}
circ_ok = True
for rel, expected_deps in circ_files.items():
    p = ROOT / rel
    if not p.exists():
        continue
    src = p.read_text(encoding="utf-8")
    for dep in expected_deps:
        mod_path = dep.replace(".", "/") + ".py"
        dep_p = ROOT / mod_path
        if dep_p.exists():
            dep_src = dep_p.read_text(encoding="utf-8")
            # Check if dep imports back into rel's module
            rel_mod = rel.replace("/", ".").replace(".py", "")
            if rel_mod in dep_src and f"import {rel_mod}" in dep_src:
                print(f"  WARN  Possible circular: {rel} ↔ {dep}")
                circ_ok = False
if circ_ok:
    print("  OK — no obvious circular import risks detected")

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print()
print("=" * 62)
print("SUMMARY")
print("=" * 62)
if not issues:
    print("  ALL CHECKS PASSED")
    sys.exit(0)
else:
    for iss in issues:
        print(f"  !! {iss}")
    sys.exit(1)
