from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class JWTCookieAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Define paths that should bypass authentication
        auth_exempt_paths = [
            '/auth/refresh/',
            '/auth/login/',
            '/auth/register/'
        ]

        if any(request.path.endswith(path) for path in auth_exempt_paths):
            return None
            
        raw_token = request.COOKIES.get(
            settings.SIMPLE_JWT.get('AUTH_COOKIE_ACCESS', 'access_token')) or None
        if raw_token is None:
            return None
            
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
