import json
import random
from pathlib import Path
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.campus.models import CampusHotspot, Category, Listing, ListingHotspot
from apps.users.models import Badge, User
from utils.enums import BadgeListingType, GroupNames, ListingStatusType, ListingType


class Command(BaseCommand):
    help = "Seed categories, campus hotspots, badges, and sample listings from utils/lookups.json"

    def handle(self, *args, **options):
        # ------------------- 1. Create default groups -------------------
        created_groups = []
        existing_groups = []
        for group_value in GroupNames.values():
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
        admin_group_name = GroupNames.ADMIN.value

        try:
            admin_user = User.objects.get(email=admin_email)
        except User.DoesNotExist:
            raise CommandError(
                f"Admin user with email '{admin_email}' does not exist. "
                "Please create a superuser first using 'python manage.py createsuperuser'."
            )

        # Check group membership
        if not admin_user.groups.filter(name=admin_group_name).exists():
            raise CommandError(
                f"User '{admin_email}' is not in the '{admin_group_name}' group. "
                f"Please add them to the group using: user.groups.add(Group.objects.get(name='{admin_group_name}'))"
            )

        # Check superuser and staff flags
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

        categories = lookup_data.get("categories", [])
        hotspots = lookup_data.get("campus_hotspots", [])
        badges = lookup_data.get("badges", [])
        listings_data = lookup_data.get("listings", [])   # sample listings

        created = {
            "categories": 0,
            "hotspots": 0,
            "badges": 0,
            "listings": 0,
        }
        updated = {
            "categories": 0,
            "hotspots": 0,
            "badges": 0,
            "listings": 0,
        }

        # ------------------- 4. Seed categories, hotspots, badges -------------------
        with transaction.atomic():
            for category in categories:
                defaults = {
                    "name": category.get("name", ""),
                    "icon": category.get("icon", ""),
                    "description": category.get("description", ""),
                    "sort_order": category.get("sort_order", 0),
                }
                obj, was_created = Category.objects.update_or_create(
                    slug=category.get("slug", ""),
                    defaults=defaults,
                )
                if was_created:
                    created["categories"] += 1
                else:
                    updated["categories"] += 1

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

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created['categories']} categories created, {updated['categories']} updated; "
            f"{created['hotspots']} hotspots created, {updated['hotspots']} updated; "
            f"{created['badges']} badges created, {updated['badges']} updated."
        ))

        # ------------------- 5. Seed sample listings -------------------

        # Ensure we have categories and hotspots
        if Category.objects.count() == 0 or CampusHotspot.objects.count() == 0:
            self.stdout.write(self.style.WARNING("Skipping listing seed: no categories or hotspots found."))
            return

        badge_choices = [choice[0] for choice in BadgeListingType.choices()]
        listing_status = ListingStatusType.ACTIVE.value
        listing_type = ListingType.SELL.value
        expires_in_10_years = timezone.now() + timedelta(days=3650)

        for item in listings_data:
            title = item.get("title")
            description = item.get("description", "")
            price = Decimal(item.get("price", 0))

            # Randomly pick a category and a badge
            category = random.choice(Category.objects.all())
            badge = random.choice(badge_choices)

            listing = Listing.objects.create(
                user=admin_user,
                category=category,
                title=title,
                description=description,
                price=price,
                badge=badge,
                listing_type=listing_type,
                status=listing_status,
                expires_at=expires_in_10_years,
                image=None,
            )

            # Pick 2 random hotspots (or fewer if not enough)
            all_hotspots = list(CampusHotspot.objects.all())
            if len(all_hotspots) >= 2:
                selected = random.sample(all_hotspots, 2)
            else:
                selected = all_hotspots
            for hotspot in selected:
                ListingHotspot.objects.create(listing=listing, hotspot=hotspot)

            created["listings"] += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created['listings']} sample listings."))