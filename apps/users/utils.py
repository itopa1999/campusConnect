from apps.users.models import TwoFactorMethod
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

def revoke_all_user_tokens(user):
    """Revoke all tokens for a specific user"""
    try:
        tokens = OutstandingToken.objects.filter(user=user)
        
        blacklisted_tokens = []
        for token in tokens:
            blacklisted_tokens.append(BlacklistedToken(token=token))
        
        if blacklisted_tokens:
            BlacklistedToken.objects.bulk_create(blacklisted_tokens, ignore_conflicts=True)
        
        return True
    except Exception as e:
        return False




def get_user_2fa_status(user):
    """
    Returns a dict with the user's current 2FA state.
    
    """
    active_method = TwoFactorMethod.objects.filter(user=user, is_enabled=True).first()

    return {
        'requires_2fa': active_method is not None,
        'active_method': active_method.method if active_method else None,
    }