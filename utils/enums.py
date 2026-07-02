from enum import Enum

from utils.constant_helper import ConstantHelper

class GroupNames(Enum):
    ADMIN = "Admin"
    STUDENT = "Student"
    MODERATOR = "Moderator"

    @classmethod
    def choices(cls):
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]
    
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
    
class AdvertTypeEnum(Enum):
    BANNER = ("banner", "Banner", ConstantHelper.POINT_CHARGES_FOR_BANNER)
    HOT_SALE = ("hot_sale", "Hot Sale", ConstantHelper.POINT_CHARGES_FOR_HOT_SALES)

    @property
    def value_code(self):
        return self.value[0]

    @property
    def label(self):
        return self.value[1]

    @property
    def points(self):
        return self.value[2]

    @classmethod
    def choices(cls):
        return [
            {
                "value": item.value_code,
                "label": item.label,
                "points": item.points,
            }
            for item in cls
        ]
    


class ListingType(Enum):
    SELL = 'sell'
    WANTED = 'wanted'
    FREEBIE = 'freebie'
    SERVICE = 'service'

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

class BadgeListingType(Enum):
    NEW = 'new'
    FAIR = 'fair'
    BUNDLE = 'bundle'
    ALMOST_NEW = 'almost_new'
    OTHER = 'other'

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


class BadgeChoiceEnum(Enum):
    UN_VERIFIED = "unverified"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    TOP_SELLER = "top_seller"

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    

class LostAndFoundStatusEnum(Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    EXPIRED = "expired"

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]


class DefaultPointEnum(Enum):
    DefaultPoint = 3

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    
class PointPurchaseStatusEnum(Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    

class PointTransactionTypeEnum(Enum):
    ACCOUNT_CREATION_BONUS = 'account_creation_bonus'
    PURCHASE = 'purchase'
    LISTING_CREATION = 'listing_creation'
    LISTING_UPDATE = 'listing_update'
    REACTIVATION = 'reactivation'
    BADGE_UPGRADE = 'badge_upgrade'
    PROMOTION = 'promotion'
    ADMIN_ADJUSTMENT = 'admin_adjustment'
    TRANSFER = 'transfer'
    REFUND = 'refund'
    OTHER = 'other'

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    
class FeatureFlagEnum(Enum):
    FREE_BANNER = "free_banner"
    ACCOUNT_CREATION_BONUS= "account_creation_bonus"

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]