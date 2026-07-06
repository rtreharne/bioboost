from __future__ import annotations

import base64
import binascii
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify
from openai import OpenAI, OpenAIError

from standalone.models import Course, CourseBlock


BLOCK_AVATAR_OBJECTIVE_LIMIT = 3
BLOCK_AVATAR_SIZE = "1024x1024"
BLOCK_AVATAR_OUTPUT_FORMAT = "png"
BLOCK_AVATAR_QUALITY = "low"


class BlockAvatarGenerationError(ValueError):
    pass


def _now():
    return timezone.now()


def set_block_avatar_generation_state(
    block_id: int,
    status: str,
    *,
    error: str = "",
    generated_at=None,
) -> None:
    updates: dict[str, object] = {
        "avatar_generation_status": status,
        "avatar_generation_error": str(error or ""),
        "updated_at": _now(),
    }
    if generated_at is not None:
        updates["avatar_generated_at"] = generated_at
    CourseBlock.objects.filter(pk=block_id).update(**updates)


def queue_block_avatar_generation(block: CourseBlock) -> None:
    set_block_avatar_generation_state(
        block.pk,
        CourseBlock.AvatarGenerationStatus.QUEUED,
        error="",
    )


def _normalized_context_line(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _block_avatar_prompt(block: CourseBlock) -> str:
    title = _normalized_context_line(block.title)
    summary = _normalized_context_line(block.summary)
    objectives = [
        _normalized_context_line(objective.text)
        for objective in list(block.learning_objectives.all())[:BLOCK_AVATAR_OBJECTIVE_LIMIT]
        if _normalized_context_line(objective.text)
    ]
    context_lines = [
        "Create a simple educational topic icon for a course content block.",
        "The icon must be memorable, minimal, and instantly recognizable at very small size.",
        "Use a single central subject or a tiny cluster of closely related elements only.",
        "Do not include any letters, words, numbers, labels, borders, frames, circles, or background scenery.",
        "Keep the composition centered with generous empty space around the icon.",
        "Use a transparent background.",
        "Avoid photorealism and avoid complex detail.",
        "Prefer crisp, friendly, high-contrast educational illustration with clean edges.",
        "",
        f"Course: {_normalized_context_line(block.course.title)}",
        f"Block title: {title or 'Untitled block'}",
    ]
    if summary:
        context_lines.append(f"Block summary: {summary}")
    if objectives:
        context_lines.append("Key learning points:")
        context_lines.extend(f"- {objective}" for objective in objectives)
    context_lines.extend(
        [
            "",
            "Return only the icon artwork itself on transparency.",
            "The icon will be displayed inside a small blue circular badge in a student chat sidebar.",
        ]
    )
    return "\n".join(context_lines)


def _response_data_items(response) -> list:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(response, dict):
        maybe_data = response.get("data")
        if isinstance(maybe_data, list):
            return maybe_data
    return []


def _item_value(item, key: str):
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _decode_block_avatar_image(response) -> bytes:
    data_items = _response_data_items(response)
    if not data_items:
        raise BlockAvatarGenerationError("OpenAI returned an empty block avatar payload.")
    b64_json = _item_value(data_items[0], "b64_json")
    if not b64_json:
        raise BlockAvatarGenerationError("OpenAI did not return base64 image data for the block avatar.")
    try:
        return base64.b64decode(b64_json, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise BlockAvatarGenerationError(f"OpenAI returned invalid block avatar image data ({exc}).") from exc


def _avatar_filename(block: CourseBlock) -> str:
    slug = slugify(block.title)[:60] or f"block-{block.pk}"
    unique_suffix = uuid.uuid4().hex[:12]
    suffix = Path(f"avatar.{BLOCK_AVATAR_OUTPUT_FORMAT}").suffix
    return f"{slug}-avatar-{unique_suffix}{suffix}"


def _openai_block_avatar_bytes(block: CourseBlock) -> bytes:
    if not settings.OPENAI_API_KEY:
        raise BlockAvatarGenerationError("Block avatar generation requires OPENAI_API_KEY.")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.images.generate(
        model=getattr(settings, "OPENAI_BLOCK_AVATAR_MODEL", "gpt-image-1.5"),
        prompt=_block_avatar_prompt(block),
        size=BLOCK_AVATAR_SIZE,
        background="transparent",
        output_format=BLOCK_AVATAR_OUTPUT_FORMAT,
        quality=BLOCK_AVATAR_QUALITY,
        user=f"course-block-{block.pk}",
    )
    return _decode_block_avatar_image(response)


def generate_and_store_block_avatar(block: CourseBlock, *, force: bool = False) -> bool:
    if not force and block.avatar_file:
        return False

    set_block_avatar_generation_state(
        block.pk,
        CourseBlock.AvatarGenerationStatus.RUNNING,
        error="",
    )

    try:
        image_bytes = _openai_block_avatar_bytes(block)
    except (BlockAvatarGenerationError, OpenAIError) as exc:
        set_block_avatar_generation_state(
            block.pk,
            CourseBlock.AvatarGenerationStatus.FAILED,
            error=str(exc),
        )
        return False
    except Exception as exc:  # noqa: BLE001
        set_block_avatar_generation_state(
            block.pk,
            CourseBlock.AvatarGenerationStatus.FAILED,
            error=str(exc),
        )
        return False

    previous_name = str(block.avatar_file.name or "")
    generated_at = _now()
    block.avatar_generation_status = CourseBlock.AvatarGenerationStatus.COMPLETED
    block.avatar_generation_error = ""
    block.avatar_generated_at = generated_at
    block.avatar_file.save(_avatar_filename(block), ContentFile(image_bytes), save=False)
    block.save(
        update_fields=[
            "avatar_file",
            "avatar_generation_status",
            "avatar_generation_error",
            "avatar_generated_at",
            "updated_at",
        ]
    )
    if previous_name and previous_name != block.avatar_file.name:
        try:
            block.avatar_file.storage.delete(previous_name)
        except Exception:  # noqa: BLE001
            pass
    return True


def generate_course_block_avatars(course: Course, *, force: bool = False) -> dict[str, int]:
    counts = {"generated": 0, "skipped": 0, "failed": 0}
    blocks = list(
        course.blocks.prefetch_related("learning_objectives").order_by("order", "created_at", "pk")
    )
    for block in blocks:
        should_attempt = force or not bool(block.avatar_file)
        if not should_attempt:
            counts["skipped"] += 1
            continue
        if generate_and_store_block_avatar(block, force=force):
            counts["generated"] += 1
        else:
            if force or not block.avatar_file:
                counts["failed"] += 1
            else:
                counts["skipped"] += 1
    return counts
