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

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    

class ListingType(Enum):
    SELL = 'sell'
    WANTED = 'wanted'
    FREEBIE = 'freebie'

    @classmethod
    def choices(cls):
        """Return choices for Django model field"""
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]

class ListingStatusType(Enum):
    ACTIVE = 'active'
    SOLD = 'sold'
    EXPIRED = 'expired'

    @classmethod
    def choices(cls):
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]

class IssueTypeEnum(Enum):
    REPORT_LISTING = "report_listing"
    REPORT_USER = "report_user"
    BUG = "bug"
    QUESTION = "question"
    OTHER = "other"
    ACCOUNT = "account"

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]    
