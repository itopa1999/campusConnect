# authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()

class JWTCookieAuthentication(BaseAuthentication):
    """
    Authenticate using the access_token stored in an HttpOnly cookie.
    """
    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        if not token:
            return None

        try:
            validated_token = AccessToken(token)
            user_id = validated_token.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Invalid token payload')

            user = User.objects.get(id=user_id, is_active=True, is_deleted=False)
            if not user.email_verified:
                raise AuthenticationFailed('Email not verified')
            return (user, validated_token)
        except (InvalidToken, TokenError) as e:
            raise AuthenticationFailed(str(e))
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')