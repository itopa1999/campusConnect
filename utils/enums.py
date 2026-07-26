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
    REJECT = 'reject'
    SOLD = 'sold'
    EXPIRED = 'expired'
    PENDING = 'pending'
    HIDDEN = 'hidden'

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
    PENDING = 'pending'
    REJECT = 'reject'
    HIDDEN = 'hide'
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
    

class NotificationEnum(Enum):
    LISTING = "listing"
    ACCOUNT = "account"
    SYSTEM = "system"
    TRANSACTION = 'transaction'
    OTHERS = "others"

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
    

class CacheKeysEnum(Enum):
    """
    Centralized cache key names for consistency across the project.
    Always use CacheKeys.KEY_NAME.value when accessing cache.
    """

    # ANNO and Student
    DASHBOARD = "get_dashboard_{user_id}"
    DASHBOARD_UPCOMING_EXPIRATION_LISTING = "get_upcoming_expiration_listing_{user_id}"
    DASHBOARD_LISTING = "get_dashboard_listing_{user_id}_{page}_{per_page}_{filters}"
    DASHBOARD_REVIEW = "get_dashboard_review_{user_id}_{page}_{per_page}_{filters}"
    GET_POINTS_BALANCE = "get_points_balance_{user_id}"
    LOOKUP_DATA = "lookup_data_{filters}"
    INDEX_PRODUCTS = "index_products"
    LISTING_DETAIL = "listing_detail_{user_id}_{listing_id}"
    CATEGORIZED_LISTINGS = "categorized_listings_{user_id}_{section}_{page}_{per_page}_{filters}"
    LOST_ITEMS = "lost_items_{page}_{per_page}_{filters}"
    POINT_PACKAGES = "point_packages"
    PURCHASES = "purchases_{user_id}_{page}_{per_page}_{filters}"
    TRANSACTIONS = "transactions_{user_id}_{page}_{per_page}_{filters}"
    PROFILE = "profile_{user_id}"
    PUBLIC_LISTING_DETAILS = "public_listing_details_{user_id}_{listing_id}"
    NOTIFICATIONS = "notifications_{user_id}_{page}_{per_page}_{filters}"
    NOTIFICATION_HEADER = "notifications_header_{user_id}"
    FAVOURITE = "favourite_{user_id}_{page}_{per_page}_{filters}"


    # Moderator
    MOD_DASHBOARD = 'mod_get_dashboard_{user_id}'


    @classmethod
    def format(cls, key, **kwargs):
        """
        Helper method to fill in placeholders for formatted keys.
        Example:
            CacheKeys.format(CacheKeys.USER_PROFILE, user_id=5)
        """
        return key.value.format(**kwargs)
    



class ModeratorActionTypeEnum(Enum):
    APPROVE = 'approve'
    REJECT = 'reject'
    HIDE = 'hide'
    DELETE = 'delete'
    FLAG = 'flag'
    UNFLAG = 'unflag'
    WARNING = 'warning'
    SUSPEND = 'suspend'
    BAN = 'ban'
    REINSTATE = 'reinstate'
    RESOLVE_REPORT = 'resolve_report'
    ESCALATE = 'escalate'
    UNHIDE = 'unhide'
    ASSIGN = 'assign'
    REOPEN = 'reopen'
    CREATE = 'create'
    UPDATE = 'update'

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    

class ContentTypeEnum(Enum):
    LISTING = 'listing'
    REVIEW = 'review'
    USER = 'user'
    REPORT = 'report'
    CATEGORY = 'category'
    HOTSPOT = 'hotspot'
    LOST_ITEM = 'lost_item'

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]
    


class ReportStatusEnum(Enum):
    PENDING = 'pending'
    IN_REVIEW = 'in_review'
    RESOLVED = 'resolved'
    ESCALATED = 'escalated'

    @classmethod
    def choices(cls):
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]


class PlatformEnum(Enum):
    SWAGGER = 'swagger'
    WEB = 'web'
    POSTMAN = 'postman'
    MOBILE = 'mobile'

    @classmethod
    def choices(cls):
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]