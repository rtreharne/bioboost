from django.conf import settings


def asset_version(request):
    return {
        "static_asset_version": getattr(settings, "STATIC_ASSET_VERSION", ""),
    }
