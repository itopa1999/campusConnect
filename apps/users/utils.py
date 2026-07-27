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