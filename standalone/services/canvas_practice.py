import copy
import threading
from contextlib import contextmanager
from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone

from standalone.models import CanvasCourseMembership, CourseBlockCollection
from standalone.services.preview import (
    PREVIEW_SESSION_KEY,
    _empty_course_state,
    draft_preview_collection_written_answer,
    draft_preview_written_answer,
    request_preview_collection_quiz,
    request_preview_quiz,
    send_preview_collection_chat_message,
    send_preview_chat_message,
    serialize_preview_state,
    submit_preview_collection_answer,
    submit_preview_answer,
)


class _StateSession(dict):
    modified = False


_CANVAS_MEMBERSHIP_LOCKS: dict[tuple[int, int], threading.RLock] = {}
_CANVAS_MEMBERSHIP_LOCKS_GUARD = threading.Lock()


@contextmanager
def _canvas_membership_lock(canvas_user_id: int, course_id: int):
    with _CANVAS_MEMBERSHIP_LOCKS_GUARD:
        lock = _CANVAS_MEMBERSHIP_LOCKS.setdefault((int(canvas_user_id), int(course_id)), threading.RLock())
    with lock:
        yield


def _normalized_practice_state(raw_state: dict | None) -> dict:
    state = copy.deepcopy(raw_state or {})
    if not state:
        return _empty_course_state()
    return state


def _shared_membership_queryset(membership: CanvasCourseMembership):
    return CanvasCourseMembership.objects.select_related("canvas_course_link__course", "canvas_user").filter(
        canvas_user_id=membership.canvas_user_id,
        canvas_course_link__course_id=membership.canvas_course_link.course_id,
    )


def _shared_memberships(membership: CanvasCourseMembership) -> list[CanvasCourseMembership]:
    return list(_shared_membership_queryset(membership).order_by("-updated_at", "-created_at", "pk"))


def _membership_state(membership: CanvasCourseMembership, *, shared_memberships: list[CanvasCourseMembership] | None = None) -> dict:
    memberships = shared_memberships if shared_memberships is not None else _shared_memberships(membership)
    empty_state = _empty_course_state()
    for candidate in memberships:
        state = _normalized_practice_state(candidate.practice_state)
        if state != empty_state:
            return state
    return _normalized_practice_state(membership.practice_state)


def _canvas_request(membership: CanvasCourseMembership, *, practice_state: dict | None = None):
    payload = {
        PREVIEW_SESSION_KEY: {
            str(membership.canvas_course_link.course_id): copy.deepcopy(
                practice_state if practice_state is not None else _membership_state(membership)
            )
        }
    }
    return SimpleNamespace(session=_StateSession(payload))


def _persist_canvas_state(
    membership: CanvasCourseMembership,
    request,
    *,
    shared_memberships: list[CanvasCourseMembership] | None = None,
) -> None:
    next_state = copy.deepcopy(
        request.session.get(PREVIEW_SESSION_KEY, {}).get(str(membership.canvas_course_link.course_id)) or _empty_course_state()
    )
    memberships = shared_memberships if shared_memberships is not None else _shared_memberships(membership)
    changed_memberships = []
    now = timezone.now()
    for linked_membership in memberships:
        if _normalized_practice_state(linked_membership.practice_state) == next_state:
            continue
        linked_membership.practice_state = copy.deepcopy(next_state)
        linked_membership.updated_at = now
        changed_memberships.append(linked_membership)
    if not changed_memberships:
        return
    CanvasCourseMembership.objects.bulk_update(changed_memberships, ["practice_state", "updated_at"])


def serialize_canvas_preview_state(membership: CanvasCourseMembership, *, active_block_id=None) -> dict:
    with _canvas_membership_lock(membership.canvas_user_id, membership.canvas_course_link.course_id):
        locked_membership = CanvasCourseMembership.objects.select_related("canvas_course_link__course").get(pk=membership.pk)
        shared_memberships = _shared_memberships(locked_membership)
        request = _canvas_request(locked_membership, practice_state=_membership_state(locked_membership, shared_memberships=shared_memberships))
        payload = serialize_preview_state(
            request,
            locked_membership.canvas_course_link.course,
            active_block_id=active_block_id,
            include_projects=False,
        )
        _persist_canvas_state(locked_membership, request, shared_memberships=shared_memberships)
    return payload


def request_canvas_preview_quiz(
    membership: CanvasCourseMembership,
    block,
    *,
    collection: CourseBlockCollection | None = None,
    requested_question_type: str | None = None,
    force_new: bool = False,
    preferred_objective_id: int | None = None,
    coding_only: bool = False,
) -> dict:
    with _canvas_membership_lock(membership.canvas_user_id, membership.canvas_course_link.course_id):
        with transaction.atomic():
            locked_membership = CanvasCourseMembership.objects.select_for_update().select_related("canvas_course_link__course").get(pk=membership.pk)
            shared_memberships = list(_shared_membership_queryset(locked_membership).select_for_update().order_by("-updated_at", "-created_at", "pk"))
            request = _canvas_request(
                locked_membership,
                practice_state=_membership_state(locked_membership, shared_memberships=shared_memberships),
            )
            if collection is not None:
                payload = request_preview_collection_quiz(
                    request,
                    locked_membership.canvas_course_link.course,
                    collection,
                    requested_question_type=requested_question_type,
                )
            else:
                payload = request_preview_quiz(
                    request,
                    locked_membership.canvas_course_link.course,
                    block,
                    requested_question_type=requested_question_type,
                    preferred_objective_id=preferred_objective_id,
                    force_new=force_new,
                    coding_only=coding_only,
                )
            for payload_block in payload.get("blocks", []):
                payload_block["projects"] = []
            _persist_canvas_state(locked_membership, request, shared_memberships=shared_memberships)
    return payload


def submit_canvas_preview_answer(
    membership: CanvasCourseMembership,
    block,
    question_id: int,
    selected_answers=None,
    *,
    collection: CourseBlockCollection | None = None,
    answer_text: str = "",
) -> dict:
    with _canvas_membership_lock(membership.canvas_user_id, membership.canvas_course_link.course_id):
        with transaction.atomic():
            locked_membership = CanvasCourseMembership.objects.select_for_update().select_related("canvas_course_link__course").get(pk=membership.pk)
            shared_memberships = list(_shared_membership_queryset(locked_membership).select_for_update().order_by("-updated_at", "-created_at", "pk"))
            request = _canvas_request(
                locked_membership,
                practice_state=_membership_state(locked_membership, shared_memberships=shared_memberships),
            )
            if collection is not None:
                payload = submit_preview_collection_answer(
                    request,
                    locked_membership.canvas_course_link.course,
                    collection,
                    question_id,
                    selected_answers or [],
                    answer_text=answer_text,
                )
            else:
                payload = submit_preview_answer(
                    request,
                    locked_membership.canvas_course_link.course,
                    block,
                    question_id,
                    selected_answers or [],
                    answer_text=answer_text,
                )
            for payload_block in payload.get("blocks", []):
                payload_block["projects"] = []
            _persist_canvas_state(locked_membership, request, shared_memberships=shared_memberships)
    return payload


def draft_canvas_preview_written_answer(
    membership: CanvasCourseMembership,
    block,
    question_id: int,
    answer_text: str,
    *,
    collection: CourseBlockCollection | None = None,
) -> dict:
    with _canvas_membership_lock(membership.canvas_user_id, membership.canvas_course_link.course_id):
        with transaction.atomic():
            locked_membership = CanvasCourseMembership.objects.select_for_update().select_related("canvas_course_link__course").get(pk=membership.pk)
            shared_memberships = list(_shared_membership_queryset(locked_membership).select_for_update().order_by("-updated_at", "-created_at", "pk"))
            request = _canvas_request(
                locked_membership,
                practice_state=_membership_state(locked_membership, shared_memberships=shared_memberships),
            )
            if collection is not None:
                payload = draft_preview_collection_written_answer(
                    request,
                    locked_membership.canvas_course_link.course,
                    collection,
                    question_id,
                    answer_text,
                )
            else:
                payload = draft_preview_written_answer(
                    request,
                    locked_membership.canvas_course_link.course,
                    block,
                    question_id,
                    answer_text,
                )
            _persist_canvas_state(locked_membership, request, shared_memberships=shared_memberships)
    return payload


def send_canvas_preview_chat_message(
    membership: CanvasCourseMembership,
    block,
    question: str,
    *,
    collection: CourseBlockCollection | None = None,
) -> dict:
    with _canvas_membership_lock(membership.canvas_user_id, membership.canvas_course_link.course_id):
        with transaction.atomic():
            locked_membership = CanvasCourseMembership.objects.select_for_update().select_related("canvas_course_link__course").get(pk=membership.pk)
            shared_memberships = list(_shared_membership_queryset(locked_membership).select_for_update().order_by("-updated_at", "-created_at", "pk"))
            request = _canvas_request(
                locked_membership,
                practice_state=_membership_state(locked_membership, shared_memberships=shared_memberships),
            )
            if collection is not None:
                payload = send_preview_collection_chat_message(
                    request,
                    locked_membership.canvas_course_link.course,
                    collection,
                    question,
                )
            else:
                payload = send_preview_chat_message(
                    request,
                    locked_membership.canvas_course_link.course,
                    block,
                    question,
                )
            for payload_block in payload.get("blocks", []):
                payload_block["projects"] = []
            _persist_canvas_state(locked_membership, request, shared_memberships=shared_memberships)
    return payload


def reset_canvas_preview_state(membership: CanvasCourseMembership) -> dict:
    with _canvas_membership_lock(membership.canvas_user_id, membership.canvas_course_link.course_id):
        with transaction.atomic():
            locked_membership = CanvasCourseMembership.objects.select_for_update().select_related("canvas_course_link__course").get(pk=membership.pk)
            shared_memberships = list(_shared_membership_queryset(locked_membership).select_for_update().order_by("-updated_at", "-created_at", "pk"))
            request = _canvas_request(locked_membership, practice_state=_empty_course_state())
            payload = serialize_preview_state(request, locked_membership.canvas_course_link.course, include_projects=False)
            _persist_canvas_state(locked_membership, request, shared_memberships=shared_memberships)
    return payload
