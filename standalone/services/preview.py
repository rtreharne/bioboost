import json
import math
import random
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from openai import OpenAI

from standalone.models import (
    Course,
    CourseBlock,
    CourseBlockCollection,
    LearningObjective,
    LearningObjectiveCorrection,
    PracticeAttemptQuestion,
    QuestionBankItem,
)
from standalone.services.guidance import build_chat_guidance_prompt, merge_assistant_guidance, sanitize_assistant_guidance
from standalone.services.math_questions import math_options_equivalent
from standalone.services.practice_scoring import (
    combine_block_practice_metrics,
    engagement_release_date,
    weighted_practice_score,
    base_practice_weights,
)
from standalone.services.question_builder import course_question_generation_budget, live_generation_unavailable_message
from standalone.services.numeric_questions import format_numeric_answer_feedback, regenerate_stored_numeric_feedback
from standalone.services.questions import (
    QuestionGenerationError,
    QuestionGenerationUnavailableError,
    _preferred_standard_generated_question_type,
    _trace_generation,
    block_has_coding_signal,
    coding_question_matches_expected_language,
    coding_question_quality_sort_key,
    further_study_questions_for_chat,
    further_study_questions_for_question,
    generate_question_pair_for_block,
    normalize_explanation_text,
    preferred_coding_language_for_block,
    question_quality_sort_key,
)
from standalone.services.projects import serialize_projects_for_blocks


PREVIEW_SESSION_KEY = "standalone_student_preview"
PREVIEW_ENROLLMENT_KEY = "preview"
PREVIEW_RETRY_COMPLETION_GAP = 3
PREVIEW_CHAT_RETRIEVAL_LIMIT = 6
PREVIEW_CHAT_HISTORY_LIMIT = 6
PREVIEW_INAPPROPRIATE_MESSAGE_WARNING = "Please keep messages respectful and appropriate. All conversations are logged and auditable by teachers."
PREVIEW_KEEP_GOING_LINES = (
    "Hit Quiz to keep going!",
    "Ready for another one? Hit Quiz.",
    "Keep the streak going. Hit Quiz.",
    "Want the next question? Tap Quiz.",
    "On to the next one. Hit Quiz.",
)
PREVIEW_KEEP_GOING_DELAY = timedelta(minutes=5)
WAQ_ALIGNMENT_THRESHOLD = 0.75
PREVIEW_WAQ_CLOSE_THRESHOLD = 0.55
PREVIEW_WAQ_MIN_SUBSTANTIVE_WORDS = 3
PREVIEW_WAQ_OPENAI_DRAFT_MIN_CHARS = 24
PREVIEW_WAQ_OPENAI_CHECK_INTERVAL = 12
CODING_QUESTION_REQUEST = "coding"
PREVIEW_QUESTION_TYPE_PRIORITY = {
    QuestionBankItem.QuestionType.NUM: 0,
    QuestionBankItem.QuestionType.MAQ: 1,
    QuestionBankItem.QuestionType.WAQ: 2,
    QuestionBankItem.QuestionType.MCQ: 3,
}
PREVIEW_STATS_QUESTION_TYPE_ORDER = {
    QuestionBankItem.QuestionType.MCQ: 0,
    QuestionBankItem.QuestionType.NUM: 1,
    QuestionBankItem.QuestionType.MAQ: 2,
    QuestionBankItem.QuestionType.WAQ: 3,
}
PREVIEW_BLOCK_THREAD_KIND = "block"
PREVIEW_COLLECTION_THREAD_KIND = "collection"


def _empty_course_state() -> dict:
    return {
        "completion_sequence": 0,
        "message_counter": 0,
        "question_states": {},
        "flagged_question_ids": [],
        "transcripts": {},
        "pending_questions": {},
        "written_answer_drafts": {},
        "completed_events": [],
        "progress_milestones": {},
        "collection_threads": {},
    }


def _default_question_state(question_id: int) -> dict:
    return {
        "enrollment": PREVIEW_ENROLLMENT_KEY,
        "question": question_id,
        "times_presented": 0,
        "times_correct": 0,
        "times_incorrect": 0,
        "last_presented_sequence": 0,
        "retired_at": None,
    }


def _question_state(course_state: dict, question_id: int) -> dict:
    states = course_state.setdefault("question_states", {})
    return states.setdefault(str(question_id), _default_question_state(question_id))


def _course_state(request, course: Course) -> dict:
    preview_root = request.session.setdefault(PREVIEW_SESSION_KEY, {})
    return preview_root.setdefault(str(course.pk), _empty_course_state())


def _next_message_id(course_state: dict) -> str:
    course_state["message_counter"] = course_state.get("message_counter", 0) + 1
    return f"preview-message-{course_state['message_counter']}"


def _welcome_message_text(title: str) -> str:
    return (
        f'Welcome to {title}. Tap the "Quiz" button to generate a quiz question for this topic, '
        "or ask about anything in the course."
    )


def _block_welcome_message_text(block_title: str) -> str:
    return _welcome_message_text(block_title)


def _collection_welcome_message_text(collection_title: str) -> str:
    return _welcome_message_text(collection_title)


def _ensure_block_transcript(course_state: dict, block: CourseBlock) -> list[dict]:
    transcripts = course_state.setdefault("transcripts", {})
    transcript = transcripts.setdefault(str(block.pk), [])
    if not transcript:
        transcript.append(
            {
                "id": _next_message_id(course_state),
                "created_at": timezone.now().isoformat(),
                "role": "assistant",
                "kind": "text",
                "thread_kind": PREVIEW_BLOCK_THREAD_KIND,
                "thread_id": block.pk,
                "text": _block_welcome_message_text(block.title),
                "is_block_welcome": True,
                "inline_cta_label": "Test Mode",
                "source_blocks": [block.title],
            }
        )
    return transcript


def _collection_thread_state(course_state: dict, collection: CourseBlockCollection) -> dict:
    return course_state.setdefault("collection_threads", {}).setdefault(
        str(collection.pk),
        {
            "transcript": [],
            "pending_question_id": None,
        },
    )


def _ensure_collection_transcript(course_state: dict, collection: CourseBlockCollection) -> list[dict]:
    thread_state = _collection_thread_state(course_state, collection)
    transcript = thread_state.setdefault("transcript", [])
    if not transcript:
        transcript.append(
            {
                "id": _next_message_id(course_state),
                "created_at": timezone.now().isoformat(),
                "role": "assistant",
                "kind": "text",
                "thread_kind": PREVIEW_COLLECTION_THREAD_KIND,
                "thread_id": collection.pk,
                "text": _collection_welcome_message_text(collection.title),
                "is_collection_welcome": True,
                "source_blocks": [collection.title],
            }
        )
    return transcript


def _append_message(course_state: dict, block: CourseBlock, role: str, kind: str, **data) -> dict:
    transcript = _ensure_block_transcript(course_state, block)
    message = {
        "id": _next_message_id(course_state),
        "created_at": timezone.now().isoformat(),
        "role": role,
        "kind": kind,
        "thread_kind": PREVIEW_BLOCK_THREAD_KIND,
        "thread_id": block.pk,
        **data,
    }
    transcript.append(message)
    return message


def _append_collection_message(course_state: dict, collection: CourseBlockCollection, role: str, kind: str, **data) -> dict:
    transcript = _ensure_collection_transcript(course_state, collection)
    message = {
        "id": _next_message_id(course_state),
        "created_at": timezone.now().isoformat(),
        "role": role,
        "kind": kind,
        "thread_kind": PREVIEW_COLLECTION_THREAD_KIND,
        "thread_id": collection.pk,
        **data,
    }
    transcript.append(message)
    return message


def _block_progress_milestones(course_state: dict, block: CourseBlock) -> dict:
    milestone_root = course_state.setdefault("progress_milestones", {})
    return milestone_root.setdefault(
        str(block.pk),
        {
            "coverage_complete_announced": False,
            "engagement_complete_announced": False,
        },
    )


def _first_active_block(course: Course):
    blocks = list(course.blocks.all())
    if not blocks:
        return None
    for block in blocks:
        if _block_is_accessible(course, block):
            return block
    return blocks[0]


def _preview_blocks(course: Course):
    return list(course.blocks.select_related("config").prefetch_related("learning_objectives").order_by("order", "created_at"))


def _collection_blocks_for_preview(course: Course, collection: CourseBlockCollection, blocks: list[CourseBlock] | None = None) -> list[CourseBlock]:
    preview_blocks = blocks or _preview_blocks(course)
    collection_block_ids = set(
        collection.blocks.order_by("order", "created_at", "pk").values_list("pk", flat=True)
    )
    return [
        block
        for block in preview_blocks
        if block.pk in collection_block_ids and _block_is_accessible(course, block)
    ]


def _flagged_question_ids(course_state: dict) -> set[int]:
    return {int(question_id) for question_id in course_state.get("flagged_question_ids", [])}


def _written_answer_draft(course_state: dict, question_id: int) -> dict:
    drafts = course_state.setdefault("written_answer_drafts", {})
    return drafts.setdefault(
        str(question_id),
        {
            "answer_text": "",
            "alignment_score": 0,
            "alignment_state": "drafting",
            "semantic_answer_text": "",
            "semantic_bucket": -1,
            "semantic_score": None,
            "semantic_aligned": False,
        },
    )


def _clear_written_answer_draft(course_state: dict, question_id: int) -> None:
    course_state.setdefault("written_answer_drafts", {}).pop(str(question_id), None)


def _question_prompt_message(course_state: dict, block: CourseBlock, question: QuestionBankItem) -> dict:
    options = question.all_answer_options()
    random.shuffle(options)
    message = _append_message(
        course_state,
        block,
        "assistant",
        "question",
        question_id=question.pk,
        question_type=question.question_type,
        question_type_label=question.question_type_label(),
        text=question.stem,
        options=options,
        block_label=block.title,
        learning_objective_id=question.learning_objective_id,
        learning_objective=(question.learning_objective.text if question.learning_objective else "General course understanding"),
        further_study_questions=further_study_questions_for_question(question),
        is_numerical=question.is_numeric(),
        is_coding_question=question.is_coding_question,
        coding_language=question.coding_language,
        coding_question_kind=question.coding_question_kind,
        code_snippet=question.code_snippet,
        answered=False,
        flagged=False,
    )
    if question.is_written_answer():
        draft = _written_answer_draft(course_state, question.pk)
        message.update(
            {
                "draft_answer": draft.get("answer_text", ""),
                "alignment_score": draft.get("alignment_score", 0),
                "alignment_state": draft.get("alignment_state", "drafting"),
                "submitted_text": "",
                "model_answer_revealed": False,
                "model_answer": "",
            }
        )
    return message


def _move_pending_question_message_to_bottom(course_state: dict, block: CourseBlock, question: QuestionBankItem) -> bool:
    transcript = _ensure_block_transcript(course_state, block)
    for index in range(len(transcript) - 1, -1, -1):
        message = transcript[index]
        if (
            message.get("kind") == "question"
            and message.get("question_id") == question.pk
            and not message.get("answered")
            and not message.get("flagged")
        ):
            if index != len(transcript) - 1:
                transcript.append(transcript.pop(index))
            return True
    return False


def _normalize_requested_question_type(question_type: str | None) -> str | None:
    if question_type in {QuestionBankItem.QuestionType.MCQ, QuestionBankItem.QuestionType.NUM, QuestionBankItem.QuestionType.MAQ, QuestionBankItem.QuestionType.WAQ}:
        return question_type
    return None


def _is_coding_question_request(question_type: str | None, coding_only: bool = False) -> bool:
    return bool(coding_only or question_type == CODING_QUESTION_REQUEST)


def _manual_preview_ratio_enabled(block: CourseBlock, ratio_attribute: str) -> bool:
    return int(getattr(block, ratio_attribute, 0) or 0) > 0


def _manual_preview_question_types(block: CourseBlock) -> list[str]:
    question_types = [QuestionBankItem.QuestionType.MCQ]
    if _manual_preview_ratio_enabled(block, "question_numeric_ratio_percent"):
        question_types.append(QuestionBankItem.QuestionType.NUM)
    question_types.extend(
        [
            QuestionBankItem.QuestionType.MAQ,
            QuestionBankItem.QuestionType.WAQ,
        ]
    )
    if _manual_preview_ratio_enabled(block, "question_coding_question_ratio_percent"):
        question_types.append(CODING_QUESTION_REQUEST)
    return question_types


def _manual_preview_question_type_allowed(block: CourseBlock, question_type: str | None, *, coding_only: bool = False) -> bool:
    if _is_coding_question_request(question_type, coding_only):
        return CODING_QUESTION_REQUEST in _manual_preview_question_types(block)
    normalized_type = _normalize_requested_question_type(question_type)
    if normalized_type is None:
        return True
    return normalized_type in _manual_preview_question_types(block)


def _effective_preview_coding_only(block: CourseBlock, question_type: str | None, *, coding_only: bool = False) -> bool:
    if not _is_coding_question_request(question_type, coding_only):
        return False
    return _manual_preview_question_type_allowed(block, question_type, coding_only=True)


def _presented_question_mix(course: Course, block: CourseBlock, course_state: dict) -> tuple[dict[str, int], int, int]:
    state_by_question_id = {
        int(question_id): int((state or {}).get("times_presented", 0) or 0)
        for question_id, state in course_state.get("question_states", {}).items()
        if int((state or {}).get("times_presented", 0) or 0) > 0
    }
    if not state_by_question_id:
        return {}, 0, 0

    type_counts: dict[str, int] = defaultdict(int)
    presented_total = 0
    coding_total = 0
    questions = course.question_bank_items.filter(
        block=block,
        pk__in=state_by_question_id.keys(),
        bank_type=QuestionBankItem.BankType.PRACTICE,
    ).only("pk", "question_type", "is_coding_question")
    for question in questions:
        times_presented = state_by_question_id.get(question.pk, 0)
        if times_presented <= 0:
            continue
        type_counts[question.question_type] += times_presented
        presented_total += times_presented
        if question.is_coding_question:
            coding_total += times_presented
    return dict(type_counts), presented_total, coding_total


def _available_preview_delivery_question_types(course: Course, block: CourseBlock, course_state: dict) -> list[str]:
    question_types = [QuestionBankItem.QuestionType.MCQ]
    if _manual_preview_ratio_enabled(block, "question_numeric_ratio_percent"):
        question_types.append(QuestionBankItem.QuestionType.NUM)
    question_types.extend(
        [
            QuestionBankItem.QuestionType.MAQ,
            QuestionBankItem.QuestionType.WAQ,
        ]
    )
    return question_types


def _preview_delivery_type_targets(course: Course, block: CourseBlock, course_state: dict) -> dict[str, float]:
    available_types = _available_preview_delivery_question_types(course, block, course_state)
    configured_targets = block.question_type_ratio_targets()
    target_total = sum(float(configured_targets.get(question_type, 0.0) or 0.0) for question_type in available_types)
    if target_total <= 0:
        return {QuestionBankItem.QuestionType.MCQ: 100.0}
    return {
        question_type: (float(configured_targets.get(question_type, 0.0) or 0.0) * 100.0 / target_total)
        for question_type in available_types
    }


def _ordered_preview_question_types_by_delivery(course: Course, block: CourseBlock, course_state: dict) -> list[str]:
    target_ratios = _preview_delivery_type_targets(course, block, course_state)
    type_counts, presented_total, _coding_total = _presented_question_mix(course, block, course_state)
    ranked = []
    for question_type, target_ratio in target_ratios.items():
        current_ratio = (type_counts.get(question_type, 0) * 100.0 / presented_total) if presented_total else 0.0
        gap = target_ratio - current_ratio
        ranked.append(
            (
                -gap,
                -target_ratio,
                PREVIEW_QUESTION_TYPE_PRIORITY.get(question_type, 99),
                question_type,
            )
        )
    ranked.sort()
    return [question_type for _gap, _target, _priority, question_type in ranked]


def _preferred_preview_coding_preference(course: Course, block: CourseBlock, course_state: dict, question_type: str | None) -> bool | None:
    if question_type == QuestionBankItem.QuestionType.NUM:
        return False

    target_ratio = int(block.question_coding_question_ratio_percent or 0)
    if target_ratio <= 0:
        return False

    _type_counts, presented_total, coding_total = _presented_question_mix(course, block, course_state)
    current_ratio = (coding_total * 100.0 / presented_total) if presented_total else 0.0
    gap = float(target_ratio) - current_ratio
    if math.isclose(gap, 0.0, abs_tol=0.01):
        return None
    return gap > 0


def _ordered_preview_coding_preferences(course: Course, block: CourseBlock, course_state: dict, question_type: str | None, *, coding_only: bool = False) -> list[bool | None]:
    if coding_only:
        return [True]

    desired = _preferred_preview_coding_preference(course, block, course_state, question_type)
    if desired is True:
        return [True, False, None]
    if desired is False:
        return [False, True, None]
    return [None, False, True]


def _block_completed_count(course_state: dict, block: CourseBlock) -> int:
    return len([event for event in course_state.get("completed_events", []) if int(event["block_id"]) == block.pk])


def _engagement_half_life_days(course: Course) -> int | None:
    value = getattr(course.config, "engagement_half_life_days", None)
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _engagement_release_date(block: CourseBlock) -> date | None:
    return engagement_release_date(block)


def _engagement_decay_weight(days_since_release: int, half_life_days: int) -> float:
    return math.pow(0.5, max(0, days_since_release) / max(1, half_life_days))


def _engagement_metrics_from_answer_dates(course: Course, block: CourseBlock, answer_dates: list[date], *, target_question_count: int) -> dict:
    half_life_days = _engagement_half_life_days(course)
    release_date = _engagement_release_date(block)
    completed_count = len(answer_dates)
    raw_score = round(min(100.0, completed_count * 100.0 / max(1, target_question_count)), 2)
    if half_life_days is None or release_date is None:
        return {
            "engagement": raw_score,
            "engagement_weighted_count": float(completed_count),
            "engagement_half_life_days": half_life_days,
            "engagement_release_date": release_date.isoformat() if release_date else "",
            "engagement_is_fixed": True,
        }

    weighted_count = sum(
        _engagement_decay_weight((answered_on - release_date).days, half_life_days)
        for answered_on in answer_dates
    )
    return {
        "engagement": round(min(raw_score, weighted_count * 100.0 / max(1, target_question_count)), 2),
        "engagement_weighted_count": round(weighted_count, 4),
        "engagement_half_life_days": half_life_days,
        "engagement_release_date": release_date.isoformat(),
        "engagement_is_fixed": False,
    }


def _block_is_accessible(course: Course, block: CourseBlock) -> bool:
    return block.is_available() or bool(getattr(course.config, "allow_pre_engagement", False))


def _advanced_question_start_percent(block: CourseBlock) -> int:
    return max(0, min(100, int(block.question_advanced_question_start_percent or 0)))


def _advanced_question_types_unlocked(course: Course, block: CourseBlock, course_state: dict) -> bool:
    threshold_percent = _advanced_question_start_percent(block)
    if threshold_percent <= 0:
        return True
    target_question_count = max(1, block.preview_target_question_count)
    completed_count = _block_completed_count(course_state, block)
    return completed_count * 100 >= threshold_percent * target_question_count


def _effective_preview_question_type(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    requested_question_type: str | None,
    *,
    coding_only: bool = False,
    force_requested_type: bool = False,
) -> str | None:
    normalized_type = _normalize_requested_question_type(requested_question_type)
    if normalized_type is None:
        if _is_coding_question_request(requested_question_type, coding_only):
            normalized_type = _preferred_standard_generated_question_type(block)
        else:
            ordered_question_types = _ordered_preview_question_types_by_delivery(course, block, course_state)
            normalized_type = ordered_question_types[0] if ordered_question_types else QuestionBankItem.QuestionType.MCQ
    if not _manual_preview_question_type_allowed(block, normalized_type, coding_only=coding_only):
        normalized_type = QuestionBankItem.QuestionType.MCQ
    if force_requested_type:
        return normalized_type
    return normalized_type


def _fallback_preview_question_types(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    requested_question_type: str | None,
    *,
    coding_only: bool = False,
) -> list[str]:
    if requested_question_type is None and not coding_only:
        ordered_delivery_types = _ordered_preview_question_types_by_delivery(course, block, course_state)
        return ordered_delivery_types or [QuestionBankItem.QuestionType.MCQ]

    ordered: list[str | None] = [
        _effective_preview_question_type(course, block, course_state, requested_question_type, coding_only=coding_only),
        QuestionBankItem.QuestionType.MCQ,
    ]
    if not coding_only and QuestionBankItem.QuestionType.NUM in _manual_preview_question_types(block):
        ordered.append(QuestionBankItem.QuestionType.NUM)
    ordered.extend(
        [
            QuestionBankItem.QuestionType.MAQ,
            QuestionBankItem.QuestionType.WAQ,
        ]
    )
    fallback_types: list[str] = []
    for question_type in ordered:
        if question_type and question_type not in fallback_types:
            fallback_types.append(question_type)
    return fallback_types


def _collection_presented_question_mix(course_state: dict, collection: CourseBlockCollection) -> tuple[dict[str, int], int]:
    transcript = _ensure_collection_transcript(course_state, collection)
    type_counts: dict[str, int] = defaultdict(int)
    presented_total = 0
    for message in transcript:
        if message.get("kind") != "question":
            continue
        question_type = str(message.get("question_type") or "").strip()
        if not question_type:
            continue
        type_counts[question_type] += 1
        presented_total += 1
    return dict(type_counts), presented_total


def _collection_delivery_type_targets(blocks: list[CourseBlock]) -> dict[str, float]:
    totals = {
        QuestionBankItem.QuestionType.MCQ: 0.0,
        QuestionBankItem.QuestionType.NUM: 0.0,
        QuestionBankItem.QuestionType.MAQ: 0.0,
        QuestionBankItem.QuestionType.WAQ: 0.0,
    }
    for block in blocks:
        targets = block.question_type_ratio_targets()
        for question_type in totals:
            totals[question_type] += float(targets.get(question_type, 0.0) or 0.0)
    total = sum(totals.values())
    if total <= 0:
        return {QuestionBankItem.QuestionType.MCQ: 100.0}
    return {
        question_type: (value * 100.0 / total)
        for question_type, value in totals.items()
        if value > 0
    }


def _ordered_collection_question_types(
    course_state: dict,
    collection: CourseBlockCollection,
    blocks: list[CourseBlock],
    requested_question_type: str | None = None,
) -> list[str]:
    if requested_question_type is not None:
        ordered: list[str] = []
        for block in blocks:
            ordered.extend(_fallback_preview_question_types(block.course, block, course_state, requested_question_type))
        deduped: list[str] = []
        for question_type in ordered:
            if question_type not in deduped:
                deduped.append(question_type)
        return deduped or [QuestionBankItem.QuestionType.MCQ]

    targets = _collection_delivery_type_targets(blocks)
    type_counts, presented_total = _collection_presented_question_mix(course_state, collection)
    ranked = []
    for question_type, target_ratio in targets.items():
        current_ratio = (type_counts.get(question_type, 0) * 100.0 / presented_total) if presented_total else 0.0
        gap = target_ratio - current_ratio
        ranked.append(
            (
                -gap,
                -target_ratio,
                PREVIEW_QUESTION_TYPE_PRIORITY.get(question_type, 99),
                question_type,
            )
        )
    ranked.sort()
    return [question_type for _gap, _target, _priority, question_type in ranked] or [QuestionBankItem.QuestionType.MCQ]


def _course_question_queryset(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    question_type: str | None = None,
    *,
    coding_only: bool = False,
    coding_preference: bool | None = None,
):
    queryset = course.question_bank_items.filter(
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
        block=block,
    ).exclude(pk__in=_flagged_question_ids(course_state))
    if not bool(getattr(course.config, "allow_pre_engagement", False)):
        queryset = queryset.filter(block__available_from__lte=timezone.localdate())
    if not coding_only and not _manual_preview_ratio_enabled(block, "question_coding_question_ratio_percent"):
        queryset = queryset.filter(is_coding_question=False)
    preferred_coding_language = preferred_coding_language_for_block(block)
    if preferred_coding_language:
        queryset = queryset.filter(Q(is_coding_question=False) | Q(coding_language=preferred_coding_language))
    elif not block_has_coding_signal(block):
        queryset = queryset.filter(is_coding_question=False)
    normalized_type = _normalize_requested_question_type(question_type)
    if normalized_type:
        queryset = queryset.filter(question_type=normalized_type)
    if coding_only:
        queryset = queryset.filter(is_coding_question=True)
    elif coding_preference is True:
        queryset = queryset.filter(is_coding_question=True)
    elif coding_preference is False:
        queryset = queryset.filter(is_coding_question=False)
    return queryset.select_related("learning_objective", "block")


def _block_question_history(question_queryset, course_state: dict, block: CourseBlock):
    objective_presented_counts: dict[int, int] = defaultdict(int)
    chunk_presented_counts: dict[int, int] = defaultdict(int)
    questions = list(question_queryset)
    for question in questions:
        state = _question_state(course_state, question.pk)
        times_presented = int(state.get("times_presented", 0) or 0)
        if times_presented <= 0:
            continue
        if question.learning_objective_id is not None:
            objective_presented_counts[int(question.learning_objective_id)] += times_presented
        if question.source_chunk_id is not None:
            chunk_presented_counts[int(question.source_chunk_id)] += times_presented

    recent_events = [
        event
        for event in reversed(course_state.get("completed_events", []))
        if int(event.get("block_id") or 0) == block.pk
    ]
    recent_objective_ids = {
        int(event["learning_objective_id"])
        for event in recent_events[:3]
        if event.get("learning_objective_id") is not None
    }
    recent_question_ids = {
        int(event["question_id"])
        for event in recent_events[:3]
        if event.get("question_id") is not None
    }
    covered_objective_ids = _covered_objective_ids(course_state, block)
    return questions, objective_presented_counts, chunk_presented_counts, recent_objective_ids, recent_question_ids, covered_objective_ids


def _pick_unseen_question(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    question_type: str | None = None,
    *,
    coding_only: bool = False,
    coding_preference: bool | None = None,
):
    queryset = _course_question_queryset(
        course,
        block,
        course_state,
        question_type,
        coding_only=coding_only,
        coding_preference=coding_preference,
    ).annotate(cohort_seen_count=Count("attempt_questions"))
    (
        questions,
        objective_presented_counts,
        chunk_presented_counts,
        recent_objective_ids,
        recent_question_ids,
        covered_objective_ids,
    ) = _block_question_history(queryset, course_state, block)
    preferred_languages_by_block: dict[int, str] = {}
    candidates = []
    for question in questions:
        if _question_state(course_state, question.pk)["times_presented"] != 0:
            continue
        preferred_coding_language = ""
        if question.is_coding_question:
            preferred_coding_language = preferred_languages_by_block.get(question.block_id, "")
            if not preferred_coding_language:
                preferred_coding_language = preferred_coding_language_for_block(question.block)
                preferred_languages_by_block[question.block_id] = preferred_coding_language
            if not preferred_coding_language:
                continue
        if not coding_question_matches_expected_language(question, preferred_coding_language):
            continue
        if question_quality_sort_key(question)[0]:
            continue
        candidates.append(
            (
                0 if question.learning_objective_id not in covered_objective_ids else 1,
                objective_presented_counts.get(int(question.learning_objective_id or 0), 0),
                chunk_presented_counts.get(int(question.source_chunk_id or 0), 0),
                1 if question.learning_objective_id in recent_objective_ids else 0,
                1 if question.pk in recent_question_ids else 0,
                *question_quality_sort_key(question),
                *coding_question_quality_sort_key(question),
                question.cohort_seen_count,
                question.created_at,
                question.pk,
                question,
            )
        )
    candidates.sort()
    return candidates[0][-1] if candidates else None


def _pick_retry_question(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    question_type: str | None = None,
    *,
    coding_only: bool = False,
    coding_preference: bool | None = None,
):
    completion_sequence = course_state.get("completion_sequence", 0)
    queryset = _course_question_queryset(
        course,
        block,
        course_state,
        question_type,
        coding_only=coding_only,
        coding_preference=coding_preference,
    )
    (
        questions,
        objective_presented_counts,
        chunk_presented_counts,
        recent_objective_ids,
        recent_question_ids,
        _covered_objective_ids,
    ) = _block_question_history(queryset, course_state, block)
    preferred_languages_by_block: dict[int, str] = {}
    candidates = []
    for question in questions:
        state = _question_state(course_state, question.pk)
        if state["times_correct"] > 0 or state["retired_at"] or state["times_incorrect"] == 0:
            continue
        preferred_coding_language = ""
        if question.is_coding_question:
            preferred_coding_language = preferred_languages_by_block.get(question.block_id, "")
            if not preferred_coding_language:
                preferred_coding_language = preferred_coding_language_for_block(question.block)
                preferred_languages_by_block[question.block_id] = preferred_coding_language
            if not preferred_coding_language:
                continue
        if not coding_question_matches_expected_language(question, preferred_coding_language):
            continue
        if question_quality_sort_key(question)[0]:
            continue
        if completion_sequence - state["last_presented_sequence"] <= PREVIEW_RETRY_COMPLETION_GAP:
            continue
        candidates.append(
            (
                1 if question.learning_objective_id in recent_objective_ids else 0,
                1 if question.pk in recent_question_ids else 0,
                objective_presented_counts.get(int(question.learning_objective_id or 0), 0),
                chunk_presented_counts.get(int(question.source_chunk_id or 0), 0),
                *question_quality_sort_key(question),
                *coding_question_quality_sort_key(question),
                state["last_presented_sequence"],
                state["times_incorrect"],
                question.pk,
                question,
            )
        )
    candidates.sort()
    return candidates[0][-1] if candidates else None


def _ordered_unmet_objective_ids(course_state: dict, block: CourseBlock) -> list[int]:
    covered_objective_ids = _covered_objective_ids(course_state, block)
    unmet_objective_ids = [
        objective.pk
        for objective in block.learning_objectives.all()
        if objective.pk not in covered_objective_ids
    ]
    return unmet_objective_ids


def _generation_objective_ids_for_block(course_state: dict, block: CourseBlock) -> list[int]:
    unmet_objective_ids = _ordered_unmet_objective_ids(course_state, block)
    if unmet_objective_ids:
        return unmet_objective_ids

    objective_ids = [objective.pk for objective in block.learning_objectives.all()]
    random.shuffle(objective_ids)
    return objective_ids


def _pending_question(course: Course, block: CourseBlock, course_state: dict):
    pending_question_id = course_state.setdefault("pending_questions", {}).get(str(block.pk))
    if not pending_question_id:
        return None
    return course.question_bank_items.filter(
        pk=pending_question_id,
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
    ).select_related("learning_objective", "block", "source_chunk").first()


def _collection_pending_question(course: Course, collection: CourseBlockCollection, course_state: dict):
    pending_question_id = _collection_thread_state(course_state, collection).get("pending_question_id")
    if not pending_question_id:
        return None
    return course.question_bank_items.filter(
        pk=pending_question_id,
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
    ).select_related("learning_objective", "block", "source_chunk").first()


def _objective_for_block(block: CourseBlock, learning_objective_id: int | None):
    if not learning_objective_id:
        return None
    return block.learning_objectives.filter(pk=learning_objective_id).first()


def _ensure_question_for_block(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    requested_question_type: str | None = None,
    *,
    preferred_objective_id: int | None = None,
    force_new: bool = False,
    coding_only: bool = False,
):
    effective_coding_only = _effective_preview_coding_only(
        block,
        requested_question_type,
        coding_only=coding_only,
    )
    effective_type = _effective_preview_question_type(
        course,
        block,
        course_state,
        requested_question_type,
        coding_only=effective_coding_only,
        force_requested_type=force_new and preferred_objective_id is not None,
    )
    preferred_objective = _objective_for_block(block, preferred_objective_id)
    if preferred_objective_id and preferred_objective is None:
        raise ValueError("Choose a learning objective from this block.")
    pending_question_id = course_state.setdefault("pending_questions", {}).get(str(block.pk))
    if force_new and pending_question_id:
        question = course.question_bank_items.filter(
            pk=pending_question_id,
            bank_type=QuestionBankItem.BankType.PRACTICE,
            status=QuestionBankItem.Status.APPROVED,
        ).first()
        if question is not None and question.pk not in _flagged_question_ids(course_state):
            raise ValueError("Answer or flag the current question before generating a fresh question.")
    if pending_question_id:
        question = course.question_bank_items.filter(
            pk=pending_question_id,
            bank_type=QuestionBankItem.BankType.PRACTICE,
            status=QuestionBankItem.Status.APPROVED,
        ).select_related("learning_objective", "block").first()
        if question is not None and question.pk not in _flagged_question_ids(course_state):
            return question, False

    question = None
    if not force_new:
        for coding_preference in _ordered_preview_coding_preferences(
            course,
            block,
            course_state,
            effective_type,
            coding_only=effective_coding_only,
        ):
            question = _pick_retry_question(
                course,
                block,
                course_state,
                effective_type,
                coding_only=effective_coding_only,
                coding_preference=coding_preference,
            )
            if question is not None:
                break
        if question is None:
            for coding_preference in _ordered_preview_coding_preferences(
                course,
                block,
                course_state,
                effective_type,
                coding_only=effective_coding_only,
            ):
                question = _pick_unseen_question(
                    course,
                    block,
                    course_state,
                    effective_type,
                    coding_only=effective_coding_only,
                    coding_preference=coding_preference,
                )
                if question is not None:
                    break
        if question is None and (requested_question_type is None or effective_coding_only):
            question, is_new_request = _fallback_question_for_block(
                course,
                block,
                course_state,
                requested_question_type,
                preferred_objective_id=preferred_objective_id,
                allow_generation=False,
                coding_only=effective_coding_only,
            )
            if question is not None:
                return question, is_new_request
        if question is not None:
            return question, True
    if question is None:
        question, _ = generate_question_pair_for_block(
            block,
            preferred_objective_ids=[preferred_objective.pk] if preferred_objective is not None else _generation_objective_ids_for_block(course_state, block),
            strict_preferred_objectives=preferred_objective is not None,
            question_type=effective_type,
            raise_generation_errors=True,
            allow_numeric_recent_angle_fallback=True,
            force_coding=effective_coding_only,
        )
    return question, True


def _fallback_question_for_block(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    requested_question_type: str | None,
    *,
    preferred_objective_id: int | None = None,
    allow_generation: bool = True,
    coding_only: bool = False,
) -> tuple[QuestionBankItem | None, bool]:
    effective_coding_only = _effective_preview_coding_only(
        block,
        requested_question_type,
        coding_only=coding_only,
    )
    preferred_objective = _objective_for_block(block, preferred_objective_id)
    fallback_types = _fallback_preview_question_types(
        course,
        block,
        course_state,
        requested_question_type,
        coding_only=effective_coding_only,
    )

    for question_type in fallback_types:
        for coding_preference in _ordered_preview_coding_preferences(
            course,
            block,
            course_state,
            question_type,
            coding_only=effective_coding_only,
        ):
            question = _pick_retry_question(
                course,
                block,
                course_state,
                question_type,
                coding_only=effective_coding_only,
                coding_preference=coding_preference,
            )
            if question is not None:
                return question, True

    for question_type in fallback_types:
        for coding_preference in _ordered_preview_coding_preferences(
            course,
            block,
            course_state,
            question_type,
            coding_only=effective_coding_only,
        ):
            question = _pick_unseen_question(
                course,
                block,
                course_state,
                question_type,
                coding_only=effective_coding_only,
                coding_preference=coding_preference,
            )
            if question is not None:
                return question, True

    if not allow_generation:
        return None, False

    if not course_question_generation_budget(course).can_generate:
        raise QuestionGenerationUnavailableError(live_generation_unavailable_message(course))

    preferred_objective_ids = _generation_objective_ids_for_block(course_state, block)
    if preferred_objective is not None:
        preferred_objective_ids = [preferred_objective.pk] + [
            objective_id for objective_id in preferred_objective_ids if objective_id != preferred_objective.pk
        ]

    requested_type = _normalize_requested_question_type(requested_question_type)
    for question_type in fallback_types:
        if question_type == requested_type:
            continue
        question, _validation = generate_question_pair_for_block(
            block,
            preferred_objective_ids=preferred_objective_ids,
            strict_preferred_objectives=False,
            question_type=question_type,
            raise_generation_errors=False,
            allow_numeric_recent_angle_fallback=True,
            force_coding=effective_coding_only,
        )
        if question is not None:
            return question, True

    question, _validation = generate_question_pair_for_block(
        block,
        preferred_objective_ids=preferred_objective_ids,
        strict_preferred_objectives=False,
        question_type=None,
        raise_generation_errors=False,
        allow_numeric_recent_angle_fallback=True,
        force_coding=effective_coding_only,
    )
    if question is not None:
        return question, True

    return None, False


def _mark_question_presented(course_state: dict, block: CourseBlock, question: QuestionBankItem):
    state = _question_state(course_state, question.pk)
    state["times_presented"] += 1
    state["last_presented_sequence"] = course_state.get("completion_sequence", 0)
    course_state.setdefault("pending_questions", {})[str(block.pk)] = question.pk
    return state


def _mark_collection_question_presented(
    course_state: dict,
    collection: CourseBlockCollection,
    question: QuestionBankItem,
) -> dict:
    state = _question_state(course_state, question.pk)
    state["times_presented"] += 1
    state["last_presented_sequence"] = course_state.get("completion_sequence", 0)
    _collection_thread_state(course_state, collection)["pending_question_id"] = question.pk
    return state


def _question_available_for_collection(
    course: Course,
    block: CourseBlock,
    course_state: dict,
    question_type: str,
) -> bool:
    if not _manual_preview_question_type_allowed(block, question_type):
        return False
    for coding_preference in _ordered_preview_coding_preferences(course, block, course_state, question_type):
        if _pick_retry_question(course, block, course_state, question_type, coding_preference=coding_preference) is not None:
            return True
        if _pick_unseen_question(course, block, course_state, question_type, coding_preference=coding_preference) is not None:
            return True
    return True


def _ensure_question_for_collection(
    course: Course,
    collection: CourseBlockCollection,
    blocks: list[CourseBlock],
    course_state: dict,
    requested_question_type: str | None = None,
    *,
    force_new: bool = False,
) -> tuple[QuestionBankItem | None, bool]:
    pending_question = _collection_pending_question(course, collection, course_state)
    if force_new and pending_question is not None and pending_question.pk not in _flagged_question_ids(course_state):
        raise ValueError("Answer or flag the current question before generating a fresh question.")
    if pending_question is not None and not force_new and pending_question.pk not in _flagged_question_ids(course_state):
        return pending_question, False

    ordered_types = _ordered_collection_question_types(
        course_state,
        collection,
        blocks,
        requested_question_type=requested_question_type,
    )

    for question_type in ordered_types:
        candidate_blocks = [block for block in blocks if _question_available_for_collection(course, block, course_state, question_type)]
        random.shuffle(candidate_blocks)
        for block in candidate_blocks:
            for coding_preference in _ordered_preview_coding_preferences(course, block, course_state, question_type):
                question = _pick_retry_question(
                    course,
                    block,
                    course_state,
                    question_type,
                    coding_preference=coding_preference,
                )
                if question is not None:
                    return question, True
            for coding_preference in _ordered_preview_coding_preferences(course, block, course_state, question_type):
                question = _pick_unseen_question(
                    course,
                    block,
                    course_state,
                    question_type,
                    coding_preference=coding_preference,
                )
                if question is not None:
                    return question, True

    if not course_question_generation_budget(course).can_generate:
        raise QuestionGenerationUnavailableError(live_generation_unavailable_message(course))

    for question_type in ordered_types:
        candidate_blocks = [block for block in blocks if _manual_preview_question_type_allowed(block, question_type)]
        random.shuffle(candidate_blocks)
        for block in candidate_blocks:
            question, _validation = generate_question_pair_for_block(
                block,
                preferred_objective_ids=_generation_objective_ids_for_block(course_state, block),
                strict_preferred_objectives=False,
                question_type=question_type,
                raise_generation_errors=False,
                allow_numeric_recent_angle_fallback=True,
                force_coding=False,
            )
            if question is not None:
                return question, True

    for block in random.sample(blocks, len(blocks)):
        question, _validation = generate_question_pair_for_block(
            block,
            preferred_objective_ids=_generation_objective_ids_for_block(course_state, block),
            strict_preferred_objectives=False,
            question_type=None,
            raise_generation_errors=False,
            allow_numeric_recent_angle_fallback=True,
            force_coding=False,
        )
        if question is not None:
            return question, True

    return None, False


def request_preview_quiz(
    request,
    course: Course,
    block: CourseBlock,
    requested_question_type: str | None = None,
    *,
    preferred_objective_id: int | None = None,
    force_new: bool = False,
    coding_only: bool = False,
) -> dict:
    course_state = _course_state(request, course)
    _ensure_block_transcript(course_state, block)
    if not _block_is_accessible(course, block):
        _append_message(
            course_state,
            block,
            "assistant",
            "text",
            text=f"{block.title} becomes available on {block.available_from:%d %b %Y}.",
            source_blocks=[block.title],
        )
        request.session.modified = True
        return serialize_preview_state(request, course, active_block_id=block.pk)

    try:
        question, is_new_request = _ensure_question_for_block(
            course,
            block,
            course_state,
            requested_question_type,
            preferred_objective_id=preferred_objective_id,
            force_new=force_new,
            coding_only=coding_only,
        )
    except QuestionGenerationError as exc:
        fallback_error = exc if isinstance(exc, QuestionGenerationUnavailableError) else None
        try:
            question, is_new_request = _fallback_question_for_block(
                course,
                block,
                course_state,
                requested_question_type,
                preferred_objective_id=preferred_objective_id,
                coding_only=coding_only,
            )
        except QuestionGenerationUnavailableError as nested_exc:
            fallback_error = nested_exc
            question, is_new_request = None, False
        if question is not None:
            _trace_generation(
                "preview_generation_fallback",
                block=block.title,
                block_id=block.pk,
                requested_type=QuestionBankItem.display_label_for_question_type(
                    _normalize_requested_question_type(requested_question_type) or QuestionBankItem.QuestionType.MCQ
                ),
                original_error=str(exc),
                fallback_type=QuestionBankItem.display_label_for_question_type(question.question_type),
                fallback_question_id=question.pk,
            )
        else:
            _trace_generation(
                "preview_generation_failed_without_fallback",
                block=block.title,
                block_id=block.pk,
                requested_type=QuestionBankItem.display_label_for_question_type(
                    _normalize_requested_question_type(requested_question_type) or QuestionBankItem.QuestionType.MCQ
                ),
                original_error=str(exc),
            )
        if question is None:
            error_text = (
                str(fallback_error)
                if isinstance(fallback_error, QuestionGenerationUnavailableError)
                else "I couldn't get a fresh question for this block just now. Please try Quiz again."
            )
            _append_message(
                course_state,
                block,
                "assistant",
                "text",
                text=error_text,
                source_blocks=[block.title],
            )
            request.session.modified = True
            return serialize_preview_state(request, course, active_block_id=block.pk)
    if question is None:
        _append_message(
            course_state,
            block,
            "assistant",
            "text",
            text="I couldn't build a suitable question for this block yet. Add more notes or learning objectives and try again.",
            source_blocks=[block.title],
        )
        request.session.modified = True
        return serialize_preview_state(request, course, active_block_id=block.pk)

    if is_new_request:
        _mark_question_presented(course_state, block, question)
        _question_prompt_message(course_state, block, question)
    else:
        if not _move_pending_question_message_to_bottom(course_state, block, question):
            _question_prompt_message(course_state, block, question)

    request.session.modified = True
    return serialize_preview_state(request, course, active_block_id=block.pk)


def request_preview_collection_quiz(
    request,
    course: Course,
    collection: CourseBlockCollection,
    *,
    requested_question_type: str | None = None,
) -> dict:
    course_state = _course_state(request, course)
    blocks = _collection_blocks_for_preview(course, collection)
    _ensure_collection_transcript(course_state, collection)
    if not blocks:
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "text",
            text="This collection does not have any released blocks yet.",
            source_blocks=[collection.title],
        )
        request.session.modified = True
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    try:
        question, is_new_request = _ensure_question_for_collection(
            course,
            collection,
            blocks,
            course_state,
            requested_question_type=requested_question_type,
        )
    except QuestionGenerationError as exc:
        error_text = (
            str(exc)
            if isinstance(exc, QuestionGenerationUnavailableError)
            else "I couldn't get a fresh question for this collection just now. Please try Quiz again."
        )
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "text",
            text=error_text,
            source_blocks=[collection.title],
        )
        request.session.modified = True
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    if question is None:
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "text",
            text="I couldn't build a suitable question for this collection yet. Add more notes or learning objectives and try again.",
            source_blocks=[collection.title],
        )
        request.session.modified = True
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    if is_new_request:
        _mark_collection_question_presented(course_state, collection, question)
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "question",
            question_id=question.pk,
            question_type=question.question_type,
            question_type_label=question.question_type_label(),
            text=question.stem,
            options=random.sample(question.all_answer_options(), len(question.all_answer_options())),
            block_label=question.block.title,
            learning_objective_id=question.learning_objective_id,
            learning_objective=(question.learning_objective.text if question.learning_objective else "General course understanding"),
            further_study_questions=further_study_questions_for_question(question),
            is_numerical=question.is_numeric(),
            is_coding_question=question.is_coding_question,
            coding_language=question.coding_language,
            coding_question_kind=question.coding_question_kind,
            code_snippet=question.code_snippet,
            answered=False,
            flagged=False,
        )
    else:
        transcript = _ensure_collection_transcript(course_state, collection)
        for index in range(len(transcript) - 1, -1, -1):
            message = transcript[index]
            if (
                message.get("kind") == "question"
                and int(message.get("question_id") or 0) == question.pk
                and not message.get("answered")
                and not message.get("flagged")
            ):
                if index != len(transcript) - 1:
                    transcript.append(transcript.pop(index))
                break

    request.session.modified = True
    return serialize_preview_state(
        request,
        course,
        active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
        active_thread_id=collection.pk,
    )


def save_preview_objective_guardrail(
    request,
    course: Course,
    block: CourseBlock,
    learning_objective_id: int,
    instruction: str,
) -> dict:
    objective = _objective_for_block(block, learning_objective_id)
    if objective is None:
        raise ValueError("Choose a learning objective from this block.")

    cleaned_instruction = sanitize_assistant_guidance(instruction)
    if not cleaned_instruction:
        raise ValueError("Enter a guardrail first.")

    updated_guidance = merge_assistant_guidance(objective.assistant_guidance, cleaned_instruction)
    if updated_guidance != objective.assistant_guidance:
        objective.assistant_guidance = updated_guidance
        objective.save(update_fields=["assistant_guidance", "updated_at"])

    course_state = _course_state(request, course)
    _append_message(
        course_state,
        block,
        "assistant",
        "text",
        text=(
            f"Guardrail saved for {objective.code}. "
            "Future questions for this learning objective will follow it here and in the student app."
        ),
        source_blocks=[block.title],
    )
    request.session.modified = True
    return serialize_preview_state(request, course, active_block_id=block.pk)


def draft_preview_written_answer(request, course: Course, block: CourseBlock, question_id: int, answer_text: str) -> dict:
    course_state = _course_state(request, course)
    question = _pending_question(course, block, course_state)
    normalized_answer = _normalize_written_answer_text(answer_text)
    if question is None or question.pk != question_id or not question.is_written_answer():
        return {
            "question_id": question_id,
            "answer_text": normalized_answer,
            "alignment_score": 0,
            "alignment_state": "drafting",
        }

    draft = _written_answer_draft(course_state, question.pk)
    alignment = _draft_written_answer_alignment(question, block, normalized_answer, draft)
    draft.update(
        {
            "answer_text": alignment["answer_text"],
            "alignment_score": alignment["alignment_score"],
            "alignment_state": alignment["alignment_state"],
        }
    )
    request.session.modified = True
    return {
        "question_id": question.pk,
        "answer_text": alignment["answer_text"],
        "alignment_score": alignment["alignment_score"],
        "alignment_state": alignment["alignment_state"],
    }


def draft_preview_collection_written_answer(
    request,
    course: Course,
    collection: CourseBlockCollection,
    question_id: int,
    answer_text: str,
) -> dict:
    course_state = _course_state(request, course)
    question = _collection_pending_question(course, collection, course_state)
    normalized_answer = _normalize_written_answer_text(answer_text)
    if question is None or question.pk != question_id or not question.is_written_answer():
        return {
            "question_id": question_id,
            "answer_text": normalized_answer,
            "alignment_score": 0,
            "alignment_state": "drafting",
        }

    draft = _written_answer_draft(course_state, question.pk)
    alignment = _draft_written_answer_alignment(question, question.block, normalized_answer, draft)
    draft.update(
        {
            "answer_text": alignment["answer_text"],
            "alignment_score": alignment["alignment_score"],
            "alignment_state": alignment["alignment_state"],
        }
    )
    request.session.modified = True
    return {
        "question_id": question.pk,
        "answer_text": alignment["answer_text"],
        "alignment_score": alignment["alignment_score"],
        "alignment_state": alignment["alignment_state"],
    }


def _normalize_submitted_answers(selected_answers) -> list[str]:
    if isinstance(selected_answers, str):
        selected_answers = [selected_answers]
    normalized = []
    for answer in selected_answers or []:
        cleaned = str(answer).strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _normalize_written_answer_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _written_answer_state(score_ratio: float, answer_text: str) -> str:
    if len(re.findall(r"[a-z0-9]+", answer_text.lower())) < PREVIEW_WAQ_MIN_SUBSTANTIVE_WORDS:
        return "drafting"
    if score_ratio >= WAQ_ALIGNMENT_THRESHOLD:
        return "aligned"
    if score_ratio >= PREVIEW_WAQ_CLOSE_THRESHOLD:
        return "close"
    return "drafting"


def _rubric_item_match_ratio(answer_text: str, answer_keywords: set[str], rubric_item: str) -> float:
    normalized_item = _normalize_written_answer_text(rubric_item).lower()
    if not normalized_item:
        return 0.0
    if normalized_item in answer_text:
        return 1.0
    item_keywords = _keyword_set(normalized_item)
    if not item_keywords:
        return 0.0
    matched = len(item_keywords & answer_keywords)
    return matched / len(item_keywords)


def _written_answer_alignment(question: QuestionBankItem, answer_text: str) -> dict:
    normalized_answer = _normalize_written_answer_text(answer_text)
    if not normalized_answer:
        return {
            "answer_text": "",
            "alignment_ratio": 0.0,
            "alignment_score": 0,
            "alignment_state": "drafting",
            "matched_keywords": [],
            "missing_keywords": list(question.written_answer_keywords or []),
        }

    answer_text_lower = normalized_answer.lower()
    answer_keywords = _keyword_set(normalized_answer)
    rubric_items = list(question.written_answer_keywords or [question.correct_answer])
    rubric_scores: list[tuple[str, float]] = []
    for rubric_item in rubric_items:
        rubric_scores.append((rubric_item, _rubric_item_match_ratio(answer_text_lower, answer_keywords, rubric_item)))

    keyword_score = (
        sum(score for _, score in rubric_scores) / len(rubric_scores)
        if rubric_scores
        else 0.0
    )
    correct_answer_keywords = _keyword_set(question.correct_answer)
    correct_answer_score = (
        len(correct_answer_keywords & answer_keywords) / len(correct_answer_keywords)
        if correct_answer_keywords
        else 0.0
    )
    substantive_score = min(1.0, len(answer_keywords) / PREVIEW_WAQ_MIN_SUBSTANTIVE_WORDS) if answer_keywords else 0.0
    alignment_ratio = min(1.0, (keyword_score * 0.68) + (correct_answer_score * 0.22) + (substantive_score * 0.10))
    if keyword_score >= 0.66 and correct_answer_score >= 0.6:
        alignment_ratio = max(alignment_ratio, WAQ_ALIGNMENT_THRESHOLD + 0.03)
    matched_keywords = [item for item, score in rubric_scores if score >= 0.74]
    missing_keywords = [item for item, score in rubric_scores if score < 0.74]
    return {
        "answer_text": normalized_answer,
        "alignment_ratio": alignment_ratio,
        "alignment_score": int(round(alignment_ratio * 100)),
        "alignment_state": _written_answer_state(alignment_ratio, normalized_answer),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
    }


def _clear_written_answer_semantic_cache(draft: dict) -> None:
    draft["semantic_answer_text"] = ""
    draft["semantic_bucket"] = -1
    draft["semantic_score"] = None
    draft["semantic_aligned"] = False


def _merged_written_answer_alignment(local_alignment: dict, semantic_score: float | None, semantic_aligned: bool) -> dict:
    if semantic_score is None:
        return local_alignment
    merged_ratio = max(local_alignment["alignment_ratio"], max(0.0, min(1.0, semantic_score)))
    if semantic_aligned:
        merged_ratio = max(merged_ratio, WAQ_ALIGNMENT_THRESHOLD + 0.03)
    return {
        **local_alignment,
        "alignment_ratio": merged_ratio,
        "alignment_score": int(round(merged_ratio * 100)),
        "alignment_state": _written_answer_state(merged_ratio, local_alignment["answer_text"]),
    }


def _parse_json_object(raw_output: str) -> dict:
    normalized_output = (raw_output or "").strip()
    if not normalized_output:
        raise ValueError("OpenAI returned an empty JSON payload.")
    try:
        return json.loads(normalized_output)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", normalized_output, re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    object_match = re.search(r"\{.*\}", normalized_output, re.DOTALL)
    if object_match:
        return json.loads(object_match.group(0))

    raise ValueError("OpenAI did not return parseable JSON.")


def _openai_written_answer_grade(question: QuestionBankItem, block: CourseBlock, answer_text: str, *, draft_mode: bool = False) -> dict:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    learning_objective = question.learning_objective.text if question.learning_objective else "General course understanding"
    source_excerpt = (question.source_chunk.text[:700].strip() if question.source_chunk_id and question.source_chunk else "") or block.summary.strip()
    prompt = f"""
{"Assess this student's in-progress written-answer draft" if draft_mode else "Grade this student's written-answer response"} and return strict JSON.

Rules:
- return only valid JSON with keys: aligned, score, feedback
- aligned must be true only if the student's answer captures the essential meaning of the model answer and rubric
- score must be a number between 0 and 1
- feedback must be one short sentence under 18 words
- ignore minor spelling and grammar issues
- do not mention "the content", "materials", "text", or "passage"
- {"treat this as a live draft: score what is written so far, even if incomplete" if draft_mode else "judge the answer as a final submission"}
- {"aligned should mean the student could reasonably submit now" if draft_mode else "aligned should mean the answer is correct overall"}

Question:
{question.stem}

Learning objective:
{learning_objective}

Canonical answer:
{question.correct_answer}

Hidden rubric:
{", ".join(question.written_answer_keywords or [question.correct_answer])}

Block context:
{source_excerpt}

Student answer:
{answer_text}
""".strip()
    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": "Return only valid JSON."}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    )
    payload = _parse_json_object(getattr(response, "output_text", ""))
    score = max(0.0, min(1.0, float(payload.get("score", 0.0))))
    feedback = _normalize_written_answer_text(str(payload.get("feedback", "")))
    return {
        "aligned": bool(payload.get("aligned")),
        "score": score,
        "feedback": feedback,
    }


def _draft_written_answer_alignment(question: QuestionBankItem, block: CourseBlock, answer_text: str, draft: dict) -> dict:
    local_alignment = _written_answer_alignment(question, answer_text)
    normalized_answer = local_alignment["answer_text"]
    if (
        not settings.OPENAI_API_KEY
        or len(normalized_answer) < PREVIEW_WAQ_OPENAI_DRAFT_MIN_CHARS
        or len(re.findall(r"[a-z0-9]+", normalized_answer.lower())) < PREVIEW_WAQ_MIN_SUBSTANTIVE_WORDS
    ):
        _clear_written_answer_semantic_cache(draft)
        return local_alignment

    current_bucket = len(normalized_answer) // PREVIEW_WAQ_OPENAI_CHECK_INTERVAL
    cached_answer = str(draft.get("semantic_answer_text", ""))
    cached_bucket = int(draft.get("semantic_bucket", -1))
    cached_score = draft.get("semantic_score")
    cached_aligned = bool(draft.get("semantic_aligned"))

    if (
        cached_score is not None
        and cached_bucket == current_bucket
        and cached_answer
        and normalized_answer.startswith(cached_answer)
    ):
        return _merged_written_answer_alignment(local_alignment, float(cached_score), cached_aligned)

    try:
        judged = _openai_written_answer_grade(question, block, normalized_answer, draft_mode=True)
    except Exception:
        _clear_written_answer_semantic_cache(draft)
        return local_alignment

    draft.update(
        {
            "semantic_answer_text": normalized_answer,
            "semantic_bucket": current_bucket,
            "semantic_score": judged["score"],
            "semantic_aligned": bool(judged["aligned"]),
        }
    )
    return _merged_written_answer_alignment(local_alignment, judged["score"], bool(judged["aligned"]))


def _fallback_written_answer_feedback(question: QuestionBankItem, alignment: dict) -> str:
    explanation = normalize_explanation_text(question.explanation, math_metadata=question.math_metadata)
    if alignment["alignment_ratio"] >= WAQ_ALIGNMENT_THRESHOLD:
        if explanation:
            return f"Correct. {explanation}"
        return "Correct."

    if alignment["missing_keywords"]:
        focus_points = ", ".join(alignment["missing_keywords"][:2])
        return f"Not aligned yet. Include {focus_points}. Model answer: {question.correct_answer}"
    return f"Not aligned yet. Be more specific. Model answer: {question.correct_answer}"


def _grade_written_answer_response(question: QuestionBankItem, block: CourseBlock, answer_text: str) -> tuple[bool, dict, str]:
    fallback_alignment = _written_answer_alignment(question, answer_text)
    if settings.OPENAI_API_KEY:
        try:
            judged = _openai_written_answer_grade(question, block, answer_text)
            judged_score = judged["score"]
            judged_alignment = {
                **fallback_alignment,
                "alignment_ratio": judged_score,
                "alignment_score": int(round(judged_score * 100)),
                "alignment_state": _written_answer_state(judged_score, fallback_alignment["answer_text"]),
            }
            is_correct = bool(judged["aligned"]) or judged_score >= WAQ_ALIGNMENT_THRESHOLD
            if is_correct:
                explanation = normalize_explanation_text(question.explanation, math_metadata=question.math_metadata)
                feedback = f"Correct. {explanation}" if explanation else "Correct."
            else:
                reason = judged["feedback"] or "Try to be more specific."
                feedback = f"Not aligned yet. {reason} Model answer: {question.correct_answer}"
            return is_correct, judged_alignment, feedback
        except Exception:
            pass

    is_correct = fallback_alignment["alignment_ratio"] >= WAQ_ALIGNMENT_THRESHOLD
    return is_correct, fallback_alignment, _fallback_written_answer_feedback(question, fallback_alignment)


def _grade_question_response(question: QuestionBankItem, selected_answers) -> tuple[bool, list[str], list[str]]:
    submitted_answers = _normalize_submitted_answers(selected_answers)
    correct_answers = question.correct_answers()
    metadata = question.math_metadata if isinstance(getattr(question, "math_metadata", None), dict) else {}
    if metadata:
        missing_answers = [
            answer
            for answer in correct_answers
            if not any(math_options_equivalent(answer, submitted, metadata) for submitted in submitted_answers)
        ]
        extra_answers = [
            submitted
            for submitted in submitted_answers
            if not any(math_options_equivalent(submitted, answer, metadata) for answer in correct_answers)
        ]
        return not missing_answers and not extra_answers, missing_answers, extra_answers
    missing_answers = [answer for answer in correct_answers if answer not in submitted_answers]
    extra_answers = [answer for answer in submitted_answers if answer not in correct_answers]
    return not missing_answers and not extra_answers, missing_answers, extra_answers


def _feedback_text(question: QuestionBankItem, selected_answers, is_correct: bool, missing_answers: list[str], extra_answers: list[str]) -> str:
    def with_incorrect_prefix(text: str) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return "Incorrect."
        if normalized.lower().startswith("incorrect."):
            return normalized
        return f"Incorrect. {normalized}"

    if question.is_numeric():
        selected_answer_text = selected_answers[0] if selected_answers else ""
        return format_numeric_answer_feedback(
            stem=question.stem,
            explanation_text=question.explanation,
            numeric_metadata=question.numeric_metadata,
            selected_answer_text=selected_answer_text,
            is_correct=is_correct,
            objective_text=getattr(question.learning_objective, "text", ""),
            chunk_text=getattr(question.source_chunk, "text", ""),
            objective_symbol_heuristics=getattr(question.learning_objective, "symbol_heuristics", {}),
        )
    explanation = normalize_explanation_text(question.explanation, math_metadata=question.math_metadata)
    if question.is_multiple_answer():
        if is_correct:
            return "Correct."
        parts = ["Incorrect."]
        if missing_answers:
            parts.append(f"Missed: {', '.join(missing_answers)}.")
        if extra_answers:
            parts.append(f"Extra: {', '.join(extra_answers)}.")
        return " ".join(parts)
    if is_correct:
        if explanation:
            return f"Correct. {explanation}"
        return "Correct. Nice work."
    if explanation:
        return with_incorrect_prefix(explanation)
    return "Incorrect."


def _feedback_with_keep_going_line(course_state: dict, feedback_text: str) -> str:
    completion_count = len(course_state.get("completed_events", []))
    keep_going_line = PREVIEW_KEEP_GOING_LINES[completion_count % len(PREVIEW_KEEP_GOING_LINES)]
    return f"{feedback_text}\n\n{keep_going_line}"


def _split_keep_going_suffix(feedback_text: str) -> tuple[str, str]:
    normalized = str(feedback_text or "")
    for line in PREVIEW_KEEP_GOING_LINES:
        suffix = f"\n\n{line}"
        if normalized.endswith(suffix):
            return normalized[:-len(suffix)], line
    return normalized, ""


def _should_add_keep_going_line(transcript: list[dict]) -> bool:
    now = timezone.now()
    for message in reversed(transcript):
        timestamp = parse_datetime(str(message.get("created_at", "")))
        if timestamp is None:
            continue
        if timezone.is_naive(timestamp):
            timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
        return now - timestamp > PREVIEW_KEEP_GOING_DELAY
    return False


def _format_progress_percent(value: float) -> str:
    rounded = round(float(value or 0.0), 2)
    if rounded.is_integer():
        return f"{int(rounded)}%"
    return f"{rounded:.2f}".rstrip("0").rstrip(".") + "%"


def _refresh_block_progress_message(course_state: dict, block: CourseBlock) -> None:
    metrics = _block_metrics(course_state, block)
    milestones = _block_progress_milestones(course_state, block)
    covered_objective_count = int(metrics.get("covered_objective_count") or 0)
    total_objective_count = int(metrics.get("total_objective_count") or 0)
    completed_count = int(metrics.get("completed_count") or 0)
    target_question_count = int(metrics.get("target_question_count") or 0)
    coverage_complete = total_objective_count > 0 and float(metrics.get("coverage") or 0.0) >= 100.0
    engagement_complete = target_question_count > 0 and float(metrics.get("engagement") or 0.0) >= 100.0

    lines: list[str] = []
    if coverage_complete and not milestones.get("coverage_complete_announced"):
        lines.append(
            f"Coverage is complete for this block: you've covered all {covered_objective_count} learning objectives."
        )
        milestones["coverage_complete_announced"] = True

    if engagement_complete and not milestones.get("engagement_complete_announced"):
        lines.append(
            f"You've reached this block's engagement target: {completed_count} of {target_question_count} questions answered."
        )
        milestones["engagement_complete_announced"] = True

    if not lines:
        return

    lines.append(
        f"Mastery is {_format_progress_percent(metrics.get('mastery') or 0.0)}. "
        "You can keep increasing it at any time by completing more questions accurately."
    )

    _append_message(
        course_state,
        block,
        "assistant",
        "progress_coach",
        text=" ".join(lines),
        source_blocks=[block.title],
    )


def _completed_event_for_feedback(course_state: dict, feedback_message_id: str, question_id: int):
    for event in reversed(course_state.get("completed_events", [])):
        if str(event.get("feedback_message_id", "")) == str(feedback_message_id):
            return event
    for event in reversed(course_state.get("completed_events", [])):
        if int(event.get("question_id") or 0) == int(question_id or 0):
            return event
    return None


def _replace_feedback_message_text(
    transcript: list[dict],
    *,
    feedback_message_id: str,
    question_id: int,
    new_feedback_text: str,
) -> bool:
    for message in transcript:
        if (
            message.get("kind") == "feedback"
            and str(message.get("id", "")) == str(feedback_message_id)
            and int(message.get("question_id") or 0) == int(question_id or 0)
        ):
            _old_feedback_text, keep_going_line = _split_keep_going_suffix(str(message.get("text", "")))
            message["text"] = f"{new_feedback_text}\n\n{keep_going_line}" if keep_going_line else new_feedback_text
            return True
    return False


def regenerate_preview_numeric_feedback(
    request,
    course: Course,
    block: CourseBlock,
    question_id: int,
    feedback_message_id: str,
) -> dict:
    course_state = _course_state(request, course)
    transcript = _ensure_block_transcript(course_state, block)
    feedback_message = next(
        (
            message
            for message in transcript
            if message.get("kind") == "feedback" and str(message.get("id", "")) == str(feedback_message_id)
        ),
        None,
    )
    if feedback_message is None:
        raise ValueError("Choose a numeric feedback message from this block first.")
    if int(feedback_message.get("question_id") or 0) != int(question_id or 0):
        raise ValueError("That feedback message no longer matches the selected question.")
    if not bool(feedback_message.get("can_regenerate_numeric_feedback")):
        raise ValueError("Only numerical question feedback can be regenerated.")

    question = course.question_bank_items.filter(
        pk=question_id,
        course=course,
        block=block,
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
    ).select_related("learning_objective", "source_chunk", "linked_question").first()
    if question is None or not question.is_numeric():
        raise ValueError("Choose a numerical practice question from this block.")

    selected_answer_text = str(feedback_message.get("selected_answer_text", "")).strip()
    if not selected_answer_text:
        raise ValueError("This numeric feedback message does not have a stored answer choice to regenerate from.")
    is_correct = bool(feedback_message.get("correct"))

    updated_feedback = regenerate_stored_numeric_feedback(
        stem=question.stem,
        explanation_text=question.explanation,
        numeric_metadata=question.numeric_metadata if isinstance(question.numeric_metadata, dict) else {},
        objective_text=getattr(question.learning_objective, "text", ""),
        chunk_text=getattr(question.source_chunk, "text", ""),
        objective_symbol_heuristics=getattr(question.learning_objective, "symbol_heuristics", {}),
    )
    refreshed_metadata = dict(question.numeric_metadata or {})
    refreshed_metadata["feedback_v2"] = updated_feedback

    with transaction.atomic():
        question_ids = [question.pk]
        if question.linked_question_id:
            question_ids.append(question.linked_question_id)
        for item in QuestionBankItem.objects.select_for_update().filter(pk__in=question_ids):
            numeric_metadata = dict(item.numeric_metadata or {})
            numeric_metadata["feedback_v2"] = updated_feedback
            item.numeric_metadata = numeric_metadata
            item.save(update_fields=["numeric_metadata", "updated_at"])

    refreshed_question = course.question_bank_items.filter(pk=question.pk).select_related("learning_objective", "source_chunk").first()
    if refreshed_question is None:
        raise ValueError("That numerical question is no longer available.")
    new_feedback_text = format_numeric_answer_feedback(
        stem=refreshed_question.stem,
        explanation_text=refreshed_question.explanation,
        numeric_metadata=refreshed_question.numeric_metadata,
        selected_answer_text=selected_answer_text,
        is_correct=is_correct,
        objective_text=getattr(refreshed_question.learning_objective, "text", ""),
        chunk_text=getattr(refreshed_question.source_chunk, "text", ""),
        objective_symbol_heuristics=getattr(refreshed_question.learning_objective, "symbol_heuristics", {}),
    )
    if not _replace_feedback_message_text(
        transcript,
        feedback_message_id=feedback_message_id,
        question_id=question_id,
        new_feedback_text=new_feedback_text,
    ):
        raise ValueError("That numeric feedback message is no longer available.")
    feedback_message["regenerated_at"] = timezone.now().isoformat()

    completed_event = _completed_event_for_feedback(course_state, feedback_message_id, question_id)
    if completed_event is not None:
        completed_event["feedback"] = new_feedback_text
        completed_event["feedback_message_id"] = feedback_message_id
        attempt_question_id = int(completed_event.get("attempt_question_id") or 0)
        if attempt_question_id:
            PracticeAttemptQuestion.objects.filter(pk=attempt_question_id).update(
                feedback=new_feedback_text,
                updated_at=timezone.now(),
            )

    request.session.modified = True
    return serialize_preview_state(request, course, active_block_id=block.pk)


def regenerate_preview_collection_numeric_feedback(
    request,
    course: Course,
    collection: CourseBlockCollection,
    question_id: int,
    feedback_message_id: str,
) -> dict:
    course_state = _course_state(request, course)
    transcript = _ensure_collection_transcript(course_state, collection)
    feedback_message = next(
        (
            message
            for message in transcript
            if message.get("kind") == "feedback" and str(message.get("id", "")) == str(feedback_message_id)
        ),
        None,
    )
    if feedback_message is None:
        raise ValueError("Choose a numeric feedback message from this collection first.")
    if int(feedback_message.get("question_id") or 0) != int(question_id or 0):
        raise ValueError("That feedback message no longer matches the selected question.")
    if not bool(feedback_message.get("can_regenerate_numeric_feedback")):
        raise ValueError("Only numerical question feedback can be regenerated.")

    question = course.question_bank_items.filter(
        pk=question_id,
        course=course,
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
    ).select_related("learning_objective", "source_chunk", "linked_question", "block").first()
    if question is None or not question.is_numeric():
        raise ValueError("Choose a numerical practice question from this collection.")

    selected_answer_text = str(feedback_message.get("selected_answer_text", "")).strip()
    if not selected_answer_text:
        raise ValueError("This numeric feedback message does not have a stored answer choice to regenerate from.")
    is_correct = bool(feedback_message.get("correct"))

    updated_feedback = regenerate_stored_numeric_feedback(
        stem=question.stem,
        explanation_text=question.explanation,
        numeric_metadata=question.numeric_metadata if isinstance(question.numeric_metadata, dict) else {},
        objective_text=getattr(question.learning_objective, "text", ""),
        chunk_text=getattr(question.source_chunk, "text", ""),
        objective_symbol_heuristics=getattr(question.learning_objective, "symbol_heuristics", {}),
    )
    refreshed_metadata = dict(question.numeric_metadata or {})
    refreshed_metadata["feedback_v2"] = updated_feedback

    with transaction.atomic():
        question_ids = [question.pk]
        if question.linked_question_id:
            question_ids.append(question.linked_question_id)
        for item in QuestionBankItem.objects.select_for_update().filter(pk__in=question_ids):
            numeric_metadata = dict(item.numeric_metadata or {})
            numeric_metadata["feedback_v2"] = updated_feedback
            item.numeric_metadata = numeric_metadata
            item.save(update_fields=["numeric_metadata", "updated_at"])

    refreshed_question = course.question_bank_items.filter(pk=question.pk).select_related("learning_objective", "source_chunk").first()
    if refreshed_question is None:
        raise ValueError("That numerical question is no longer available.")
    new_feedback_text = format_numeric_answer_feedback(
        stem=refreshed_question.stem,
        explanation_text=refreshed_question.explanation,
        numeric_metadata=refreshed_question.numeric_metadata,
        selected_answer_text=selected_answer_text,
        is_correct=is_correct,
        objective_text=getattr(refreshed_question.learning_objective, "text", ""),
        chunk_text=getattr(refreshed_question.source_chunk, "text", ""),
        objective_symbol_heuristics=getattr(refreshed_question.learning_objective, "symbol_heuristics", {}),
    )
    if not _replace_feedback_message_text(
        transcript,
        feedback_message_id=feedback_message_id,
        question_id=question_id,
        new_feedback_text=new_feedback_text,
    ):
        raise ValueError("That numeric feedback message is no longer available.")
    feedback_message["regenerated_at"] = timezone.now().isoformat()

    completed_event = _completed_event_for_feedback(course_state, feedback_message_id, question_id)
    if completed_event is not None:
        completed_event["feedback"] = new_feedback_text
        completed_event["feedback_message_id"] = feedback_message_id
        attempt_question_id = int(completed_event.get("attempt_question_id") or 0)
        if attempt_question_id:
            PracticeAttemptQuestion.objects.filter(pk=attempt_question_id).update(
                feedback=new_feedback_text,
                updated_at=timezone.now(),
            )

    request.session.modified = True
    return serialize_preview_state(
        request,
        course,
        active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
        active_thread_id=collection.pk,
    )


def submit_preview_answer(request, course: Course, block: CourseBlock, question_id: int, selected_answers=None, *, answer_text: str = "") -> dict:
    course_state = _course_state(request, course)
    pending_question_id = course_state.setdefault("pending_questions", {}).get(str(block.pk))
    question = course.question_bank_items.filter(
        pk=question_id,
        course=course,
        block=block,
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
    ).select_related("learning_objective", "block", "source_chunk").first()
    if question is None or pending_question_id != question_id:
        return serialize_preview_state(request, course, active_block_id=block.pk)

    transcript = _ensure_block_transcript(course_state, block)
    normalized_answers = _normalize_submitted_answers(selected_answers)
    normalized_answer_text = _normalize_written_answer_text(answer_text)
    written_alignment = None
    if question.is_written_answer():
        is_correct, written_alignment, feedback_text = _grade_written_answer_response(question, block, normalized_answer_text)
        answer_display_text = normalized_answer_text
    else:
        is_correct, missing_answers, extra_answers = _grade_question_response(question, normalized_answers)
        feedback_text = _feedback_text(question, normalized_answers, is_correct, missing_answers, extra_answers)
        answer_display_text = ", ".join(normalized_answers)
    include_keep_going_line = _should_add_keep_going_line(transcript)

    for message in reversed(transcript):
        if message.get("kind") == "question" and message.get("question_id") == question_id and not message.get("answered"):
            message["answered"] = True
            if question.is_written_answer():
                message["submitted_text"] = answer_display_text
                message["alignment_score"] = written_alignment["alignment_score"] if written_alignment else 0
                message["alignment_state"] = written_alignment["alignment_state"] if written_alignment else "drafting"
                message["model_answer_revealed"] = not is_correct
                message["model_answer"] = question.correct_answer if not is_correct else ""
                message["draft_answer"] = ""
            else:
                message["selected_answers"] = normalized_answers
                message["selected_answer"] = normalized_answers[0] if len(normalized_answers) == 1 else ""
                message["correct_answers"] = question.correct_answers()
            break

    _append_message(course_state, block, "user", "answer", text=answer_display_text)
    feedback_message = _append_message(
        course_state,
        block,
        "assistant",
        "feedback",
        text=_feedback_with_keep_going_line(course_state, feedback_text) if include_keep_going_line else feedback_text,
        correct=is_correct,
        question_id=question.pk,
        question_type=question.question_type,
        selected_answer_text=normalized_answers[0] if normalized_answers else answer_display_text,
        can_regenerate_numeric_feedback=question.is_numeric(),
        source_blocks=[block.title],
    )

    course_state["completion_sequence"] = course_state.get("completion_sequence", 0) + 1
    state = _question_state(course_state, question_id)
    if is_correct:
        state["times_correct"] += 1
        state["retired_at"] = timezone.now().isoformat()
    else:
        state["times_incorrect"] += 1
    course_state.setdefault("completed_events", []).append(
        {
            "block_id": block.pk,
            "thread_kind": PREVIEW_BLOCK_THREAD_KIND,
            "thread_id": block.pk,
            "question_id": question.pk,
            "correct": is_correct,
            "answered_at": timezone.now().isoformat(),
            "learning_objective_id": question.learning_objective_id,
            "source_chunk_id": question.source_chunk_id,
            "question_type": question.question_type,
            "selected_answers": normalized_answers,
            "answer_text": answer_display_text,
            "feedback": feedback_text,
            "feedback_message_id": feedback_message["id"],
        }
    )
    course_state.setdefault("pending_questions", {})[str(block.pk)] = None
    _clear_written_answer_draft(course_state, question_id)
    _refresh_block_progress_message(course_state, block)

    request.session.modified = True
    return serialize_preview_state(request, course, active_block_id=block.pk)


def submit_preview_collection_answer(
    request,
    course: Course,
    collection: CourseBlockCollection,
    question_id: int,
    selected_answers=None,
    *,
    answer_text: str = "",
) -> dict:
    course_state = _course_state(request, course)
    pending_question = _collection_pending_question(course, collection, course_state)
    question = course.question_bank_items.filter(
        pk=question_id,
        course=course,
        bank_type=QuestionBankItem.BankType.PRACTICE,
        status=QuestionBankItem.Status.APPROVED,
    ).select_related("learning_objective", "block", "source_chunk").first()
    if pending_question is None or question is None or pending_question.pk != question_id:
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    transcript = _ensure_collection_transcript(course_state, collection)
    normalized_answers = _normalize_submitted_answers(selected_answers)
    normalized_answer_text = _normalize_written_answer_text(answer_text)
    written_alignment = None
    if question.is_written_answer():
        is_correct, written_alignment, feedback_text = _grade_written_answer_response(question, question.block, normalized_answer_text)
        answer_display_text = normalized_answer_text
    else:
        is_correct, missing_answers, extra_answers = _grade_question_response(question, normalized_answers)
        feedback_text = _feedback_text(question, normalized_answers, is_correct, missing_answers, extra_answers)
        answer_display_text = ", ".join(normalized_answers)
    include_keep_going_line = _should_add_keep_going_line(transcript)

    for message in reversed(transcript):
        if message.get("kind") == "question" and message.get("question_id") == question_id and not message.get("answered"):
            message["answered"] = True
            if question.is_written_answer():
                message["submitted_text"] = answer_display_text
                message["alignment_score"] = written_alignment["alignment_score"] if written_alignment else 0
                message["alignment_state"] = written_alignment["alignment_state"] if written_alignment else "drafting"
                message["model_answer_revealed"] = not is_correct
                message["model_answer"] = question.correct_answer if not is_correct else ""
                message["draft_answer"] = ""
            else:
                message["selected_answers"] = normalized_answers
                message["selected_answer"] = normalized_answers[0] if len(normalized_answers) == 1 else ""
                message["correct_answers"] = question.correct_answers()
            break

    _append_collection_message(course_state, collection, "user", "answer", text=answer_display_text)
    feedback_message = _append_collection_message(
        course_state,
        collection,
        "assistant",
        "feedback",
        text=_feedback_with_keep_going_line(course_state, feedback_text) if include_keep_going_line else feedback_text,
        correct=is_correct,
        question_id=question.pk,
        question_type=question.question_type,
        selected_answer_text=normalized_answers[0] if normalized_answers else answer_display_text,
        can_regenerate_numeric_feedback=question.is_numeric(),
        source_blocks=[question.block.title],
    )

    course_state["completion_sequence"] = course_state.get("completion_sequence", 0) + 1
    state = _question_state(course_state, question_id)
    if is_correct:
        state["times_correct"] += 1
        state["retired_at"] = timezone.now().isoformat()
    else:
        state["times_incorrect"] += 1
    course_state.setdefault("completed_events", []).append(
        {
            "block_id": question.block.pk,
            "thread_kind": PREVIEW_COLLECTION_THREAD_KIND,
            "thread_id": collection.pk,
            "question_id": question.pk,
            "correct": is_correct,
            "answered_at": timezone.now().isoformat(),
            "learning_objective_id": question.learning_objective_id,
            "source_chunk_id": question.source_chunk_id,
            "question_type": question.question_type,
            "selected_answers": normalized_answers,
            "answer_text": answer_display_text,
            "feedback": feedback_text,
            "feedback_message_id": feedback_message["id"],
        }
    )
    _collection_thread_state(course_state, collection)["pending_question_id"] = None
    _clear_written_answer_draft(course_state, question_id)
    _refresh_block_progress_message(course_state, question.block)

    request.session.modified = True
    return serialize_preview_state(
        request,
        course,
        active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
        active_thread_id=collection.pk,
    )


def flag_preview_question(
    request,
    course: Course,
    block: CourseBlock,
    question_id: int,
    *,
    instruction: str = "",
    learning_objective_id: int | None = None,
) -> dict:
    course_state = _course_state(request, course)
    question = course.question_bank_items.filter(
        pk=question_id,
        course=course,
        block=block,
        bank_type=QuestionBankItem.BankType.PRACTICE,
    ).select_related("linked_question", "learning_objective").first()
    if question is None:
        return serialize_preview_state(request, course, active_block_id=block.pk)

    cleaned_instruction = sanitize_assistant_guidance(instruction)
    if cleaned_instruction:
        correction_objective = question.learning_objective
        if correction_objective is None:
            correction_objective = block.learning_objectives.filter(pk=learning_objective_id or 0).first()
        if correction_objective is None:
            raise ValueError("Choose a learning objective before saving a correction note for this question.")
        LearningObjectiveCorrection.objects.create(
            learning_objective=correction_objective,
            question=question,
            created_by=getattr(request, "user", None),
            instruction=cleaned_instruction,
            question_stem_snapshot=question.stem,
        )

    flagged_ids = course_state.setdefault("flagged_question_ids", [])
    for linked_question_id in filter(None, [question.pk, question.linked_question_id]):
        if str(linked_question_id) not in flagged_ids:
            flagged_ids.append(str(linked_question_id))

    transcript = _ensure_block_transcript(course_state, block)
    for message in reversed(transcript):
        if message.get("kind") == "question" and message.get("question_id") == question.pk:
            message["flagged"] = True
            message["answered"] = True
            break

    if course_state.setdefault("pending_questions", {}).get(str(block.pk)) == question.pk:
        course_state["pending_questions"][str(block.pk)] = None
    _clear_written_answer_draft(course_state, question.pk)

    _append_message(
        course_state,
        block,
        "assistant",
        "text",
        text=(
            f"Thanks. I saved that correction note against {question.learning_objective.code if question.learning_objective else correction_objective.code}, "
            "and I won't show this question or its linked validation variant again here."
            if cleaned_instruction
            else "Thanks. I won't show this question again here, and its linked validation question has been removed too."
        ),
        source_blocks=[block.title],
    )
    request.session.modified = True
    return serialize_preview_state(request, course, active_block_id=block.pk)


def flag_preview_collection_question(
    request,
    course: Course,
    collection: CourseBlockCollection,
    question_id: int,
    *,
    instruction: str = "",
    learning_objective_id: int | None = None,
) -> dict:
    course_state = _course_state(request, course)
    question = course.question_bank_items.filter(
        pk=question_id,
        course=course,
        bank_type=QuestionBankItem.BankType.PRACTICE,
    ).select_related("linked_question", "learning_objective", "block").first()
    if question is None:
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    cleaned_instruction = sanitize_assistant_guidance(instruction)
    if cleaned_instruction:
        correction_objective = question.learning_objective
        if correction_objective is None:
            correction_objective = question.block.learning_objectives.filter(pk=learning_objective_id or 0).first()
        if correction_objective is None:
            raise ValueError("Choose a learning objective before saving a correction note for this question.")
        LearningObjectiveCorrection.objects.create(
            learning_objective=correction_objective,
            question=question,
            created_by=getattr(request, "user", None),
            instruction=cleaned_instruction,
            question_stem_snapshot=question.stem,
        )

    flagged_ids = course_state.setdefault("flagged_question_ids", [])
    for linked_question_id in filter(None, [question.pk, question.linked_question_id]):
        if str(linked_question_id) not in flagged_ids:
            flagged_ids.append(str(linked_question_id))

    transcript = _ensure_collection_transcript(course_state, collection)
    for message in reversed(transcript):
        if message.get("kind") == "question" and message.get("question_id") == question.pk:
            message["flagged"] = True
            message["answered"] = True
            break

    thread_state = _collection_thread_state(course_state, collection)
    if thread_state.get("pending_question_id") == question.pk:
        thread_state["pending_question_id"] = None
    _clear_written_answer_draft(course_state, question.pk)

    _append_collection_message(
        course_state,
        collection,
        "assistant",
        "text",
        text=(
            f"Thanks. I saved that correction note against {question.learning_objective.code if question.learning_objective else correction_objective.code}, "
            "and I won't show this question or its linked validation variant again here."
            if cleaned_instruction
            else "Thanks. I won't show this question again here, and its linked validation question has been removed too."
        ),
        source_blocks=[question.block.title],
    )
    request.session.modified = True
    return serialize_preview_state(
        request,
        course,
        active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
        active_thread_id=collection.pk,
    )


def _keyword_set(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 3
    }


def _is_inappropriate_chat_message(text: str) -> bool:
    normalized = " " + re.sub(r"\s+", " ", text.lower()).strip() + " "
    flagged_phrases = {
        " fuck ",
        " fucking ",
        " shit ",
        " bullshit ",
        " bitch ",
        " bastard ",
        " cunt ",
        " dick ",
        " prick ",
        " slut ",
        " whore ",
        " retard ",
        " kill yourself ",
        " kys ",
        " nazi ",
        " rape ",
        " raped ",
        " sexually explicit ",
        " porn ",
        " nigger ",
        " nigga ",
        " fag ",
        " faggot ",
        " stupid ",
        " moron ",
        " idiot ",
    }
    if any(phrase in normalized for phrase in flagged_phrases):
        return True

    targeted_harassment = [
        r"\byou(?:'re| are)?\s+(?:an?\s+)?(?:idiot|moron|stupid|pathetic|useless|disgusting)\b",
        r"\bgo\s+kill\s+yourself\b",
        r"\bi\s+hate\s+you\b",
    ]
    return any(re.search(pattern, normalized) for pattern in targeted_harassment)


def _decode_chat_unicode_escapes(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        codepoint = match.group(1) or match.group(2)
        try:
            return chr(int(codepoint, 16))
        except (TypeError, ValueError):
            return match.group(0)

    return re.sub(r"\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})", replace, str(text or ""))


def _chat_math_body_looks_like_prose(body: str) -> bool:
    source = str(body or "").strip()
    if not source:
        return False
    lowered = source.lower()
    if lowered.startswith(("-", "*")) or re.match(r"^(?:let |here,|so |therefore|using |substituting|rounding|given:)", lowered):
        return True
    prose_check = re.sub(r"\\\([\s\S]*?\\\)", " ", source)
    prose_check = re.sub(r"\\text\{[^}]*\}", " ", prose_check)
    prose_check = re.sub(r"\\mathrm\{[^}]*\}", " ", prose_check)
    prose_check = re.sub(r"\s+", " ", prose_check).strip()
    words = re.findall(r"[A-Za-z]{2,}", prose_check)
    return len(words) >= 5 or (len(words) >= 3 and bool(re.search(r"[.,:]", prose_check)))


def _normalize_chat_display_math_blocks(text: str) -> str:
    normalized = str(text or "")
    for _ in range(6):
        next_text = re.sub(
            r"\\\[\s*(\\\[[\s\S]*?\\\])\s*\\\]",
            lambda match: match.group(1).strip(),
            normalized,
            flags=re.S,
        )
        next_text = re.sub(
            r"\\\[\s*([\s\S]*?)\s*\\\]",
            lambda match: (
                match.group(1).strip()
                if _chat_math_body_looks_like_prose(match.group(1))
                else rf"\[{match.group(1).strip()}\]"
            ),
            next_text,
            flags=re.S,
        )
        if next_text == normalized:
            break
        normalized = next_text
    return normalized


def _looks_like_standalone_chat_math_line(line: str) -> bool:
    text = _decode_chat_unicode_escapes(str(line or "")).strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered.startswith(("-", "*")) or text.endswith(":"):
        return False
    if text.startswith(r"\[") and text.endswith(r"\]"):
        return False
    if re.match(r"^(?:answer|step\s+\d+)\b", lowered):
        return False
    has_tex_signal = bool(re.search(r"\\(?:frac|times|approx|sqrt|mathrm|text|pi|theta|omega|lambda|mu|rho|sigma|phi|Delta|delta|cdot|sin|cos|tan|ln|log|exp)\b", text))
    has_equation_signal = any(token in text for token in ("=", r"\approx", r"\times", r"\frac", r"\sqrt", "/", "×", "÷"))
    if not has_equation_signal and not has_tex_signal:
        return False
    compact_equation = re.fullmatch(r"[A-Za-z0-9α-ωΑ-Ω\\{}\[\]_^=+\-−×÷*/().,|\s]+", text)
    if compact_equation is None:
        return False
    natural_words = re.findall(r"[A-Za-z]{3,}", re.sub(r"\\[A-Za-z]+", " ", text))
    return len(natural_words) <= 6


def _normalize_chat_step_spacing(line: str) -> str:
    text = str(line or "").strip()
    if not text:
        return ""
    text = re.sub(r"^[•●◦]\s*", "- ", text)
    text = re.sub(r"^(\d+\.)\s*(?:\*\*)?(Step\s+\d+:)(?:\*\*)?", r"\1 **\2**", text, flags=re.IGNORECASE)
    text = re.sub(r"^(\d+\.)\s*\*\*(Step\s+\d+:)\*\*(?!\s)", r"\1 **\2** ", text, flags=re.IGNORECASE)
    text = re.sub(r"^(\d+\.)\s*(?:\*\*)?(Answer:)(?:\*\*)?(?!\s)", r"\1 **\2** ", text, flags=re.IGNORECASE)
    text = re.sub(r"^(\d+\.)\s*(?:\*\*)?(Answer:)(?:\*\*)?", r"\1 **\2**", text, flags=re.IGNORECASE)
    if re.match(r"^(?:Answer:|Step\s+\d+:)(?:\s|$)", text, flags=re.IGNORECASE) and not text.startswith("**"):
        text = re.sub(r"^(Answer:|Step\s+\d+:)", r"**\1**", text, flags=re.IGNORECASE)
    return text


def _normalize_chat_answer_text(text: str) -> str:
    normalized = _decode_chat_unicode_escapes(str(text or ""))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    normalized = _normalize_chat_display_math_blocks(normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()

    blocks: list[str] = []
    prose_lines: list[str] = []

    def flush_prose_lines() -> None:
        if not prose_lines:
            return
        paragraph = "\n".join(_normalize_chat_step_spacing(line) for line in prose_lines if line.strip()).strip()
        if paragraph:
            blocks.append(paragraph)
        prose_lines.clear()

    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if not line:
            flush_prose_lines()
            continue
        if _looks_like_standalone_chat_math_line(line):
            flush_prose_lines()
            blocks.append(rf"\[{line}\]")
            continue
        prose_lines.append(line)

    flush_prose_lines()
    return "\n\n".join(blocks).strip()


def _block_source_documents(course: Course, allowed_block_ids: set[int] | None = None):
    documents = []
    for block in course.blocks.prefetch_related("learning_objectives", "assets", "content_chunks").all():
        if allowed_block_ids is not None and block.pk not in allowed_block_ids:
            continue
        extracted_parts = [block.summary.strip()] if block.summary.strip() else []
        extracted_parts.extend(objective.text.strip() for objective in block.learning_objectives.all() if objective.text.strip())
        extracted_parts.extend(asset.extracted_text[:240].strip() for asset in block.assets.all() if asset.extracted_text.strip())
        extracted_parts.extend(chunk.text[:240].strip() for chunk in block.content_chunks.all()[:2] if chunk.text.strip())
        combined = " ".join(part for part in extracted_parts if part)
        documents.append((block, combined))
    return documents


def _chat_source_snippets(course: Course, allowed_block_ids: set[int] | None = None):
    snippets = []
    for block in course.blocks.prefetch_related("learning_objectives", "assets", "content_chunks").all():
        if allowed_block_ids is not None and block.pk not in allowed_block_ids:
            continue
        if block.summary.strip():
            snippets.append({"block": block, "text": block.summary.strip(), "kind": "summary", "bias": 3})
        for objective in block.learning_objectives.all():
            if objective.text.strip():
                snippets.append({"block": block, "text": f"{objective.code}: {objective.text.strip()}", "kind": "objective", "bias": 2})
        for asset in list(block.assets.all())[:2]:
            excerpt = asset.extracted_text[:420].strip()
            if excerpt:
                snippets.append({"block": block, "text": excerpt, "kind": "notes", "bias": 1})
        for chunk in list(block.content_chunks.all())[:4]:
            excerpt = chunk.text[:420].strip()
            if excerpt:
                snippets.append({"block": block, "text": excerpt, "kind": "notes", "bias": 1})
    return snippets


def _retrieve_chat_snippets(course: Course, block: CourseBlock, question: str, allowed_block_ids: set[int] | None = None):
    question_keywords = _keyword_set(question)
    ranked = []
    snippets = _chat_source_snippets(course, allowed_block_ids=allowed_block_ids)
    for snippet in snippets:
        block_title_keywords = _keyword_set(snippet["block"].title)
        snippet_keywords = _keyword_set(f"{snippet['block'].title} {snippet['text']}")
        overlap = len(question_keywords & snippet_keywords)
        title_overlap = len(question_keywords & block_title_keywords)
        active_block_boost = 2 if snippet["block"].pk == block.pk else 0
        score = (overlap * 4) + (title_overlap * 2) + snippet["bias"] + active_block_boost
        ranked.append((score, overlap, snippet))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]["block"].order), reverse=True)
    selected = [item[2] for item in ranked if item[0] > 0][:PREVIEW_CHAT_RETRIEVAL_LIMIT]
    if selected:
        return selected

    return [snippet for snippet in snippets if snippet["block"].pk == block.pk][:PREVIEW_CHAT_RETRIEVAL_LIMIT]


def _recent_chat_context(transcript: list[dict]) -> str:
    lines = []
    for message in transcript[-PREVIEW_CHAT_HISTORY_LIMIT:]:
        if message.get("kind") == "loading":
            continue
        if message.get("kind") == "question":
            lines.append(f"assistant: {message.get('text', '')}")
            if message.get("selected_answer"):
                lines.append(f"user: {message['selected_answer']}")
            continue
        if message.get("kind") == "answer":
            lines.append(f"user: {message.get('text', '')}")
            continue
        role = message.get("role", "assistant")
        text = (message.get("text") or "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines[-PREVIEW_CHAT_HISTORY_LIMIT:])


def _openai_chat_reply(
    course_state: dict,
    course: Course,
    block: CourseBlock,
    question: str,
    *,
    transcript: list[dict] | None = None,
    allowed_block_ids: set[int] | None = None,
) -> tuple[str, list[str]]:
    snippets = _retrieve_chat_snippets(course, block, question, allowed_block_ids=allowed_block_ids)
    if not snippets:
        return _fallback_chat_reply(course, block, question, allowed_block_ids=allowed_block_ids)

    recent_chat = _recent_chat_context(transcript or _ensure_block_transcript(course_state, block))
    source_block_titles = []
    for snippet in snippets:
        if snippet["block"].title not in source_block_titles:
            source_block_titles.append(snippet["block"].title)

    sources_text = "\n\n".join(
        f"[Block: {snippet['block'].title} | Type: {snippet['kind']}]\n{snippet['text']}"
        for snippet in snippets
    )
    teacher_guidance = build_chat_guidance_prompt(course, block, question)
    prompt = f"""
You are the student chat tutor for the course "{course.title}".

Answer the student's question clearly and directly.

Rules:
- use the supplied course notes as your primary grounding
- answer naturally, not like a search result
- do not say "the content", "the materials", "the text", or "the passage"
- if the notes are thin, you may add a brief standard definition to clarify a term, but keep it aligned with the notes
- if the answer is not supported well enough by the notes, say so plainly and be brief
- do not mention source block names in the body unless they help the explanation
- keep the answer concise and useful for a student
- use clean markdown when it helps readability, especially simple bullet lists or numbered steps
- when naming key ideas in a list, prefer markdown like **Idea:** short explanation
- if you show a worked method, use a short intro line, then numbered steps, then a brief final answer line
- put standalone equations on their own line and write display maths as \\[ ... \\]
- keep each numbered step as prose first, then the equation on the next line when that is clearer
- wrap short code snippets, commands, literals, filenames, or syntax examples in single backticks
- use fenced code blocks for multi-line code examples

Current block:
{block.title}

Recent chat:
{recent_chat or "No recent chat."}

Relevant course notes:
{sources_text}

{teacher_guidance}

Student question:
{question}
""".strip()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": "Answer clearly using the supplied notes."}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    )
    answer = _normalize_chat_answer_text((getattr(response, "output_text", "") or "").strip())
    if not answer:
        return _fallback_chat_reply(course, block, question, allowed_block_ids=allowed_block_ids)

    source_blocks = source_block_titles if any(title != block.title for title in source_block_titles) else []
    return answer, source_blocks


def _fallback_chat_reply(
    course: Course,
    block: CourseBlock,
    question: str,
    *,
    allowed_block_ids: set[int] | None = None,
) -> tuple[str, list[str]]:
    question_keywords = _keyword_set(question)
    ranked = []
    for candidate_block, document in _block_source_documents(course, allowed_block_ids=allowed_block_ids):
        score = len(question_keywords & _keyword_set(f"{candidate_block.title} {document}"))
        ranked.append((score, candidate_block, document))
    ranked.sort(key=lambda item: (item[0], item[1].order), reverse=True)

    top_ranked = [item for item in ranked if item[0] > 0][:2]
    if not top_ranked:
        return (
            f"I can answer questions about what's covered in {course.title}. Try naming a topic, learning objective, or block.",
            [block.title],
        )

    primary_block = top_ranked[0][1]
    primary_document = top_ranked[0][2]
    primary_summary = primary_block.summary.strip() or primary_document[:220].strip()
    primary_objectives = list(primary_block.learning_objectives.values_list("text", flat=True)[:2])

    answer_parts = [f"{primary_block.title} is the most relevant block here."]
    if primary_summary:
        answer_parts.append(primary_summary)
    if primary_objectives:
        answer_parts.append(f"Key focus: {'; '.join(primary_objectives)}.")
    if len(top_ranked) > 1:
        answer_parts.append(f"This also connects to {top_ranked[1][1].title}.")

    source_blocks = [item[1].title for item in top_ranked]
    return " ".join(answer_parts), source_blocks


def send_preview_chat_message(request, course: Course, block: CourseBlock, question: str) -> dict:
    course_state = _course_state(request, course)
    pending_question = _pending_question(course, block, course_state)
    if pending_question is not None and pending_question.is_written_answer():
        _append_message(
            course_state,
            block,
            "assistant",
            "text",
            text="Finish the written answer before asking a related question.",
            source_blocks=[block.title],
        )
        request.session.modified = True
        return serialize_preview_state(request, course, active_block_id=block.pk)

    if len(question) > settings.CHAT_MAX_QUESTION_LENGTH:
        _append_message(
            course_state,
            block,
            "assistant",
            "text",
            text=f"Please keep your message under {settings.CHAT_MAX_QUESTION_LENGTH} characters.",
            source_blocks=[block.title],
        )
        request.session.modified = True
        return serialize_preview_state(request, course, active_block_id=block.pk)

    _append_message(course_state, block, "user", "text", text=question)
    if _is_inappropriate_chat_message(question):
        _append_message(
            course_state,
            block,
            "assistant",
            "text",
            text=PREVIEW_INAPPROPRIATE_MESSAGE_WARNING,
            source_blocks=[block.title],
        )
        request.session.modified = True
        return serialize_preview_state(request, course, active_block_id=block.pk)

    transcript = _ensure_block_transcript(course_state, block)
    answer, source_blocks = _fallback_chat_reply(course, block, question)
    if settings.OPENAI_API_KEY:
        try:
            answer, source_blocks = _openai_chat_reply(course_state, course, block, question, transcript=transcript)
        except Exception:
            answer, source_blocks = _fallback_chat_reply(course, block, question)
    answer = _normalize_chat_answer_text(answer)
    _append_message(
        course_state,
        block,
        "assistant",
        "text",
        text=answer,
        source_blocks=source_blocks,
        further_study_questions=further_study_questions_for_chat(
            question=question,
            answer=answer,
            block_title=block.title,
            objective_texts=list(block.learning_objectives.values_list("text", flat=True)[:3]),
        ),
    )
    request.session.modified = True
    return serialize_preview_state(request, course, active_block_id=block.pk)


def send_preview_collection_chat_message(
    request,
    course: Course,
    collection: CourseBlockCollection,
    question: str,
) -> dict:
    course_state = _course_state(request, course)
    blocks = _collection_blocks_for_preview(course, collection)
    transcript = _ensure_collection_transcript(course_state, collection)
    pending_question = _collection_pending_question(course, collection, course_state)
    if pending_question is not None and pending_question.is_written_answer():
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "text",
            text="Finish the written answer before asking a related question.",
            source_blocks=[collection.title],
        )
        request.session.modified = True
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    if len(question) > settings.CHAT_MAX_QUESTION_LENGTH:
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "text",
            text=f"Please keep your message under {settings.CHAT_MAX_QUESTION_LENGTH} characters.",
            source_blocks=[collection.title],
        )
        request.session.modified = True
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    _append_collection_message(course_state, collection, "user", "text", text=question)
    if _is_inappropriate_chat_message(question):
        _append_collection_message(
            course_state,
            collection,
            "assistant",
            "text",
            text=PREVIEW_INAPPROPRIATE_MESSAGE_WARNING,
            source_blocks=[collection.title],
        )
        request.session.modified = True
        return serialize_preview_state(
            request,
            course,
            active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
            active_thread_id=collection.pk,
        )

    anchor_block = blocks[0] if blocks else _first_active_block(course)
    allowed_block_ids = {block.pk for block in blocks}
    answer, source_blocks = _fallback_chat_reply(course, anchor_block, question, allowed_block_ids=allowed_block_ids)
    if settings.OPENAI_API_KEY:
        try:
            answer, source_blocks = _openai_chat_reply(
                course_state,
                course,
                anchor_block,
                question,
                transcript=transcript,
                allowed_block_ids=allowed_block_ids,
            )
        except Exception:
            answer, source_blocks = _fallback_chat_reply(course, anchor_block, question, allowed_block_ids=allowed_block_ids)
    answer = _normalize_chat_answer_text(answer)
    objective_texts: list[str] = []
    for block in blocks:
        objective_texts.extend(list(block.learning_objectives.values_list("text", flat=True)[:2]))
        if len(objective_texts) >= 4:
            break
    _append_collection_message(
        course_state,
        collection,
        "assistant",
        "text",
        text=answer,
        source_blocks=source_blocks,
        further_study_questions=further_study_questions_for_chat(
            question=question,
            answer=answer,
            block_title=collection.title,
            objective_texts=objective_texts[:4],
        ),
    )
    request.session.modified = True
    return serialize_preview_state(
        request,
        course,
        active_thread_kind=PREVIEW_COLLECTION_THREAD_KIND,
        active_thread_id=collection.pk,
    )


def _block_metrics(course_state: dict, block: CourseBlock) -> dict:
    completed_events = [event for event in course_state.get("completed_events", []) if int(event["block_id"]) == block.pk]
    completed_count = _block_completed_count(course_state, block)
    correct_count = sum(1 for event in completed_events if event["correct"])
    incorrect_count = max(0, completed_count - correct_count)
    objective_ids = {
        int(event["learning_objective_id"])
        for event in completed_events
        if event["correct"] and event.get("learning_objective_id") is not None
    }
    total_objectives = block.learning_objectives.count()
    covered_objective_count = len(objective_ids)
    target_question_count = max(1, block.preview_target_question_count)
    answer_dates = [datetime.fromisoformat(event["answered_at"]).date() for event in completed_events]
    engagement_metrics = _engagement_metrics_from_answer_dates(
        block.course,
        block,
        answer_dates,
        target_question_count=target_question_count,
    )

    mastery = round((correct_count * 100 / completed_count), 2) if completed_count else 0.0
    coverage = round((covered_objective_count * 100 / total_objectives), 2) if total_objectives else 0.0
    engagement = float(engagement_metrics["engagement"])
    metric_values = {
        "mastery": mastery,
        "coverage": coverage,
        "engagement": engagement,
    }
    overall = _weighted_practice_score(block.course, metric_values)
    weights = base_practice_weights(block.course)
    advanced_question_start_percent = _advanced_question_start_percent(block)
    advanced_question_types_unlocked = _advanced_question_types_unlocked(block.course, block, course_state)
    return {
        "overall": overall,
        "mastery": mastery,
        "coverage": coverage,
        "engagement": engagement,
        "completed_count": completed_count,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "covered_objective_count": covered_objective_count,
        "total_objective_count": total_objectives,
        "engagement_weighted_count": engagement_metrics["engagement_weighted_count"],
        "engagement_half_life_days": engagement_metrics["engagement_half_life_days"],
        "engagement_release_date": engagement_metrics["engagement_release_date"],
        "engagement_is_fixed": engagement_metrics["engagement_is_fixed"],
        "weights": weights,
        "target_question_count": target_question_count,
        "advanced_question_start_percent": advanced_question_start_percent,
        "advanced_question_types_unlocked": advanced_question_types_unlocked,
    }


def _collection_metrics(course_state: dict, collection: CourseBlockCollection, blocks: list[CourseBlock]) -> dict:
    block_ids = {block.pk for block in blocks}
    completed_events = [
        event
        for event in course_state.get("completed_events", [])
        if str(event.get("thread_kind") or "") == PREVIEW_COLLECTION_THREAD_KIND
        and int(event.get("thread_id") or 0) == collection.pk
        and int(event.get("block_id") or 0) in block_ids
    ]
    completed_count = len(completed_events)
    correct_count = sum(1 for event in completed_events if event.get("correct"))
    incorrect_count = max(0, completed_count - correct_count)
    covered_objective_ids = {
        int(event["learning_objective_id"])
        for event in completed_events
        if event.get("correct") and event.get("learning_objective_id") is not None
    }
    total_objective_ids = {
        objective.pk
        for block in blocks
        for objective in block.learning_objectives.all()
    }
    total_objective_count = len(total_objective_ids)
    covered_objective_count = len(covered_objective_ids)
    mastery = round((correct_count * 100 / completed_count), 2) if completed_count else 0.0
    coverage = round((covered_objective_count * 100 / total_objective_count), 2) if total_objective_count else 0.0
    return {
        "mastery": mastery,
        "coverage": coverage,
        "completed_count": completed_count,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "covered_objective_count": covered_objective_count,
        "total_objective_count": total_objective_count,
    }


def _practice_score_weights(course: Course) -> dict:
    return base_practice_weights(course)


def _weighted_practice_score(course: Course, metrics: dict) -> float:
    return weighted_practice_score(course, metrics)


def _course_metrics(course: Course, serialized_blocks: list[dict], block_metric_pairs: list[dict] | None = None) -> dict:
    metric_blocks = [block for block in serialized_blocks if block.get("counts_in_metrics")] or serialized_blocks
    if not metric_blocks:
        weights = _practice_score_weights(course)
        return {
            "mastery": 0.0,
            "coverage": 0.0,
            "engagement": 0.0,
            "overall": 0.0,
            "block_count": 0,
            "completed_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "covered_objective_count": 0,
            "total_objective_count": sum(block.get("learning_objective_count", 0) for block in serialized_blocks),
            "engagement_weighted_count": 0.0,
            "combined_target_question_count": 0,
            "engagement_half_life_days": _engagement_half_life_days(course),
            "engagement_is_fixed": _engagement_half_life_days(course) is None,
            "weights": weights,
        }

    block_pairs = block_metric_pairs or []
    if len(block_pairs) == len(serialized_blocks):
        filtered_pairs = [
            pair
            for pair, block in zip(block_pairs, serialized_blocks)
            if block.get("counts_in_metrics")
        ]
        block_pairs = filtered_pairs or block_pairs
    elif len(block_pairs) != len(metric_blocks):
        block_pairs = []
    block_count = len(block_pairs)
    metrics = combine_block_practice_metrics(course, block_pairs)
    weights = metrics.get("weights") or _practice_score_weights(course)
    return {
        **metrics,
        "block_count": block_count,
        "completed_count": sum(block["metrics"]["completed_count"] for block in metric_blocks),
        "correct_count": sum(block["metrics"]["correct_count"] for block in metric_blocks),
        "incorrect_count": sum(block["metrics"]["incorrect_count"] for block in metric_blocks),
        "covered_objective_count": sum(block["metrics"]["covered_objective_count"] for block in serialized_blocks),
        "total_objective_count": sum(block.get("learning_objective_count", 0) for block in serialized_blocks),
        "engagement_weighted_count": round(sum(block["metrics"]["engagement_weighted_count"] for block in metric_blocks), 4),
        "combined_target_question_count": sum(block["metrics"]["target_question_count"] for block in metric_blocks),
        "engagement_half_life_days": _engagement_half_life_days(course),
        "engagement_is_fixed": all(block["metrics"].get("engagement_is_fixed") for block in metric_blocks),
        "weights": weights,
    }


def _course_stats(course_state: dict, serialized_blocks: list[dict], course_metrics: dict) -> dict:
    total_objective_count = sum(block.get("learning_objective_count", 0) for block in serialized_blocks)
    completed_count = int(course_metrics.get("completed_count") or 0)
    correct_count = int(course_metrics.get("correct_count") or 0)
    summary = {
        "mastery": round((correct_count * 100 / completed_count), 2) if completed_count else 0.0,
        "coverage": float(course_metrics.get("coverage") or 0.0),
        "completed_count": completed_count,
        "correct_count": correct_count,
        "incorrect_count": int(course_metrics.get("incorrect_count") or 0),
        "covered_objective_count": int(course_metrics.get("covered_objective_count") or 0),
        "total_objective_count": int(course_metrics.get("total_objective_count") or total_objective_count),
        "longest_streak": 0,
    }

    dated_events: list[tuple[datetime, int, dict]] = []
    for index, event in enumerate(course_state.get("completed_events", [])):
        answered_at = parse_datetime(str(event.get("answered_at") or ""))
        if answered_at is None:
            continue
        dated_events.append((answered_at, index, event))
    dated_events.sort(key=lambda item: (item[0], item[1]))

    timeline: list[dict] = []
    cumulative_completed = 0
    cumulative_correct = 0
    current_correct_streak = 0
    longest_correct_streak = 0
    covered_objective_ids: set[int] = set()
    current_day: date | None = None

    def append_timeline_day(day_value: date) -> None:
        mastery = round((cumulative_correct * 100 / cumulative_completed), 2) if cumulative_completed else 0.0
        coverage = round((len(covered_objective_ids) * 100 / total_objective_count), 2) if total_objective_count else 0.0
        timeline.append(
            {
                "date": day_value.isoformat(),
                "mastery": mastery,
                "coverage": coverage,
                "completed_count": cumulative_completed,
                "correct_count": cumulative_correct,
            }
        )

    for answered_at, _index, event in dated_events:
        answered_day = answered_at.date()
        if current_day is None:
            current_day = answered_day
        elif answered_day != current_day:
            append_timeline_day(current_day)
            current_day = answered_day

        cumulative_completed += 1
        if event.get("correct"):
            cumulative_correct += 1
            current_correct_streak += 1
            longest_correct_streak = max(longest_correct_streak, current_correct_streak)
            objective_id = event.get("learning_objective_id")
            if objective_id is not None:
                covered_objective_ids.add(int(objective_id))
        else:
            current_correct_streak = 0

    if current_day is not None:
        append_timeline_day(current_day)

    summary["longest_streak"] = longest_correct_streak

    question_type_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"completed_count": 0, "correct_count": 0})
    for _answered_at, _index, event in dated_events:
        question_type = str(event.get("question_type") or "").strip()
        if not question_type:
            continue
        question_type_totals[question_type]["completed_count"] += 1
        if event.get("correct"):
            question_type_totals[question_type]["correct_count"] += 1

    question_type_mastery = [
        {
            "question_type": question_type,
            "label": QuestionBankItem.display_label_for_question_type(question_type),
            "mastery": round(
                (totals["correct_count"] * 100 / totals["completed_count"]),
                2,
            ) if totals["completed_count"] else 0.0,
            "completed_count": totals["completed_count"],
            "correct_count": totals["correct_count"],
            "incorrect_count": max(0, totals["completed_count"] - totals["correct_count"]),
        }
        for question_type, totals in question_type_totals.items()
    ]
    question_type_mastery.sort(
        key=lambda item: (
            PREVIEW_STATS_QUESTION_TYPE_ORDER.get(item["question_type"], 99),
            item["label"],
        )
    )

    return {
        "summary": summary,
        "timeline": timeline,
        "question_type_mastery": question_type_mastery,
        "latest_answered_at": dated_events[-1][0].isoformat() if dated_events else "",
    }


def _covered_objective_ids(course_state: dict, block: CourseBlock) -> set[int]:
    return {
        int(event["learning_objective_id"])
        for event in course_state.get("completed_events", [])
        if int(event["block_id"]) == block.pk and event["correct"] and event.get("learning_objective_id") is not None
    }


def _serialized_transcript(
    course_state: dict,
    transcript: list[dict],
    block: CourseBlock | None = None,
    *,
    welcome_title: str = "",
) -> list[dict]:
    question_ids = {
        int(message["question_id"])
        for message in transcript
        if message.get("kind") == "question" and message.get("question_id")
    }
    questions_by_id = {
        question.pk: question
        for question in QuestionBankItem.objects.filter(pk__in=question_ids).select_related("learning_objective")
    }
    serialized_messages = []
    for message in transcript:
        message_payload = dict(message)
        replacement_title = welcome_title or (block.title if block is not None else "")
        if (
            message_payload.get("role") == "assistant"
            and message_payload.get("kind") == "text"
            and (
                message_payload.get("is_block_welcome")
                or message_payload.get("is_collection_welcome")
                or (replacement_title and str(message_payload.get("text") or "").startswith(f"Welcome to {replacement_title}."))
            )
        ):
            message_payload["text"] = _welcome_message_text(replacement_title)
            if message_payload.get("is_collection_welcome"):
                message_payload["is_collection_welcome"] = True
            else:
                message_payload["is_block_welcome"] = True
            message_payload["inline_cta_label"] = "Test Mode"
        if message_payload.get("kind") == "question":
            question = questions_by_id.get(int(message_payload.get("question_id") or 0))
            if question is not None:
                message_payload.setdefault("further_study_questions", further_study_questions_for_question(question))
                message_payload.setdefault("is_coding_question", question.is_coding_question)
                message_payload.setdefault("coding_language", question.coding_language)
                message_payload.setdefault("coding_question_kind", question.coding_question_kind)
                message_payload.setdefault("code_snippet", question.code_snippet)
        if message_payload.get("kind") == "question" and message_payload.get("question_type") == QuestionBankItem.QuestionType.WAQ:
            if not message_payload.get("answered"):
                draft = _written_answer_draft(course_state, int(message_payload["question_id"]))
                message_payload.setdefault("draft_answer", draft.get("answer_text", ""))
                message_payload.setdefault("alignment_score", draft.get("alignment_score", 0))
                message_payload.setdefault("alignment_state", draft.get("alignment_state", "drafting"))
            message_payload.setdefault("submitted_text", "")
            message_payload.setdefault("model_answer_revealed", False)
            message_payload.setdefault("model_answer", "")
        serialized_messages.append(message_payload)
    return serialized_messages


def serialize_preview_state(
    request,
    course: Course,
    *,
    active_block_id=None,
    active_thread_kind: str | None = None,
    active_thread_id: int | None = None,
    project_enrollment=None,
    include_projects: bool = True,
) -> dict:
    course_state = _course_state(request, course)
    blocks = _preview_blocks(course)
    active_block_id = active_block_id or (_first_active_block(course).pk if blocks else None)
    project_map = serialize_projects_for_blocks(
        blocks,
        request=request,
        enrollment=project_enrollment,
        include_projects=include_projects,
    )
    serialized_blocks = []
    course_metric_pairs = []
    pending_questions = course_state.get("pending_questions", {})
    for block in blocks:
        transcript = _ensure_block_transcript(course_state, block)
        objectives = list(block.learning_objectives.all())
        covered_objective_ids = _covered_objective_ids(course_state, block)
        block_metrics = _block_metrics(course_state, block)
        released = block.is_available()
        pre_engagement_enabled = bool(getattr(course.config, "allow_pre_engagement", False))
        serialized_blocks.append(
            {
                "id": block.pk,
                "title": block.title,
                "created_at": block.created_at.isoformat(),
                "summary": block.summary or "No summary yet.",
                "avatar_url": (block.avatar_file.url if block.avatar_file else ""),
                "learning_objectives": [
                    {
                        "id": objective.pk,
                        "code": objective.code,
                        "text": objective.text,
                        "covered": objective.pk in covered_objective_ids,
                        "assistant_guidance": sanitize_assistant_guidance(objective.assistant_guidance),
                        "has_guardrail": bool(sanitize_assistant_guidance(objective.assistant_guidance)),
                    }
                    for objective in objectives
                ],
                "available_from": block.available_from.isoformat(),
                "available_from_label": f"{block.available_from.day} {block.available_from:%b %Y}",
                "is_available": _block_is_accessible(course, block),
                "counts_in_metrics": released or (pre_engagement_enabled and block_metrics["completed_count"] > 0),
                "learning_objective_count": len(objectives),
                "target_question_count": block.preview_target_question_count,
                "available_manual_question_types": _manual_preview_question_types(block),
                "has_pending_question": bool(pending_questions.get(str(block.pk))),
                "transcript": _serialized_transcript(course_state, transcript, block, welcome_title=block.title),
                "metrics": block_metrics,
                "projects": project_map.get(block.pk, []),
            }
        )
        course_metric_pairs.append({"block": block, "metrics": block_metrics})
    serialized_collections = []
    for collection in CourseBlockCollection.objects.filter(course=course).prefetch_related("blocks").order_by("created_at", "pk"):
        collection_blocks = _collection_blocks_for_preview(course, collection, blocks)
        if not collection_blocks:
            continue
        transcript = _ensure_collection_transcript(course_state, collection)
        metrics = _collection_metrics(course_state, collection, collection_blocks)
        serialized_collections.append(
            {
                "id": collection.pk,
                "title": collection.title,
                "created_at": collection.created_at.isoformat(),
                "block_ids": [block.pk for block in collection_blocks],
                "anchor_block_id": collection_blocks[0].pk,
                "available_manual_question_types": sorted(
                    {
                        question_type
                        for block in collection_blocks
                        for question_type in _manual_preview_question_types(block)
                        if question_type in {
                            QuestionBankItem.QuestionType.MCQ,
                            QuestionBankItem.QuestionType.NUM,
                            QuestionBankItem.QuestionType.MAQ,
                            QuestionBankItem.QuestionType.WAQ,
                        }
                    }
                ),
                "transcript": _serialized_transcript(
                    course_state,
                    transcript,
                    welcome_title=collection.title,
                ),
                "metrics": metrics,
                "covered_objective_count": metrics["covered_objective_count"],
                "total_objective_count": metrics["total_objective_count"],
                "has_pending_question": bool(_collection_thread_state(course_state, collection).get("pending_question_id")),
            }
        )
    course_metrics = _course_metrics(course, serialized_blocks, course_metric_pairs)
    request.session.modified = True
    resolved_thread_kind = active_thread_kind or PREVIEW_BLOCK_THREAD_KIND
    resolved_thread_id = active_thread_id or active_block_id
    return {
        "course": {
            "id": course.pk,
            "title": course.title,
            "summary": course.summary,
            "metrics": course_metrics,
            "stats": _course_stats(course_state, serialized_blocks, course_metrics),
        },
        "active_block_id": active_block_id,
        "active_thread_kind": resolved_thread_kind,
        "active_thread_id": resolved_thread_id,
        "blocks": serialized_blocks,
        "collections": serialized_collections,
    }
