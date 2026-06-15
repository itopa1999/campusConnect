from django.db import models

from apps.users.manager import SoftDeleteManager


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)
    modified_by = models.CharField(max_length=100, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=100, null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        abstract = True