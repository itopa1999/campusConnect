from django.contrib import admin
from django.utils.timezone import now
from django.db.models import Case, When, Value, BooleanField

class SoftDeleteAdmin(admin.ModelAdmin):
    """
    Admin base class that shows all objects (including soft-deleted ones)
    and performs soft delete when the default delete action is used.
    """

    def get_queryset(self, request):
        """Show all objects, including deleted ones."""
        return self.model.objects.all_including_deleted()

    def delete_queryset(self, request, queryset):
        """
        Override the default delete action to perform soft delete.
        """
        queryset.update(
            is_deleted=Case(
                When(is_deleted=True, then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            ),
            deleted_at=now(),
            deleted_by=request.user.username
        )
        self.message_user(request, f"{queryset.count()} object(s) soft-deleted.")
