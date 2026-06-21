class SecurityHeadersMiddleware:
    """
    Middleware that adds security headers to all responses.
    Includes Content-Security-Policy and other protective headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content-Security-Policy
        csp_directives = [
            "default-src 'self'",
            # Scripts: self + S3 static (Django admin JS) + CDN (Bootstrap, anime.js) + Google Analytics
            "script-src 'self' vadomdata.s3.amazonaws.com cdn.jsdelivr.net www.googletagmanager.com www.google-analytics.com 'unsafe-inline'",
            # Styles: self + S3 static (Django admin CSS) + CDN (Bootstrap, Google Fonts) + inline (Bootstrap requires it)
            "style-src 'self' vadomdata.s3.amazonaws.com cdn.jsdelivr.net fonts.googleapis.com 'unsafe-inline'",
            # Fonts: self + S3 static + Google Fonts + CDN (Bootstrap Icons)
            "font-src 'self' vadomdata.s3.amazonaws.com fonts.gstatic.com cdn.jsdelivr.net",
            # Images: self + data URIs (for inline images) + S3 bucket + Google Analytics
            "img-src 'self' data: vadomdata.s3.amazonaws.com www.google-analytics.com",
            # Connections: self + Google Analytics
            "connect-src 'self' www.google-analytics.com www.googletagmanager.com",
            # Frames: self + mapa de OpenStreetMap (página de contacto)
            "frame-src 'self' https://www.openstreetmap.org",
            # Block all object/embed (Flash, Java applets, etc.)
            "object-src 'none'",
            # Only allow forms to submit to self
            "form-action 'self'",
            # Prevent framing (clickjacking protection, redundant with X-Frame-Options)
            "frame-ancestors 'none'",
            # Restrict base tag to prevent base URL hijacking
            "base-uri 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Referrer Policy - send origin only for cross-origin requests
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy - restrict browser features
        response['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), payment=()'
        )

        return response
