from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

# --- Rate Limiter ---
def get_real_ip(request: Request):
    return get_remote_address(request)

limiter = Limiter(key_func=get_real_ip)


# --- Security Headers ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject standard enterprise security headers.
    Protects against Clickjacking, MIME-sniffing, and XSS.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # 1. Prevent Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # 2. Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. HTTP Strict Transport Security (force HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 4. Content Security Policy (Basic API-focused CSP)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # 5. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 6. Permissions Policy (Disable dangerous browser Features)
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), usb=()"
        
        return response
