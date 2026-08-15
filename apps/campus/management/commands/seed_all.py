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
        # 1. CREATE DEFAULT GROUPS
        # ============================================================

        created_groups = []
        existing_groups = []

        for group_value in GroupNamesEnum.values():

            group, is_created = Group.objects.get_or_create(
                name=group_value
            )

            if is_created:
                created_groups.append(group_value)
            else:
                existing_groups.append(group_value)

        if created_groups:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created groups: {', '.join(created_groups)}"
                )
            )

        if existing_groups:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Groups already exist: {', '.join(existing_groups)}"
                )
            )

        # ============================================================
        # 2. VERIFY DEFAULT ADMIN USER
        # ============================================================

        admin_email = "admin@admin.com"
        admin_group_name = GroupNamesEnum.ADMIN.value

        try:
            admin_user = User.objects.get(
                email=admin_email
            )

        except User.DoesNotExist:
            raise CommandError(
                f"Admin user with email '{admin_email}' does not exist. "
                "Please create a superuser first using "
                "'python manage.py createsuperuser'."
            )

        # ------------------------------------------------------------
        # Verify admin group
        # ------------------------------------------------------------

        if not admin_user.groups.filter(
            name=admin_group_name
        ).exists():

            raise CommandError(
                f"User '{admin_email}' is not in the "
                f"'{admin_group_name}' group. "
                f"Please add them to the group using: "
                f"user.groups.add("
                f"Group.objects.get(name='{admin_group_name}')"
                f")"
            )

        # ------------------------------------------------------------
        # Verify superuser/staff permissions
        # ------------------------------------------------------------

        if not admin_user.is_superuser or not admin_user.is_staff:

            raise CommandError(
                f"User '{admin_email}' must have "
                "is_superuser=True and is_staff=True. "
                "Please set these permissions via the admin panel "
                "or shell."
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
        # 3. LOAD LOOKUPS.JSON
        # ============================================================

        base_dir = Path(__file__).resolve().parents[4]

        lookups_path = (
            base_dir
            / "utils"
            / "lookups.json"
        )

        if not lookups_path.exists():

            raise CommandError(
                f"lookups.json not found at {lookups_path}"
            )

        with open(
            lookups_path,
            encoding="utf-8"
        ) as lookup_file:

            lookup_data = json.load(lookup_file)

        # ------------------------------------------------------------
        # Extract lookup sections
        # ------------------------------------------------------------

        categories_data = lookup_data.get(
            "categories",
            []
        )

        hotspots = lookup_data.get(
            "campus_hotspots",
            []
        )

        badges = lookup_data.get(
            "badges",
            []
        )

        points_data = lookup_data.get(
            "points",
            []
        )

        feature_flags_data = lookup_data.get(
            "featureflag",
            []
        )

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
        # 5. SEED CATEGORIES, SUBCATEGORIES, HOTSPOTS,
        #    BADGES AND FEATURE FLAGS
        # ============================================================

        with transaction.atomic():

            # --------------------------------------------------------
            # Categories
            # --------------------------------------------------------

            for cat_data in categories_data:

                slug = cat_data.get("slug")

                defaults = {
                    "name": cat_data.get(
                        "name",
                        ""
                    ),
                    "listing_type": cat_data.get(
                        "listing_type",
                        ""
                    ),
                    "icon": cat_data.get(
                        "icon",
                        ""
                    ),
                    "description": cat_data.get(
                        "description",
                        ""
                    ),
                    "sort_order": cat_data.get(
                        "sort_order",
                        0
                    ),
                }

                category, was_created = (
                    Category.objects.update_or_create(
                        slug=slug,
                        defaults=defaults,
                    )
                )

                if was_created:

                    created["categories"] += 1

                else:

                    updated["categories"] += 1

                # ----------------------------------------------------
                # Subcategories
                # ----------------------------------------------------

                subcategories = cat_data.get(
                    "subcategories",
                    []
                )

                for sub_data in subcategories:

                    sub_slug = sub_data.get(
                        "slug"
                    )

                    sub_defaults = {
                        "name": sub_data.get(
                            "name",
                            ""
                        ),
                        "icon": sub_data.get(
                            "icon",
                            ""
                        ),
                        "description": sub_data.get(
                            "description",
                            ""
                        ),
                        "sort_order": sub_data.get(
                            "sort_order",
                            0
                        ),
                        "category": category,
                    }

                    (
                        sub_obj,
                        sub_created,
                    ) = SubCategory.objects.update_or_create(
                        slug=sub_slug,
                        category=category,
                        defaults=sub_defaults,
                    )

                    if sub_created:

                        created["subcategories"] += 1

                    else:

                        updated["subcategories"] += 1

            # --------------------------------------------------------
            # Campus Hotspots
            # --------------------------------------------------------

            for hotspot in hotspots:

                defaults = {
                    "description": hotspot.get(
                        "description",
                        ""
                    ),
                    "sort_order": hotspot.get(
                        "sort_order",
                        0
                    ),
                }

                (
                    obj,
                    was_created,
                ) = CampusHotspot.objects.update_or_create(
                    name=hotspot.get(
                        "name",
                        ""
                    ),
                    defaults=defaults,
                )

                if was_created:

                    created["hotspots"] += 1

                else:

                    updated["hotspots"] += 1

            # --------------------------------------------------------
            # Badges
            # --------------------------------------------------------

            for badge in badges:

                icon_value = (
                    badge.get("icon")
                    or None
                )

                defaults = {
                    "description": badge.get(
                        "description",
                        ""
                    ),
                    "icon": icon_value,
                }

                (
                    obj,
                    was_created,
                ) = Badge.objects.update_or_create(
                    name=badge.get(
                        "name",
                        ""
                    ),
                    defaults=defaults,
                )

                if was_created:

                    created["badges"] += 1

                else:

                    updated["badges"] += 1

            # --------------------------------------------------------
            # Feature Flags
            # --------------------------------------------------------

            for flag_data in feature_flags_data:

                defaults = {
                    "description": flag_data.get(
                        "description",
                        ""
                    ),
                    "is_active": flag_data.get(
                        "is_active",
                        True
                    ),
                    "is_deleted": False,
                }

                (
                    obj,
                    was_created,
                ) = FeatureFlag.objects.update_or_create(
                    name=flag_data.get(
                        "name"
                    ),
                    defaults=defaults,
                )

                if was_created:

                    created["feature_flags"] += 1

                else:

                    updated["feature_flags"] += 1

        # ============================================================
        # 6. SEED POINT PACKAGES
        # ============================================================

        for pkg_data in points_data:

            defaults = {
                "price": pkg_data.get(
                    "price"
                ),
                "description": pkg_data.get(
                    "description",
                    ""
                ),
                "is_popular": pkg_data.get(
                    "is_popular",
                    False
                ),
                "is_best_value": pkg_data.get(
                    "is_best_value",
                    False
                ),
                "sort_order": pkg_data.get(
                    "sort_order",
                    0
                ),
            }

            (
                obj,
                was_created,
            ) = PointPackage.objects.update_or_create(
                points=pkg_data.get(
                    "points"
                ),
                defaults=defaults,
            )

            if was_created:

                created["point_packages"] += 1

            else:

                updated["point_packages"] += 1

        # ============================================================
        # 7. FINAL SUMMARY
        # ============================================================

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete:"
            )
        )

        self.stdout.write(
            f"  Categories: "
            f"{created['categories']} created, "
            f"{updated['categories']} updated"
        )

        self.stdout.write(
            f"  Subcategories: "
            f"{created['subcategories']} created, "
            f"{updated['subcategories']} updated"
        )

        self.stdout.write(
            f"  Campus hotspots: "
            f"{created['hotspots']} created, "
            f"{updated['hotspots']} updated"
        )

        self.stdout.write(
            f"  Badges: "
            f"{created['badges']} created, "
            f"{updated['badges']} updated"
        )

        self.stdout.write(
            f"  Feature flags: "
            f"{created['feature_flags']} created, "
            f"{updated['feature_flags']} updated"
        )

        self.stdout.write(
            f"  Point packages: "
            f"{created['point_packages']} created, "
            f"{updated['point_packages']} updated"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "No sample listings were created."
            )
        )