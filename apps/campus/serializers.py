

from rest_framework import serializers
from apps.campus.models import Claim, Listing, Category, CampusHotspot, LostAndFound

class ListingSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_deleted=False),
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
            'category', 'hotspots', 'is_ads_banner', 'is_hot_sales'
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
        fields = [
            'id', 'item_name', 'description', 'location', 'date_found',
            'status', 'verification1', 'answer1', 'verification2', 'answer2',
            'full_name', 'email', 'phone', 'department', 'image'
        ]
        read_only_fields = ['id', 'status']


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            'id', 'lost_item', 'answer1', 'answer2',
            'full_name', 'email', 'phone'
        ]
        read_only_fields = ['id']


class UploadLisitingImageSerializer(serializers.Serializer):
    image = serializers.ImageField()