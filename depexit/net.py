"""HTTPS context that works on fresh interpreters.

python.org builds of Python on macOS ship without root certificates until
"Install Certificates.command" is run, so the default context rejects every
server. Certificate verification is never disabled: when the default store
is empty we load a CA bundle that exists on the machine instead.
"""
from __future__ import annotations

import os
import ssl
from functools import lru_cache

CANDIDATE_BUNDLES = (
    "/etc/ssl/cert.pem",                      # macOS system bundle, also some BSDs
    "/etc/ssl/certs/ca-certificates.crt",     # Debian, Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt",       # Fedora, RHEL
    "/etc/ssl/ca-bundle.pem",                 # openSUSE
)


@lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if os.environ.get("SSL_CERT_FILE") or ctx.get_ca_certs() or ctx.cert_store_stats().get("x509_ca"):
        return ctx
    try:
        import certifi  # present when the user has it; not a dependency
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    for path in CANDIDATE_BUNDLES:
        if os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return ctx
