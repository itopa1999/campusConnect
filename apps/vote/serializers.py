from rest_framework import serializers
from apps.vote.models import PollCategory


class PollCategoryCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating OR updating a poll category.
    Just handles field validation and model mapping.
    All business logic goes in commands/services.
    """
    class Meta:
        model = PollCategory
        fields = (
            'name',
            'description',
            'color_code',
            'icon',
            'is_active',
        )

    def validate_name(self, value):
        """Basic validation: name cannot be empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()

    def validate_color_code(self, value):
        """Basic validation: color code format."""
        if value:
            value = value.strip()
            if not value.startswith('#'):
                raise serializers.ValidationError(
                    "Color code must start with '#'."
                )
            if len(value) not in [4, 7]:
                raise serializers.ValidationError(
                    "Color code must be a valid hex code (e.g., #FFF or #FFFFFF)."
                )
        return value