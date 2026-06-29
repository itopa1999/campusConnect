from apps.users.models import FeatureFlag

def is_feature_active(feature_name: str, user=None) -> bool:

    try:
        flag = FeatureFlag.objects.get(name=feature_name, is_deleted=False)
    except FeatureFlag.DoesNotExist:
        return False

    if not flag.is_active:
        return False

    if user is not None:
        return flag.users.filter(id=user.id).exists()

    return flag.users.count() == 0