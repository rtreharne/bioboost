from django.core.management.base import BaseCommand, CommandError

from standalone.models import CourseBlock
from standalone.services.block_avatars import generate_and_store_block_avatar


class Command(BaseCommand):
    help = "Generate or refresh stored OpenAI avatars for course blocks."

    def add_arguments(self, parser):
        parser.add_argument("--course-id", type=int, dest="course_id")
        parser.add_argument("--block-id", type=int, dest="block_id")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate avatars even when a block already has one stored.",
        )

    def handle(self, *args, **options):
        course_id = options.get("course_id")
        block_id = options.get("block_id")
        force = bool(options.get("force"))

        queryset = CourseBlock.objects.select_related("course").prefetch_related("learning_objectives").order_by("course_id", "order", "pk")
        if course_id is not None:
            queryset = queryset.filter(course_id=course_id)
        if block_id is not None:
            queryset = queryset.filter(pk=block_id)

        blocks = list(queryset)
        if not blocks:
            raise CommandError("No matching course blocks were found.")

        generated = 0
        skipped = 0
        failed = 0

        for block in blocks:
            if not force and block.avatar_file:
                skipped += 1
                continue
            if generate_and_store_block_avatar(block, force=force):
                generated += 1
            else:
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"block-avatar generation complete: scanned={len(blocks)} generated={generated} skipped={skipped} failed={failed}"
            )
        )
