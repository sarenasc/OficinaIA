"""Round-trip a disposable test credential; never reads existing user credentials."""

import secrets as random

from app.security.secrets import secrets

ref = None
try:
    value = random.token_urlsafe(24)
    ref = secrets.put(value)
    assert secrets.get(ref) == value
    print("Windows Credential Manager: write/read verified")
finally:
    if ref:
        secrets.delete(ref)
        print("Disposable test credential removed")
