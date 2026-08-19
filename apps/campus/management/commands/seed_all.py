import json
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management import BaseCommand, CommandError
from django.db import transaction

from apps.campus.models import CampusHotspot, Category, SubCategory
from apps.users.models import Badge, FeatureFlag, PointPackage, User
from utils.enums import GroupNamesEnum


class Command(BaseCommand):
    help = (
        "Seed categories, subcategories, campus hotspots, badges, "
        "feature flags, and point packages from utils/lookups.json"
    )

    def handle(self, *args, **options):

        # ============================================================
        # 1. CREATE DEFAULT GROUPS (unchanged - keep as is)
        # ============================================================

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

        # ============================================================
        # 2. VERIFY DEFAULT ADMIN USER (unchanged)
        # ============================================================

        admin_email = "admin@admin.com"
        admin_group_name = GroupNamesEnum.ADMIN.value

        try:
            admin_user = User.objects.get(email=admin_email)
        except User.DoesNotExist:
            raise CommandError(
                f"Admin user with email '{admin_email}' does not exist. "
                "Please create a superuser first using "
                "'python manage.py createsuperuser'."
            )

        if not admin_user.groups.filter(name=admin_group_name).exists():
            raise CommandError(
                f"User '{admin_email}' is not in the '{admin_group_name}' group. "
                f"Please add them to the group using: "
                f"user.groups.add(Group.objects.get(name='{admin_group_name}'))"
            )

        if not admin_user.is_superuser or not admin_user.is_staff:
            raise CommandError(
                f"User '{admin_email}' must have is_superuser=True and is_staff=True. "
                "Please set these permissions via the admin panel or shell."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user '{admin_email}' verified: "
                f"group={admin_group_name}, "
                f"superuser={admin_user.is_superuser}, "
                f"staff={admin_user.is_staff}"
            )
        )

        # ============================================================
        # 3. LOAD LOOKUPS.JSON (unchanged)
        # ============================================================

        base_dir = Path(__file__).resolve().parents[4]
        lookups_path = base_dir / "utils" / "lookups.json"

        if not lookups_path.exists():
            raise CommandError(f"lookups.json not found at {lookups_path}")

        with open(lookups_path, encoding="utf-8") as lookup_file:
            lookup_data = json.load(lookup_file)

        categories_data = lookup_data.get("categories", [])
        hotspots = lookup_data.get("campus_hotspots", [])
        badges = lookup_data.get("badges", [])
        points_data = lookup_data.get("points", [])
        feature_flags_data = lookup_data.get("featureflag", [])

        # ============================================================
        # 4. INITIALIZE COUNTERS
        # ============================================================

        created = {
            "categories": 0,
            "subcategories": 0,
            "hotspots": 0,
            "badges": 0,
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

        # ============================================================
        # 5. SEED WITH BULK OPERATIONS
        # ============================================================

        with transaction.atomic():

            # --------------------------------------------------------
            # 5a. Categories
            # --------------------------------------------------------
            existing_categories = {cat.slug: cat for cat in Category.objects.all()}
            categories_to_create = []
            categories_to_update = []

            for cat_data in categories_data:
                slug = cat_data["slug"]
                defaults = {
                    "name": cat_data.get("name", ""),
                    "listing_type": cat_data.get("listing_type", ""),
                    "icon": cat_data.get("icon", ""),
                    "description": cat_data.get("description", ""),
                    "sort_order": cat_data.get("sort_order", 0),
                }

                if slug in existing_categories:
                    category = existing_categories[slug]
                    # Update the object in memory
                    for field, value in defaults.items():
                        setattr(category, field, value)
                    categories_to_update.append(category)
                else:
                    # Create a new Category instance (without saving)
                    categories_to_create.append(Category(slug=slug, **defaults))

            # Bulk insert new categories
            if categories_to_create:
                Category.objects.bulk_create(categories_to_create)
                created["categories"] = len(categories_to_create)

            # Bulk update existing categories
            if categories_to_update:
                Category.objects.bulk_update(
                    categories_to_update,
                    fields=["name", "listing_type", "icon", "description", "sort_order"]
                )
                updated["categories"] = len(categories_to_update)

            # Refresh our dict with the newly created objects (which now have IDs)
            all_categories = {cat.slug: cat for cat in Category.objects.all()}

            # --------------------------------------------------------
            # 5b. Subcategories
            # --------------------------------------------------------
            # Unique key for subcategory: (slug, category_id)
            existing_subcategories = {
                (sub.slug, sub.category_id): sub
                for sub in SubCategory.objects.select_related("category").all()
            }
            subs_to_create = []
            subs_to_update = []

            for cat_data in categories_data:
                category_slug = cat_data["slug"]
                category = all_categories.get(category_slug)
                if not category:
                    # Should not happen, but skip gracefully
                    continue

                for sub_data in cat_data.get("subcategories", []):
                    sub_slug = sub_data["slug"]
                    key = (sub_slug, category.id)
                    defaults = {
                        "name": sub_data.get("name", ""),
                        "icon": sub_data.get("icon", ""),
                        "description": sub_data.get("description", ""),
                        "sort_order": sub_data.get("sort_order", 0),
                        "category": category,
                    }

                    if key in existing_subcategories:
                        sub_obj = existing_subcategories[key]
                        for field, value in defaults.items():
                            setattr(sub_obj, field, value)
                        subs_to_update.append(sub_obj)
                    else:
                        # category is already set in defaults
                        subs_to_create.append(SubCategory(slug=sub_slug, **defaults))

            if subs_to_create:
                SubCategory.objects.bulk_create(subs_to_create)
                created["subcategories"] = len(subs_to_create)

            if subs_to_update:
                SubCategory.objects.bulk_update(
                    subs_to_update,
                    fields=["name", "icon", "description", "sort_order", "category"]
                )
                updated["subcategories"] = len(subs_to_update)

            # --------------------------------------------------------
            # 5c. Campus Hotspots
            # --------------------------------------------------------
            # Unique key: name
            existing_hotspots = {hs.name: hs for hs in CampusHotspot.objects.all()}
            hotspots_to_create = []
            hotspots_to_update = []

            for hotspot in hotspots:
                name = hotspot.get("name", "")
                if not name:
                    continue
                defaults = {
                    "description": hotspot.get("description", ""),
                    "sort_order": hotspot.get("sort_order", 0),
                }

                if name in existing_hotspots:
                    obj = existing_hotspots[name]
                    for field, value in defaults.items():
                        setattr(obj, field, value)
                    hotspots_to_update.append(obj)
                else:
                    hotspots_to_create.append(CampusHotspot(name=name, **defaults))

            if hotspots_to_create:
                CampusHotspot.objects.bulk_create(hotspots_to_create)
                created["hotspots"] = len(hotspots_to_create)

            if hotspots_to_update:
                CampusHotspot.objects.bulk_update(
                    hotspots_to_update,
                    fields=["description", "sort_order"]
                )
                updated["hotspots"] = len(hotspots_to_update)

            # --------------------------------------------------------
            # 5d. Badges
            # --------------------------------------------------------
            # Unique key: name
            existing_badges = {b.name: b for b in Badge.objects.all()}
            badges_to_create = []
            badges_to_update = []

            for badge in badges:
                name = badge.get("name", "")
                if not name:
                    continue
                defaults = {
                    "description": badge.get("description", ""),
                    "icon": badge.get("icon") or None,
                }

                if name in existing_badges:
                    obj = existing_badges[name]
                    for field, value in defaults.items():
                        setattr(obj, field, value)
                    badges_to_update.append(obj)
                else:
                    badges_to_create.append(Badge(name=name, **defaults))

            if badges_to_create:
                Badge.objects.bulk_create(badges_to_create)
                created["badges"] = len(badges_to_create)

            if badges_to_update:
                Badge.objects.bulk_update(
                    badges_to_update,
                    fields=["description", "icon"]
                )
                updated["badges"] = len(badges_to_update)

            # --------------------------------------------------------
            # 5e. Feature Flags
            # --------------------------------------------------------
            # Unique key: name
            existing_flags = {f.name: f for f in FeatureFlag.objects.all()}
            flags_to_create = []
            flags_to_update = []

            for flag_data in feature_flags_data:
                name = flag_data.get("name")
                if not name:
                    continue
                defaults = {
                    "description": flag_data.get("description", ""),
                    "is_active": flag_data.get("is_active", True),
                    "is_deleted": False,
                }

                if name in existing_flags:
                    obj = existing_flags[name]
                    for field, value in defaults.items():
                        setattr(obj, field, value)
                    flags_to_update.append(obj)
                else:
                    flags_to_create.append(FeatureFlag(name=name, **defaults))

            if flags_to_create:
                FeatureFlag.objects.bulk_create(flags_to_create)
                created["feature_flags"] = len(flags_to_create)

            if flags_to_update:
                FeatureFlag.objects.bulk_update(
                    flags_to_update,
                    fields=["description", "is_active", "is_deleted"]
                )
                updated["feature_flags"] = len(flags_to_update)

        # ============================================================
        # 6. SEED POINT PACKAGES (outside the transaction, as before)
        # ============================================================
        # Unique key: points
        existing_packages = {p.points: p for p in PointPackage.objects.all()}
        packages_to_create = []
        packages_to_update = []

        for pkg_data in points_data:
            points = pkg_data.get("points")
            if points is None:
                continue
            defaults = {
                "price": pkg_data.get("price"),
                "description": pkg_data.get("description", ""),
                "is_popular": pkg_data.get("is_popular", False),
                "is_best_value": pkg_data.get("is_best_value", False),
                "sort_order": pkg_data.get("sort_order", 0),
            }

            if points in existing_packages:
                obj = existing_packages[points]
                for field, value in defaults.items():
                    setattr(obj, field, value)
                packages_to_update.append(obj)
            else:
                packages_to_create.append(PointPackage(points=points, **defaults))

        if packages_to_create:
            PointPackage.objects.bulk_create(packages_to_create)
            created["point_packages"] = len(packages_to_create)

        if packages_to_update:
            PointPackage.objects.bulk_update(
                packages_to_update,
                fields=["price", "description", "is_popular", "is_best_value", "sort_order"]
            )
            updated["point_packages"] = len(packages_to_update)

        # ============================================================
        # 7. FINAL SUMMARY (unchanged)
        # ============================================================

        self.stdout.write(self.style.SUCCESS("Seed complete:"))
        self.stdout.write(
            f"  Categories: {created['categories']} created, {updated['categories']} updated"
        )
        self.stdout.write(
            f"  Subcategories: {created['subcategories']} created, {updated['subcategories']} updated"
        )
        self.stdout.write(
            f"  Campus hotspots: {created['hotspots']} created, {updated['hotspots']} updated"
        )
        self.stdout.write(
            f"  Badges: {created['badges']} created, {updated['badges']} updated"
        )
        self.stdout.write(
            f"  Feature flags: {created['feature_flags']} created, {updated['feature_flags']} updated"
        )
        self.stdout.write(
            f"  Point packages: {created['point_packages']} created, {updated['point_packages']} updated"
        )
        self.stdout.write(
            self.style.SUCCESS("No sample listings were created.")
        )