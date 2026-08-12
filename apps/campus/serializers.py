

from decimal import Decimal

from rest_framework import serializers
from apps.campus.models import Claim, Listing, Category, CampusHotspot, LostAndFound, SubCategory

class ListingSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_deleted=False),
        write_only=True
    )
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
        write_only=True
    )
    hotspots = serializers.PrimaryKeyRelatedField(
        queryset=CampusHotspot.objects.filter(is_deleted=False),
        many=True,
        write_only=True,
        required=True
    )
    image = serializers.ImageField(required=False, allow_null=True)

    is_ads_banner = serializers.BooleanField(required=False, default=False)
    is_hot_sales = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'price', 'listing_type',
            'badge', 'status', 'expires_at', 'image',
            'category', 'subcategory', 'hotspots', 'is_ads_banner', 'is_hot_sales'
        ]
        read_only_fields = ['id', 'status', 'expires_at']

    def create(self, validated_data):
        hotspots = validated_data.pop('hotspots', [])
        listing = Listing.objects.create(**validated_data)
        listing.hotspots.set(hotspots)
        return listing


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