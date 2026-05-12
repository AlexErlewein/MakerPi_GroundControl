"""Custom middleware for iOS PWA compatibility"""

from starlette.middleware.sessions import SessionMiddleware


class PWASessionMiddleware(SessionMiddleware):
    """SessionMiddleware without SameSite attribute.

    Starlette forces samesite=lax by default, which breaks session cookies
    in iOS PWA standalone mode — the fetch() calls don't send the cookie.
    Omitting SameSite entirely falls back to the browser default (no restriction),
    which works on both HTTP and iOS PWA contexts.
    """

    def __init__(self, app, secret_key, **kwargs):
        super().__init__(app, secret_key=secret_key, **kwargs)
        # Override: remove the samesite= flag entirely
        self.security_flags = "httponly"
