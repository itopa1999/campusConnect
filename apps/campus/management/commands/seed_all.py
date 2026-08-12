import json
import random
from pathlib import Path
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.campus.models import CampusHotspot, Category, Listing, ListingHotspot, SubCategory
from apps.users.models import Badge, FeatureFlag, PointPackage, User
from utils.enums import BadgeListingTypeEnum, GroupNamesEnum, ListingStatusTypeEnum, ListingTypeEnum


class Command(BaseCommand):
    help = "Seed categories, subcategories, campus hotspots, badges, feature flags, point packages, and sample listings from utils/lookups.json"

    def handle(self, *args, **options):
        # ------------------- 1. Create default groups -------------------
        created_groups = []
        existing_groups = []
        for group_value in GroupNamesEnum.values():
            group, is_created = Group.objects.get_or_create(name=group_value)
            if is_created:
                created_groups.append(group_value)
            else:
                existing_groups.append(group_value)

        if created_groups:
            self.stdout.write(self.style.SUCCESS(f"Created groups: {', '.join(created_groups)}"))
        if existing_groups:
            self.stdout.write(self.style.SUCCESS(f"Groups already exist: {', '.join(existing_groups)}"))

        # ------------------- 2. Verified admin superuser -------------------
        admin_email = "admin@admin.com"
        admin_group_name = GroupNamesEnum.ADMIN.value

        try:
            admin_user = User.objects.get(email=admin_email)
        except User.DoesNotExist:
            raise CommandError(
                f"Admin user with email '{admin_email}' does not exist. "
                "Please create a superuser first using 'python manage.py createsuperuser'."
            )

        if not admin_user.groups.filter(name=admin_group_name).exists():
            raise CommandError(
                f"User '{admin_email}' is not in the '{admin_group_name}' group. "
                f"Please add them to the group using: user.groups.add(Group.objects.get(name='{admin_group_name}'))"
            )

        if not admin_user.is_superuser or not admin_user.is_staff:
            raise CommandError(
                f"User '{admin_email}' must have is_superuser=True and is_staff=True. "
                "Please set these permissions via the admin panel or shell."
            )

        self.stdout.write(self.style.SUCCESS(
            f"Admin user '{admin_email}' verified: group={admin_group_name}, "
            f"superuser={admin_user.is_superuser}, staff={admin_user.is_staff}"
        ))

        # ------------------- 3. Load lookups.json -------------------
        base_dir = Path(__file__).resolve().parents[4]
        lookups_path = base_dir / "utils" / "lookups.json"

        if not lookups_path.exists():
            raise CommandError(f"lookups.json not found at {lookups_path}")

        with open(lookups_path, encoding="utf-8") as lookup_file:
            lookup_data = json.load(lookup_file)

        categories_data = lookup_data.get("categories", [])
        hotspots = lookup_data.get("campus_hotspots", [])
        badges = lookup_data.get("badges", [])
        listings_data = lookup_data.get("listings", [])
        points_data = lookup_data.get("points", [])
        feature_flags_data = lookup_data.get("featureflag", [])

        created = {
            "categories": 0,
            "subcategories": 0,
            "hotspots": 0,
            "badges": 0,
            "listings_created": 0,
            "listings_updated": 0,
            "point_packages": 0,
            "feature_flags": 0,
        }
        updated = {
            "categories": 0,
            "subcategories": 0,
            "hotspots": 0,
            "badges": 0,
            "point_packages": 0,
            "feature_flags": 0,
        }

        # ------------------- 4. Seed categories, subcategories, hotspots, badges, feature flags -------------------
        with transaction.atomic():
            # First, create/update categories and store them in a dict for later subcategory association
            category_map = {}

            for cat_data in categories_data:
                slug = cat_data.get("slug")
                defaults = {
                    "name": cat_data.get("name", ""),
                    "icon": cat_data.get("icon", ""),
                    "description": cat_data.get("description", ""),
                    "sort_order": cat_data.get("sort_order", 0),
                }
                category, was_created = Category.objects.update_or_create(
                    slug=slug,
                    defaults=defaults,
                )
                category_map[slug] = category
                if was_created:
                    created["categories"] += 1
                else:
                    updated["categories"] += 1

                # Now seed subcategories for this category
                subcategories = cat_data.get("subcategories", [])
                for sub_data in subcategories:
                    sub_slug = sub_data.get("slug")
                    sub_defaults = {
                        "name": sub_data.get("name", ""),
                        "description": sub_data.get("description", ""),
                        "sort_order": sub_data.get("sort_order", 0),
                        "category": category,   # link to parent
                    }
                    sub_obj, sub_created = SubCategory.objects.update_or_create(
                        slug=sub_slug,
                        category=category,
                        defaults=sub_defaults,
                    )
                    if sub_created:
                        created["subcategories"] += 1
                    else:
                        updated["subcategories"] += 1

            # Hotspots
            for hotspot in hotspots:
                defaults = {
                    "description": hotspot.get("description", ""),
                    "sort_order": hotspot.get("sort_order", 0),
                }
                obj, was_created = CampusHotspot.objects.update_or_create(
                    name=hotspot.get("name", ""),
                    defaults=defaults,
                )
                if was_created:
                    created["hotspots"] += 1
                else:
                    updated["hotspots"] += 1

            # Badges
            for badge in badges:
                icon_value = badge.get("icon") or None
                defaults = {
                    "description": badge.get("description", ""),
                    "icon": icon_value,
                }
                obj, was_created = Badge.objects.update_or_create(
                    name=badge.get("name", ""),
                    defaults=defaults,
                )
                if was_created:
                    created["badges"] += 1
                else:
                    updated["badges"] += 1

            # Feature Flags
            for flag_data in feature_flags_data:
                defaults = {
                    "description": flag_data.get("description", ""),
                    "is_active": flag_data.get("is_active", True),
                    "is_deleted": False,
                }
                obj, was_created = FeatureFlag.objects.update_or_create(
                    name=flag_data.get("name"),
                    defaults=defaults,
                )
                if was_created:
                    created["feature_flags"] += 1
                else:
                    updated["feature_flags"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created['categories']} categories created, {updated['categories']} updated; "
            f"{created['subcategories']} subcategories created, {updated['subcategories']} updated; "
            f"{created['hotspots']} hotspots created, {updated['hotspots']} updated; "
            f"{created['badges']} badges created, {updated['badges']} updated; "
            f"{created['feature_flags']} feature flags created, {updated['feature_flags']} updated."
        ))

        # ------------------- 5. Seed sample listings with subcategories -------------------
        if Category.objects.count() == 0 or CampusHotspot.objects.count() == 0:
            self.stdout.write(self.style.WARNING("Skipping listing seed: no categories or hotspots found."))
            return

        badge_choices = [choice[0] for choice in BadgeListingTypeEnum.choices()]
        listing_status = ListingStatusTypeEnum.ACTIVE.value
        listing_type = ListingTypeEnum.SELL.value
        expires_in_10_years = timezone.now() + timedelta(days=3650)

        # Get all subcategories to potentially assign to listings
        all_subcategories = list(SubCategory.objects.all())

        for item in listings_data:
            title = item.get("title")
            description = item.get("description", "")
            price = Decimal(item.get("price", 0))

            category = random.choice(Category.objects.all())
            badge = random.choice(badge_choices)

            # Optionally assign a random subcategory (if available)
            subcategory = None
            if all_subcategories:
                # Filter subcategories belonging to the chosen category
                category_subcategories = [sc for sc in all_subcategories if sc.category == category]
                if category_subcategories:
                    subcategory = random.choice(category_subcategories)

            listing, was_created = Listing.objects.update_or_create(
                title=title,
                user=admin_user,
                defaults={
                    "category": category,
                    "subcategory": subcategory,
                    "description": description,
                    "price": price,
                    "badge": badge,
                    "listing_type": listing_type,
                    "status": listing_status,
                    "expires_at": expires_in_10_years,
                    "image": None,
                }
            )

            if was_created:
                created["listings_created"] += 1
            else:
                created["listings_updated"] += 1

            all_hotspots = list(CampusHotspot.objects.all())
            if len(all_hotspots) >= 2:
                selected = random.sample(all_hotspots, 2)
            else:
                selected = all_hotspots

            for hotspot in selected:
                ListingHotspot.objects.get_or_create(
                    listing=listing,
                    hotspot=hotspot
                )

        self.stdout.write(self.style.SUCCESS(
            f"Listings seeded: {created['listings_created']} created, {created['listings_updated']} updated."
        ))

        # ------------------- 6. Seed point packages -------------------
        for pkg_data in points_data:
            defaults = {
                "price": pkg_data.get("price"),
                "description": pkg_data.get("description", ""),
                "is_popular": pkg_data.get("is_popular", False),
                "is_best_value": pkg_data.get("is_best_value", False),
                "sort_order": pkg_data.get("sort_order", 0),
            }
            obj, was_created = PointPackage.objects.update_or_create(
                points=pkg_data.get("points"),
                defaults=defaults,
            )
            if was_created:
                created["point_packages"] += 1
            else:
                updated["point_packages"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created['point_packages']} point packages, {updated['point_packages']} updated."
        ))