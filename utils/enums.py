from enum import Enum

from utils.constant_helper import ConstantHelper


# ============================================================
# BASE ENUM
# ============================================================

class BaseChoiceEnum(Enum):

    @classmethod
    def choices(cls):
        """
        Return Django-compatible choices.

        Example:
            SELL = "Sell"

        becomes:

            [("Sell", "Sell")]
        """
        return [
            (member.value, member.value)
            for member in cls
        ]

    @classmethod
    def values(cls):
        """
        Return all enum values.
        """
        return [
            member.value
            for member in cls
        ]


# ============================================================
# GROUPS
# ============================================================

class GroupNamesEnum(BaseChoiceEnum):
    ADMIN = "Admin"
    STUDENT = "Student"
    MODERATOR = "Moderator"


# ============================================================
# USER ID VERIFICATION
# ============================================================

class UserIdVerificationEnum(BaseChoiceEnum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PENDING = "Pending"


# ============================================================
# TOKEN TYPES
# ============================================================

class TokenTypeEnum(BaseChoiceEnum):
    EMAIL_VERIFICATION = "Email Verification"
    PASSWORD_RESET = "Password Reset"
    ACCOUNT_ACTIVATION = "Account Activation"


# ============================================================
# ADVERT TYPES
# ============================================================

class AdvertTypeEnum(Enum):
    BANNER = (
        "banner",
        "Banner",
        ConstantHelper.POINT_CHARGES_FOR_BANNER,
    )

    HOT_SALE = (
        "hot_sale",
        "Hot Sale",
        ConstantHelper.POINT_CHARGES_FOR_HOT_SALES,
    )

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

    @classmethod
    def values(cls):
        return [
            item.value_code
            for item in cls
        ]


# ============================================================
# PURPOSE
# ============================================================

class PurposeChoicesEnum(BaseChoiceEnum):
    RENT_ENTIRE = "Rent Entire Unit"
    RENT_ROOM = "Rent a Room (Shared)"
    ROOMMATE_WANTED = "Looking for Roommate"


# ============================================================
# LISTING TYPES
# ============================================================

class ListingTypeEnum(BaseChoiceEnum):
    SELL = "Sell"
    SERVICE = "Service"
    ACCOMMODATION = "Accommodation"

    # RENT = "Rent"
    # EXCHANGE = "Exchange"
    # ROOMMATE = "Roommate"
    # WANTED = "Wanted"
    # FREEBIE = "Freebie"
    # JOB = "Job"
    # EVENT = "Event"
    # LOST_FOUND = "Lost Found"
    # DONATION = "Donation"


# ============================================================
# LISTING STATUS
# ============================================================

class ListingStatusTypeEnum(BaseChoiceEnum):
    ACTIVE = "Active"
    REJECT = "Reject"
    SOLD = "Sold"
    EXPIRED = "Expired"
    PENDING = "Pending"
    HIDDEN = "Hidden"


# ============================================================
# LISTING CONDITION
# ============================================================

class ListingConditionEnum(BaseChoiceEnum):
    NEW = "New"
    FAIR = "Fair"
    BUNDLE = "Bundle"
    ALMOST_NEW = "Almost New"
    OTHER = "Other"


# ============================================================
# ISSUE TYPES
# ============================================================

class IssueTypeEnum(BaseChoiceEnum):
    REPORT_LISTING = "Report Listing"
    REPORT_USER = "Report User"
    BUG = "Bug"
    QUESTION = "Question"
    OTHER = "Other"
    ACCOUNT = "Account"


# ============================================================
# BADGES
# ============================================================

class BadgeChoiceEnum(BaseChoiceEnum):
    UN_VERIFIED = "Unverified"
    VERIFIED = "Verified"
    TRUSTED = "Trusted"
    TOP_SELLER = "Top Seller"


# ============================================================
# LOST AND FOUND STATUS
# ============================================================

class LostAndFoundStatusEnum(BaseChoiceEnum):
    PENDING = "Pending"
    REJECT = "Reject"
    HIDDEN = "Hidden"
    OPEN = "Open"
    CLAIMED = "Claimed"
    EXPIRED = "Expired"


# ============================================================
# DEFAULT POINT
# ============================================================

class DefaultPointEnum(Enum):
    DEFAULT_POINT = 3

    @classmethod
    def values(cls):
        return [
            item.value
            for item in cls
        ]


# ============================================================
# POINT PURCHASE STATUS
# ============================================================

class PointPurchaseStatusEnum(BaseChoiceEnum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"
    REFUNDED = "Refunded"


# ============================================================
# POINT TRANSACTION TYPE
# ============================================================

class PointTransactionTypeEnum(BaseChoiceEnum):
    ACCOUNT_CREATION_BONUS = "Account Creation Bonus"
    PURCHASE = "Purchase"
    LISTING_CREATION = "Listing Creation"
    LISTING_UPDATE = "Listing Update"
    REACTIVATION = "Reactivation"
    BADGE_UPGRADE = "Badge Upgrade"
    PROMOTION = "Promotion"
    ADMIN_ADJUSTMENT = "Admin Adjustment"
    TRANSFER = "Transfer"
    REFUND = "Refund"
    OTHER = "Other"


# ============================================================
# NOTIFICATIONS
# ============================================================

class NotificationEnum(BaseChoiceEnum):
    LISTING = "Listing"
    ACCOUNT = "Account"
    SYSTEM = "System"
    NOTIFICATION = "Notification"
    TRANSACTION = "Transaction"
    OTHERS = "Others"


# ============================================================
# FEATURE FLAGS
# ============================================================

class FeatureFlagEnum(BaseChoiceEnum):
    FREE_BANNER = "Free Banner"
    ACCOUNT_CREATION_BONUS = "Account Creation Bonus"
    HIDE_VISIBILITY = "Profile Visibility"


# ============================================================
# CACHE KEYS
# ============================================================
# IMPORTANT:
# DO NOT CHANGE THESE TO HUMAN-READABLE VALUES.
#
# Cache keys are technical identifiers and intentionally contain
# underscores/placeholders.

class CacheKeysEnum(Enum):

    DASHBOARD = "get_dashboard_{user_id}"

    DASHBOARD_UPCOMING_EXPIRATION_LISTING = (
        "get_upcoming_expiration_listing_{user_id}"
    )

    DASHBOARD_LISTING = (
        "get_dashboard_listing_{user_id}_{page}_{per_page}_{filters}"
    )

    DASHBOARD_REVIEW = (
        "get_dashboard_review_{user_id}_{page}_{per_page}_{filters}"
    )

    GET_POINTS_BALANCE = "get_points_balance_{user_id}"

    LOOKUP_DATA = "lookup_data_{filters}"

    INDEX_PRODUCTS = "index_products"

    LISTING_DETAIL = "listing_detail_{user_id}_{listing_id}"

    CATEGORIZED_LISTINGS = (
        "categorized_listings_"
        "{user_id}_{section}_{page}_{per_page}_{filters}"
    )

    LOST_ITEMS = "lost_items_{page}_{per_page}_{filters}"

    POINT_PACKAGES = "point_packages"

    PURCHASES = "purchases_{user_id}_{page}_{per_page}_{filters}"

    TRANSACTIONS = (
        "transactions_{user_id}_{page}_{per_page}_{filters}"
    )

    PROFILE = "profile_{user_id}"

    PROFILE_ID = "profile_id_{user_id}"

    PROFILE_HALL = "profile_hall_{user_id}"

    PROFILE_VISIBILITY = "profile_visibility_{user_id}"

    PUBLIC_LISTING_DETAILS = (
        "public_listing_details_{user_id}_{listing_id}"
    )

    NOTIFICATIONS = (
        "notifications_{user_id}_{page}_{per_page}_{filters}"
    )

    NOTIFICATION_HEADER = "notifications_header_{user_id}"

    FAVOURITE = (
        "favourite_{user_id}_{page}_{per_page}_{filters}"
    )

    # Moderator
    MOD_DASHBOARD = "mod_get_dashboard_{user_id}"

    @classmethod
    def format(cls, key, **kwargs):
        return key.value.format(**kwargs)


# ============================================================
# MODERATOR ACTIONS
# ============================================================

class ModeratorActionTypeEnum(BaseChoiceEnum):
    APPROVE = "Approve"
    REJECT = "Reject"
    HIDE = "Hide"
    DELETE = "Delete"
    FLAG = "Flag"
    UNFLAG = "Unflag"
    WARNING = "Warning"
    SUSPEND = "Suspend"
    BAN = "Ban"
    REINSTATE = "Reinstate"
    RESOLVE_REPORT = "Resolve Report"
    ESCALATE = "Escalate"
    UNHIDE = "Unhide"
    ASSIGN = "Assign"
    REOPEN = "Reopen"
    CREATE = "Create"
    UPDATE = "Update"


# ============================================================
# CONTENT TYPES
# ============================================================

class ContentTypeEnum(BaseChoiceEnum):
    LISTING = "Listing"
    REVIEW = "Review"
    USER = "User"
    REPORT = "Report"
    CATEGORY = "Category"
    HOTSPOT = "Hotspot"
    LOST_ITEM = "Lost Item"


# ============================================================
# REPORT STATUS
# ============================================================

class ReportStatusEnum(BaseChoiceEnum):
    PENDING = "Pending"
    IN_REVIEW = "In Review"
    RESOLVED = "Resolved"
    ESCALATED = "Escalated"


# ============================================================
# PLATFORM
# ============================================================

class PlatformEnum(BaseChoiceEnum):
    SWAGGER = "Swagger"
    WEB = "Web"
    POSTMAN = "Postman"
    MOBILE = "Mobile"


# ============================================================
# TWO FACTOR AUTHENTICATION
# ============================================================

class TwoFactorMethodEnum(BaseChoiceEnum):
    TOTP = "TOTP"
    SMS = "SMS"
    EMAIL = "Email"
    HARDWARE = "Hardware"
    BACKUP = "Backup"