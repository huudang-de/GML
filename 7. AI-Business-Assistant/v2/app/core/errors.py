"""Errors and security sanitization for AI Business Assistant v2.

Adheres to:
- Spec §5 T1 / T5
- Plan C3 / ADR-005
"""

import re
from typing import Union


class UnsafeDeploymentError(Exception):
    """Raised when configuration violates production security policies (e.g., TC-T5-09)."""
    pass


class SqlRejected(Exception):
    """Raised when an SQL query violates AST security policies or RBAC allowlist."""
    pass


class DbExecutionError(Exception):
    """Raised when database execution fails."""
    pass


# Pattern to redact credentials in database URIs:
# Matches postgresql://user:pass@host or postgresql+psycopg2://user:pass@host
_URI_CREDENTIALS_RE = re.compile(
    r'(postgres(?:ql)?(?:\+[a-zA-Z0-9_-]+)?://)(?:[^@/\s]+)@',
    re.IGNORECASE,
)

# Pattern to redact internal silver schema references:
_SILVER_SCHEMA_RE = re.compile(r'silver\.', re.IGNORECASE)

# Pattern to redact absolute Windows file paths (e.g. D:\path or D:\\path or D:/path)
_WIN_PATH_RE = re.compile(
    r'[a-zA-Z]:(?:\\{1,2}|/)[^\s"\'<>:;|\)\(\]\}\]]+',
)

# Pattern to redact absolute POSIX file paths (e.g. /var/app/..., /etc/..., /home/...)
_POSIX_PATH_RE = re.compile(
    r'/(?:var|etc|home|usr|tmp|app|opt|root|srv|bin|sbin)/[^\s"\'<>:;|\)\(\]\}\]]+',
)


def sanitize_db_error(err: Union[Exception, str]) -> str:
    """Sanitize database error messages to prevent credential, schema, or system path leakage.

    1. Redacts user:password credentials in database connection URIs.
    2. Redacts all references to raw internal schema 'silver.' with '[REDACTED_SCHEMA].'.
    3. Redacts absolute system file paths (Windows and Linux).

    Args:
        err: Exception instance or raw error string.

    Returns:
        Sanitized error string safe for logging or client reporting.
    """
    if isinstance(err, Exception):
        msg = str(err)
        if not msg:
            msg = repr(err)
    else:
        msg = str(err)

    # 1. Mask URI credentials
    msg = _URI_CREDENTIALS_RE.sub(r'\1[REDACTED_CREDENTIALS]@', msg)

    # 2. Mask silver schema references
    msg = _SILVER_SCHEMA_RE.sub('[REDACTED_SCHEMA].', msg)

    # 3. Mask Windows and POSIX system paths
    msg = _WIN_PATH_RE.sub('[REDACTED_PATH]', msg)
    msg = _POSIX_PATH_RE.sub('[REDACTED_PATH]', msg)

    return msg
