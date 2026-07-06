from __future__ import annotations

from django.conf import settings
from django.db.backends.signals import connection_created
from django.dispatch import receiver


def configure_sqlite_connection(connection) -> None:
    if connection.vendor != "sqlite":
        return

    busy_timeout_ms = max(1000, int(float(getattr(settings, "SQLITE_TIMEOUT_SECONDS", 20.0)) * 1000))
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")


@receiver(connection_created)
def apply_sqlite_pragmas(sender, connection, **kwargs):  # noqa: ARG001
    configure_sqlite_connection(connection)
