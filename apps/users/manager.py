from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import Group
from django.db import models

from utils.enums import GroupNamesEnum


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that automatically filters out soft-deleted objects"""
    def active(self):
        """Return only non-deleted objects"""
        return self.filter(is_deleted=False)
    
    def deleted(self):
        """Return only deleted objects"""
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted objects by default"""
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)
    
    def all_including_deleted(self):
        """Return all objects including deleted ones"""
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def deleted_only(self):
        """Return only deleted objects"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)


class UserManager(SoftDeleteManager, BaseUserManager):
    use_in_migrations = True
    
    def create_user(self, email, password=None, group_name=None, **extra_fields):
        if not email:
            raise ValueError('email is required')
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        
        if group_name is None:
            group_name = GroupNamesEnum.ADMIN.value if extra_fields.get('is_superuser') else GroupNamesEnum.STUDENT.value

        group, created = Group.objects.get_or_create(name=group_name)
        user.save(using=self._db)
        user.groups.add(group)
        return user
    
    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(('super user must have is_staff true'))
        
        return self.create_user(email, password, **extra_fields)