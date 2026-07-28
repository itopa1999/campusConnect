import json
from pathlib import Path
from django.conf import settings
from apps.users.models import TwoFactorMethod
from utils.base_result import BaseResultWithData
from utils.enums import TwoFactorMethodEnum

class TwoFactorQuery:

    @staticmethod
    def get_user_2fa_methods(request) -> BaseResultWithData:
        user = request.user

        # Load static methods from lookup.json
        lookup_path = Path(settings.BASE_DIR) / "utils" / "lookups.json"
        with open(lookup_path) as f:
            lookup_data = json.load(f)

        # Filter out "backup" – it's no longer a 2FA method
        static_methods = [
            m for m in lookup_data.get("2faMethods", [])
            if m.get("value") != "backup"
        ]

        # Fetch user's existing 2FA methods
        user_methods = {
            m.method: m for m in TwoFactorMethod.objects.filter(user=user)
        }

        # Build enriched response
        methods_list = []
        for method in static_methods:
            value = method["value"]

            # Defaults
            is_enabled = False
            can_enable = True

            # ─── TOTP ──────────────────────────────────────────
            if value == TwoFactorMethodEnum.TOTP.value:
                totp_method = user_methods.get(value)
                if totp_method:
                    is_enabled = totp_method.is_enabled
                    # can enable if secret exists (set up)
                    can_enable = bool(totp_method.secret)
                else:
                    can_enable = True   # can start fresh setup

            # ─── SMS ──────────────────────────────────────────
            elif value == TwoFactorMethodEnum.SMS.value:
                sms_method = user_methods.get(value)
                if sms_method:
                    is_enabled = sms_method.is_enabled
                can_enable = bool(user.phone)   # phone required

            # ─── EMAIL ────────────────────────────────────────
            elif value == TwoFactorMethodEnum.EMAIL.value:
                email_method = user_methods.get(value)
                if email_method:
                    is_enabled = email_method.is_enabled
                can_enable = bool(user.email)    # email required

            # ─── HARDWARE ─────────────────────────────────────
            elif value == TwoFactorMethodEnum.HARDWARE.value:
                hw_method = user_methods.get(value)
                if hw_method:
                    is_enabled = hw_method.is_enabled
                can_enable = True   # no prerequisites

            methods_list.append({
                "id": method["id"],
                "value": value,
                "name": method["name"],
                "description": method["description"],
                "icon": method["icon"],
                "is_enabled": is_enabled,
                "can_enable": can_enable,
            })

        return BaseResultWithData(
            message="User 2FA methods retrieved",
            data={
                "methods": methods_list
            },
            status_code=200
        )