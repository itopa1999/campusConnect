

from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from apps.campus.models import AccommodationListing, Claim, Listing, Category, CampusHotspot, LostAndFound, SellListing, ServiceListing, SubCategory
from utils.enums import ListingTypeEnum, PurposeChoicesEnum
from django.utils import timezone

class ListingSerializer(serializers.ModelSerializer):
    # Write-only fields for detail models
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_deleted=False),
        write_only=True,
        required=False,
        allow_null=True
    )
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.filter(is_deleted=False),
        write_only=True,
        required=False,
        allow_null=True
    )
    hotspots = serializers.PrimaryKeyRelatedField(
        queryset=CampusHotspot.objects.filter(is_deleted=False),
        many=True,
        write_only=True,
        required=False
    )
    image = serializers.ImageField(required=False, allow_null=True)

    # Common sell/service fields (some optional)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    negotiation = serializers.BooleanField(default=False, required=False)
    condition = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    brand = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    model = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    quantity = serializers.IntegerField(default=1, required=False)
    warranty = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)

    # Service-specific
    delivery_time = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    service_duration = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    experience = serializers.IntegerField(required=False, allow_null=True)
    portfolio = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    online_available = serializers.BooleanField(default=False, required=False)

    # Accommodation-specific
    purpose = serializers.ChoiceField(choices=PurposeChoicesEnum.choices(), required=False)
    property_type = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    bedrooms = serializers.IntegerField(default=1, required=False)
    bathrooms = serializers.IntegerField(default=1, required=False)
    furnished = serializers.BooleanField(default=False, required=False)
    rent_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    available_from = serializers.DateField(required=False, allow_null=True)
    lease_duration = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    electricity = serializers.BooleanField(default=False, required=False)
    water = serializers.BooleanField(default=False, required=False)
    security = serializers.BooleanField(default=False, required=False)
    parking = serializers.BooleanField(default=False, required=False)
    distance_to_campus = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    preferred_gender = serializers.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('A', 'Any')], required=False, allow_null=True)
    preferred_student_type = serializers.ChoiceField(choices=[('UG', 'Undergrad'), ('G', 'Graduate'), ('A', 'Any')], required=False, allow_null=True)
    max_occupants = serializers.IntegerField(default=1, required=False)
    roommate_notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    # Listing fields (read-only)
    is_ads_banner = serializers.BooleanField(default=False, required=False)
    is_hot_sales = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = Listing
        fields = [
            'id', 'user', 'listing_type', 'title', 'description', 'image',
            'status', 'expires_at', 'hotspots',
            'is_ads_banner', 'is_hot_sales', 'is_hot_sales_expires_at',
            'is_ads_banner_expires_at', 'auto_reactivate',

            # write-only detail fields
            'category', 'subcategory',
            'price', 'negotiation', 'condition', 'brand', 'model', 'quantity', 'warranty',
            'delivery_time', 'service_duration', 'experience', 'portfolio', 'online_available',
            'purpose', 'property_type', 'bedrooms', 'bathrooms', 'furnished', 'rent_price',
            'available_from', 'lease_duration', 'electricity', 'water', 'security', 'parking',
            'distance_to_campus', 'preferred_gender', 'preferred_student_type',
            'max_occupants', 'roommate_notes',
        ]
        read_only_fields = ['id', 'status', 'expires_at', 'is_hot_sales_expires_at', 'is_ads_banner_expires_at']
        extra_kwargs = {
            'user': {'read_only': True},
            'listing_type': {'required': True},
            'title': {'required': True},
            'description': {'required': False},
        }

    def validate(self, data):
        listing_type = data.get('listing_type')
        if not listing_type:
            raise serializers.ValidationError({"listing_type": "This field is required."})

        # Validate required fields per listing type
        if listing_type == ListingTypeEnum.SELL.value:
            if 'category' not in data or data['category'] is None:
                raise serializers.ValidationError({"category": "Category is required for sell listings."})
            if 'price' not in data or data['price'] is None:
                raise serializers.ValidationError({"price": "Price is required for sell listings."})
            if data.get('price', 0) <= 0:
                raise serializers.ValidationError({"price": "Price must be greater than zero."})

        elif listing_type == ListingTypeEnum.SERVICE.value:
            pass

        elif listing_type == ListingTypeEnum.ACCOMMODATION.value:
            if 'rent_price' not in data or data['rent_price'] is None:
                raise serializers.ValidationError({"rent_price": "Rent price is required for accommodation listings."})
            if data.get('rent_price', 0) <= 0:
                raise serializers.ValidationError({"rent_price": "Rent price must be greater than zero."})
            if 'property_type' not in data or not data['property_type']:
                raise serializers.ValidationError({"property_type": "Property type is required for accommodation listings."})

        else:
            raise serializers.ValidationError({"listing_type": f"Invalid listing type. Choose {ListingTypeEnum.values()}"})

        return data

    @transaction.atomic
    def create(self, validated_data):
        # Extract detail fields
        detail_data = {
            'category': validated_data.pop('category', None),
            'subcategory': validated_data.pop('subcategory', None),
            'price': validated_data.pop('price', None),
            'negotiation': validated_data.pop('negotiation', False),
            'condition': validated_data.pop('condition', None),
            'brand': validated_data.pop('brand', None),
            'model': validated_data.pop('model', None),
            'quantity': validated_data.pop('quantity', 1),
            'warranty': validated_data.pop('warranty', None),
            'delivery_time': validated_data.pop('delivery_time', None),
            'service_duration': validated_data.pop('service_duration', None),
            'experience': validated_data.pop('experience', None),
            'portfolio': validated_data.pop('portfolio', None),
            'online_available': validated_data.pop('online_available', False),
            'purpose': validated_data.pop('purpose', None),
            'property_type': validated_data.pop('property_type', None),
            'bedrooms': validated_data.pop('bedrooms', 1),
            'bathrooms': validated_data.pop('bathrooms', 1),
            'furnished': validated_data.pop('furnished', False),
            'rent_price': validated_data.pop('rent_price', None),
            'available_from': validated_data.pop('available_from', None),
            'lease_duration': validated_data.pop('lease_duration', None),
            'electricity': validated_data.pop('electricity', False),
            'water': validated_data.pop('water', False),
            'security': validated_data.pop('security', False),
            'parking': validated_data.pop('parking', False),
            'distance_to_campus': validated_data.pop('distance_to_campus', None),
            'preferred_gender': validated_data.pop('preferred_gender', None),
            'preferred_student_type': validated_data.pop('preferred_student_type', None),
            'max_occupants': validated_data.pop('max_occupants', 1),
            'roommate_notes': validated_data.pop('roommate_notes', None),
        }

        # Pop hotspots separately
        hotspots = validated_data.pop('hotspots', [])

        # Set user from context
        user = self.context.get('user') or self.context['request'].user
        validated_data['user'] = user

        # Create Listing
        listing = Listing.objects.create(**validated_data)

        # Create detail based on listing_type
        listing_type = listing.listing_type

        if listing_type == ListingTypeEnum.SELL.value:
            SellListing.objects.create(
                listing=listing,
                category=detail_data['category'],
                subcategory=detail_data.get('subcategory'),
                price=detail_data['price'],
                negotiation=detail_data['negotiation'],
                condition=detail_data.get('condition'),
                brand=detail_data.get('brand'),
                model=detail_data.get('model'),
                quantity=detail_data.get('quantity', 1),
                warranty=detail_data.get('warranty'),
            )

        elif listing_type == ListingTypeEnum.SERVICE.value:
            ServiceListing.objects.create(
                listing=listing,
                category=detail_data['category'],
                subcategory=detail_data.get('subcategory'),
                price=detail_data.get('price'),
                negotiation=detail_data['negotiation'],
                delivery_time=detail_data.get('delivery_time'),
                service_duration=detail_data.get('service_duration'),
                experience=detail_data.get('experience'),
                portfolio=detail_data.get('portfolio'),
                online_available=detail_data['online_available'],
            )

        elif listing_type == ListingTypeEnum.ACCOMMODATION.value:
            AccommodationListing.objects.create(
                listing=listing,
                purpose=detail_data.get('purpose'),
                property_type=detail_data['property_type'],
                bedrooms=detail_data['bedrooms'],
                bathrooms=detail_data['bathrooms'],
                furnished=detail_data['furnished'],
                rent_price=detail_data['rent_price'],
                available_from=detail_data.get('available_from'),
                lease_duration=detail_data.get('lease_duration'),
                electricity=detail_data['electricity'],
                water=detail_data['water'],
                security=detail_data['security'],
                parking=detail_data['parking'],
                distance_to_campus=detail_data.get('distance_to_campus'),
                preferred_gender=detail_data.get('preferred_gender'),
                preferred_student_type=detail_data.get('preferred_student_type'),
                max_occupants=detail_data['max_occupants'],
                roommate_notes=detail_data.get('roommate_notes'),
            )

        # Set hotspots
        listing.hotspots.set(hotspots)

        return listing

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.image = validated_data.get('image', instance.image)
        instance.is_ads_banner = validated_data.get('is_ads_banner', instance.is_ads_banner)
        instance.is_hot_sales = validated_data.get('is_hot_sales', instance.is_hot_sales)
        instance.auto_reactivate = validated_data.get('auto_reactivate', instance.auto_reactivate)
        instance.save()

        # Update hotspots
        if 'hotspots' in validated_data:
            instance.hotspots.set(validated_data['hotspots'])

        listing_type = instance.listing_type
        if listing_type == ListingTypeEnum.SELL.value and hasattr(instance, 'sell_details'):
            sell = instance.sell_details
            sell.category = validated_data.get('category', sell.category)
            sell.subcategory = validated_data.get('subcategory', sell.subcategory)
            sell.price = validated_data.get('price', sell.price)
            sell.negotiation = validated_data.get('negotiation', sell.negotiation)
            sell.condition = validated_data.get('condition', sell.condition)
            sell.brand = validated_data.get('brand', sell.brand)
            sell.model = validated_data.get('model', sell.model)
            sell.quantity = validated_data.get('quantity', sell.quantity)
            sell.warranty = validated_data.get('warranty', sell.warranty)
            sell.save()
        elif listing_type == ListingTypeEnum.SERVICE.value and hasattr(instance, 'service_details'):
            service = instance.service_details
            service.category = validated_data.get('category', service.category)
            service.subcategory = validated_data.get('subcategory', service.subcategory)
            service.price = validated_data.get('price', service.price)
            service.negotiation = validated_data.get('negotiation', service.negotiation)
            service.delivery_time = validated_data.get('delivery_time', service.delivery_time)
            service.service_duration = validated_data.get('service_duration', service.service_duration)
            service.experience = validated_data.get('experience', service.experience)
            service.portfolio = validated_data.get('portfolio', service.portfolio)
            service.online_available = validated_data.get('online_available', service.online_available)
            service.save()
        elif listing_type == ListingTypeEnum.ACCOMMODATION.value and hasattr(instance, 'accommodation_details'):
            acc = instance.accommodation_details
            acc.purpose = validated_data.get('purpose', acc.purpose)
            acc.property_type = validated_data.get('property_type', acc.property_type)
            acc.bedrooms = validated_data.get('bedrooms', acc.bedrooms)
            acc.bathrooms = validated_data.get('bathrooms', acc.bathrooms)
            acc.furnished = validated_data.get('furnished', acc.furnished)
            acc.rent_price = validated_data.get('rent_price', acc.rent_price)
            acc.available_from = validated_data.get('available_from', acc.available_from)
            acc.lease_duration = validated_data.get('lease_duration', acc.lease_duration)
            acc.electricity = validated_data.get('electricity', acc.electricity)
            acc.water = validated_data.get('water', acc.water)
            acc.security = validated_data.get('security', acc.security)
            acc.parking = validated_data.get('parking', acc.parking)
            acc.distance_to_campus = validated_data.get('distance_to_campus', acc.distance_to_campus)
            acc.preferred_gender = validated_data.get('preferred_gender', acc.preferred_gender)
            acc.preferred_student_type = validated_data.get('preferred_student_type', acc.preferred_student_type)
            acc.max_occupants = validated_data.get('max_occupants', acc.max_occupants)
            acc.roommate_notes = validated_data.get('roommate_notes', acc.roommate_notes)
            acc.save()

        return instance

class LostAndFoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = LostAndFound
        fields = ['item_name', 'description', 'full_name', 'email', 'phone',
                  'department', 'id', 'status', 'location', 'date_found', 'verification1', 'verification2', 'image']
        read_only_fields = [
            "id",
            "status",
            "full_name",
            "email",
            "phone",
            "department",
        ]

    def validate_date_found(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "Date found cannot be in the future."
            )

        return value


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            'id', 'lost_item', 'answer1', 'answer2'
            
        ]
        read_only_fields = ['id', 'full_name', 'email', 'phone']


class UploadListingImageSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)


class UpdateAdsViewSerializer(serializers.Serializer):
    is_ads_banner = serializers.BooleanField()
    is_hot_sales = serializers.BooleanField()


class ListingAutoActivationSerializer(serializers.Serializer):
    auto_reactivate = serializers.BooleanField()


class ListingUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Title is required.',
            'blank': 'Title cannot be empty.'
        }
    )
    
    category_id = serializers.IntegerField(
        required=True,
        error_messages={
            'required': 'Category is required.',
            'invalid': 'Please select a valid category.'
        }
    )
    
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        min_value=Decimal('0.00'),
        error_messages={
            'required': 'Price is required.',
            'min_value': 'Price cannot be negative.'
        }
    )
    
    description = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Description is required.',
            'blank': 'Description cannot be empty.'
        }
    )
    
    badge = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True
    )
    
    hotspots = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )