import json
from pathlib import Path

from django.core.management import BaseCommand, CommandError
from django.db import transaction

from apps.campus.models import CampusHotspot, Category
from apps.users.models import Badge


class Command(BaseCommand):
    help = "Seed categories, campus hotspots, and badges from utils/lookups.json"

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[4]
        lookups_path = base_dir / "utils" / "lookups.json"

        if not lookups_path.exists():
            raise CommandError(f"lookups.json not found at {lookups_path}")

        with open(lookups_path, encoding="utf-8") as lookup_file:
            lookup_data = json.load(lookup_file)

        categories = lookup_data.get("categories", [])
        hotspots = lookup_data.get("campus_hotspots", [])
        badges = lookup_data.get("badges", [])

        created = {
            "categories": 0,
            "hotspots": 0,
            "badges": 0,
        }
        updated = {
            "categories": 0,
            "hotspots": 0,
            "badges": 0,
        }

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
