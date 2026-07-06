import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import OperationalError, close_old_connections

from standalone.services.question_builder import run_question_bank_builder_cycle


class Command(BaseCommand):
    help = "Run the per-course background question bank builder loop."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single builder cycle and exit.",
        )

    def handle(self, *args, **options):
        once = bool(options.get("once"))
        poll_seconds = max(5, int(settings.QUESTION_BANK_BUILDER_POLL_SECONDS or 60))

        while True:
            try:
                results = run_question_bank_builder_cycle()
            except OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                close_old_connections()
                self.stderr.write("question-bank-builder skipped cycle because the SQLite database was locked")
                if once:
                    return
                time.sleep(min(5, poll_seconds))
                continue
            generated = sum(1 for result in results if result.generated)
            self.stdout.write(
                f"question-bank-builder cycle complete: scanned={len(results)} generated={generated}"
            )
            if once:
                return
            time.sleep(poll_seconds)
