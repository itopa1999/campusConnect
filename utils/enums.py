from enum import Enum

class GroupNames(Enum):
    ADMIN = "Admin"
    CUSTOMER = "Customer"
    
    @classmethod
    def values(cls):
        """Return all enum values as a list"""
        return [group.value for group in cls]


class TokenType(Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_ACTIVATION = "account_activation"
    
    @classmethod
    def choices(cls):
        """Return choices for Django model field"""
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]
    
