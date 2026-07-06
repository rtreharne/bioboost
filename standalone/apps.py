import importlib

from django.apps import AppConfig


class StandaloneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "standalone"

    def ready(self):
        importlib.import_module("standalone.sqlite")
