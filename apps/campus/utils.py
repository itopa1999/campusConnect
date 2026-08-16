from utils.enums import ListingTypeEnum
from utils.helpers import format_naira

def get_listing_detail_info(listing):
    """
    Returns (price, category_name, category_icon) for a listing based on its type.
    """
    if listing.listing_type.lower() == ListingTypeEnum.SELL.value.lower() and hasattr(listing, 'sell_details') and listing.sell_details:
        price = format_naira(listing.sell_details.price)
        category = listing.sell_details.category
        return price, category.name if category else '', category.icon if category else ''
    elif listing.listing_type.lower() == ListingTypeEnum.SERVICE.value.lower() and hasattr(listing, 'service_details') and listing.service_details:
        price = format_naira(listing.service_details.price) if listing.service_details.price else 0
        category = listing.service_details.category
        return price, category.name if category else '', category.icon if category else ''
    elif listing.listing_type.lower() == ListingTypeEnum.ACCOMMODATION.value.lower() and hasattr(listing, 'accommodation_details') and listing.accommodation_details:
        price = format_naira(listing.accommodation_details.rent_price)
        return price, listing.accommodation_details.property_type or '', 'fas fa-home'
    return 0, '', ''