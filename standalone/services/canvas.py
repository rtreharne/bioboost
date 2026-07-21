import html
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from standalone.models import CanvasCourseLink, CanvasCourseMembership, CanvasMagicLink, CanvasUserIdentity

logger = logging.getLogger(__name__)

_SYNCABLE_ENROLLMENT_TYPES = {
    "StudentEnrollment": CanvasCourseMembership.CanvasRole.STUDENT,
    "TeacherEnrollment": CanvasCourseMembership.CanvasRole.TEACHER,
    "TaEnrollment": CanvasCourseMembership.CanvasRole.TA,
    "DesignerEnrollment": CanvasCourseMembership.CanvasRole.DESIGNER,
}


class CanvasAPIError(Exception):
    def __init__(self, message: str, *, status_code: int = 0, detail: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


@dataclass
class CanvasSyncResult:
    membership_count: int
    course_name: str


def canvas_api_configured() -> bool:
    return bool(settings.CANVAS_API_URL and settings.CANVAS_API_TOKEN)


def require_canvas_api_config() -> None:
    if canvas_api_configured():
        return
    raise CanvasAPIError("Canvas API settings are missing. Add CANVAS_API_URL and CANVAS_API_TOKEN first.")


def canvas_api_base_url() -> str:
    require_canvas_api_config()
    base_url = str(settings.CANVAS_API_URL or "").strip().rstrip("/")
    if not base_url:
        raise CanvasAPIError("Canvas API settings are missing. Add CANVAS_API_URL and CANVAS_API_TOKEN first.")
    if base_url.endswith("/api/v1"):
        return base_url
    if "/api/" in base_url:
        return base_url
    return f"{base_url}/api/v1"


def canvas_root_url() -> str:
    parts = urlsplit(canvas_api_base_url())
    return f"{parts.scheme}://{parts.netloc}"


def canvas_inbox_url() -> str:
    return urljoin(f"{canvas_root_url()}/", "conversations")


def normalized_canvas_search_text(*parts: str) -> str:
    tokens: list[str] = []
    for part in parts:
        collapsed = " ".join(str(part or "").strip().lower().split())
        if collapsed:
            tokens.append(collapsed)
    unique_tokens: list[str] = []
    for token in tokens:
        if token not in unique_tokens:
            unique_tokens.append(token)
    return " ".join(unique_tokens)


def hashed_canvas_login_id(login_id: str, *, fallback_key: str) -> str:
    candidate = str(login_id or "").strip().lower() or fallback_key
    digest = hmac.new(settings.SECRET_KEY.encode("utf-8"), candidate.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def canvas_magic_link_body(*, course_title: str, magic_url: str, expires_at) -> str:
    expiry_display = timezone.localtime(expires_at).strftime("%d %b %Y, %H:%M")
    return (
        f"Open BioBoost for {course_title} from Canvas here:\n\n"
        f"{magic_url}\n\n"
        f"This link expires on {expiry_display} and can only be used once."
    )


def _request_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.CANVAS_API_TOKEN}",
        "Accept": "application/json",
    }


def _next_link(response_headers) -> str:
    link_header = str(response_headers.get("Link") or "").strip()
    if not link_header:
        return ""
    for part in link_header.split(","):
        bits = [item.strip() for item in part.split(";") if item.strip()]
        if len(bits) < 2:
            continue
        if 'rel="next"' not in bits[1]:
            continue
        target = bits[0].strip()
        if target.startswith("<") and target.endswith(">"):
            return target[1:-1]
    return ""


def _error_message(error_payload: Any, default_message: str) -> str:
    if isinstance(error_payload, dict):
        for key in ("message", "error", "errors"):
            value = error_payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list) and value:
                return "; ".join(str(item) for item in value)
    return default_message


def _canvas_request_json(url: str, *, method: str = "GET", params: dict[str, Any] | None = None, form_data: dict[str, Any] | None = None) -> tuple[Any, Any]:
    query = urlencode(params or {}, doseq=True)
    request_url = f"{url}?{query}" if query else url
    data = None
    headers = _request_headers()
    if form_data is not None:
        data = urlencode(form_data, doseq=True).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(request_url, data=data, headers=headers, method=method.upper())
    timeout_seconds = max(1.0, float(getattr(settings, "CANVAS_API_TIMEOUT_SECONDS", 15.0) or 15.0))
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8") or "null")
            return payload, response.headers
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            parsed_detail = json.loads(detail) if detail else {}
        except json.JSONDecodeError:
            parsed_detail = {}
        message = _error_message(parsed_detail, f"Canvas API returned HTTP {error.code}.")
        raise CanvasAPIError(message, status_code=error.code, detail=detail) from error
    except URLError as error:
        raise CanvasAPIError("Canvas API could not be reached. Check CANVAS_API_URL and network access.") from error


def fetch_canvas_course(course_id: int) -> dict[str, Any]:
    payload, _headers = _canvas_request_json(urljoin(f"{canvas_api_base_url()}/", f"courses/{int(course_id)}"))
    if not isinstance(payload, dict):
        raise CanvasAPIError("Canvas course lookup returned an unexpected response.")
    return payload


def fetch_canvas_course_enrollments(course_id: int) -> list[dict[str, Any]]:
    next_url = urljoin(f"{canvas_api_base_url()}/", f"courses/{int(course_id)}/enrollments")
    params = {
        "state[]": ["active"],
        "include[]": ["user"],
        "per_page": 100,
    }
    enrollments: list[dict[str, Any]] = []
    while next_url:
        payload, headers = _canvas_request_json(next_url, params=params)
        params = None
        if not isinstance(payload, list):
            raise CanvasAPIError("Canvas enrollments returned an unexpected response.")
        enrollments.extend(item for item in payload if isinstance(item, dict))
        next_url = _next_link(headers)
    return enrollments


def sync_canvas_course_link(link: CanvasCourseLink) -> CanvasSyncResult:
    course_payload = fetch_canvas_course(link.canvas_course_id)
    course_name = str(course_payload.get("name") or course_payload.get("course_code") or "").strip()
    enrollments = fetch_canvas_course_enrollments(link.canvas_course_id)
    now = timezone.now()
    membership_user_ids: set[int] = set()
    with transaction.atomic():
        locked_link = CanvasCourseLink.objects.select_for_update().get(pk=link.pk)
        for enrollment in enrollments:
            enrollment_type = str(enrollment.get("type") or "").strip()
            canvas_role = _SYNCABLE_ENROLLMENT_TYPES.get(enrollment_type)
            if not canvas_role:
                continue
            enrollment_state = str(enrollment.get("enrollment_state") or enrollment.get("workflow_state") or "active").strip().lower()
            if enrollment_state not in {"active", "current", "invited"}:
                continue
            user_payload = enrollment.get("user") if isinstance(enrollment.get("user"), dict) else {}
            canvas_user_id = int(user_payload.get("id") or enrollment.get("user_id") or 0)
            if canvas_user_id <= 0:
                continue
            sortable_name = str(user_payload.get("sortable_name") or user_payload.get("name") or "").strip()
            display_name = str(user_payload.get("short_name") or user_payload.get("name") or sortable_name).strip()
            login_id = str(user_payload.get("login_id") or "").strip()
            identity, _created = CanvasUserIdentity.objects.get_or_create(
                canvas_user_id=canvas_user_id,
                defaults={
                    "login_id_hash": hashed_canvas_login_id(login_id, fallback_key=f"canvas-user:{canvas_user_id}"),
                    "sortable_name": sortable_name,
                    "display_name": display_name,
                    "search_text": normalized_canvas_search_text(display_name, sortable_name),
                    "last_seen_at": now,
                },
            )
            next_hash = hashed_canvas_login_id(login_id, fallback_key=f"canvas-user:{canvas_user_id}")
            changed_fields: list[str] = []
            if identity.login_id_hash != next_hash:
                identity.login_id_hash = next_hash
                changed_fields.append("login_id_hash")
            if identity.sortable_name != sortable_name:
                identity.sortable_name = sortable_name
                changed_fields.append("sortable_name")
            if identity.display_name != display_name:
                identity.display_name = display_name
                changed_fields.append("display_name")
            next_search_text = normalized_canvas_search_text(display_name, sortable_name)
            if identity.search_text != next_search_text:
                identity.search_text = next_search_text
                changed_fields.append("search_text")
            identity.last_seen_at = now
            changed_fields.append("last_seen_at")
            if changed_fields:
                identity.save(update_fields=[*dict.fromkeys(changed_fields), "updated_at"])

            membership, _created = CanvasCourseMembership.objects.get_or_create(
                canvas_course_link=locked_link,
                canvas_user=identity,
                defaults={
                    "canvas_role": canvas_role,
                    "enrollment_state": enrollment_state,
                },
            )
            membership_user_ids.add(identity.pk)
            membership_changes: list[str] = []
            if membership.canvas_role != canvas_role:
                membership.canvas_role = canvas_role
                membership_changes.append("canvas_role")
            if membership.enrollment_state != enrollment_state:
                membership.enrollment_state = enrollment_state
                membership_changes.append("enrollment_state")
            if membership_changes:
                membership.save(update_fields=[*membership_changes, "updated_at"])

        if membership_user_ids:
            locked_link.memberships.exclude(canvas_user_id__in=membership_user_ids).delete()
        else:
            locked_link.memberships.all().delete()

        locked_link.canvas_course_name = course_name
        locked_link.last_synced_at = now
        locked_link.last_sync_error = ""
        locked_link.save(update_fields=["canvas_course_name", "last_synced_at", "last_sync_error", "updated_at"])
        membership_count = locked_link.memberships.count()
    link.refresh_from_db()
    return CanvasSyncResult(membership_count=membership_count, course_name=course_name)


def sync_canvas_course_link_with_error_state(link: CanvasCourseLink) -> CanvasSyncResult:
    try:
        return sync_canvas_course_link(link)
    except CanvasAPIError as error:
        CanvasCourseLink.objects.filter(pk=link.pk).update(last_sync_error=str(error), updated_at=timezone.now())
        raise


def canvas_link_is_stale(link: CanvasCourseLink) -> bool:
    if link.last_synced_at is None:
        return True
    max_age_hours = max(1, int(getattr(settings, "CANVAS_AUTO_SYNC_MAX_AGE_HOURS", 6) or 6))
    return link.last_synced_at <= timezone.now() - timedelta(hours=max_age_hours)


def issue_canvas_magic_link(membership: CanvasCourseMembership, *, return_to_url: str = "") -> CanvasMagicLink:
    now = timezone.now()
    membership.magic_links.filter(used_at__isnull=True, superseded_at__isnull=True).update(superseded_at=now, updated_at=now)
    return CanvasMagicLink.objects.create(
        membership=membership,
        expires_at=CanvasMagicLink.default_expiry(),
        return_to_url=str(return_to_url or "").strip(),
        sent_to_canvas_user_id=membership.canvas_user.canvas_user_id,
    )


def send_canvas_magic_link_message(magic_link: CanvasMagicLink, *, absolute_magic_url: str) -> CanvasMagicLink:
    membership = magic_link.membership
    link = membership.canvas_course_link
    subject = f"Your BioBoost login link for {link.course.title}"
    body = canvas_magic_link_body(course_title=link.course.title, magic_url=absolute_magic_url, expires_at=magic_link.expires_at)
    payload, _headers = _canvas_request_json(
        urljoin(f"{canvas_api_base_url()}/", "conversations"),
        method="POST",
        form_data={
            "recipients[]": [membership.canvas_user.canvas_user_id],
            "subject": subject,
            "body": body,
            "force_new": 1,
            "context_code": f"course_{link.canvas_course_id}",
        },
    )
    message_id = ""
    if isinstance(payload, list) and payload:
        first_item = payload[0]
        if isinstance(first_item, dict):
            message_id = str(first_item.get("id") or "")
    magic_link.sent_canvas_message_id = message_id
    magic_link.sent_canvas_subject = subject
    magic_link.save(update_fields=["sent_canvas_message_id", "sent_canvas_subject", "updated_at"])
    return magic_link


def create_canvas_embed_launch_page(link: CanvasCourseLink, *, launch_url: str, page_key: str) -> str:
    launch_url_value = str(launch_url or "").strip()
    if not launch_url_value:
        raise CanvasAPIError("BioBoost could not build a Canvas launch page for this course.")
    launch_page_title = f"BioBoost launch {str(page_key or '').strip()[:8] or timezone.now().strftime('%Y%m%d%H%M%S')}"
    iframe_title = html.escape(f"{link.course.title} Canvas launch", quote=True)
    iframe_src = html.escape(launch_url_value, quote=True)
    body = (
        "<p>BioBoost is opening below inside Canvas.</p>"
        f'<p><iframe style="overflow: hidden; background: #ffffff; border: 0px none currentcolor;" '
        f'title="{iframe_title}" src="{iframe_src}" width="100%" height="900" loading="lazy" referrerpolicy="unsafe-url"></iframe></p>'
        "<p>If the launcher below does not open automatically, return to your Canvas inbox and use the newest BioBoost message.</p>"
    )
    payload, _headers = _canvas_request_json(
        urljoin(f"{canvas_api_base_url()}/", f"courses/{int(link.canvas_course_id)}/pages"),
        method="POST",
        form_data={
            "wiki_page[title]": launch_page_title,
            "wiki_page[body]": body,
            "wiki_page[published]": 1,
            "wiki_page[editing_roles]": "teachers",
        },
    )
    if not isinstance(payload, dict):
        raise CanvasAPIError("Canvas launch page creation returned an unexpected response.")
    page_url = str(payload.get("html_url") or "").strip()
    if page_url:
        return page_url
    page_slug = str(payload.get("url") or "").strip()
    if page_slug:
        return urljoin(f"{canvas_root_url()}/", f"courses/{int(link.canvas_course_id)}/pages/{page_slug}")
    raise CanvasAPIError("Canvas launch page creation returned an unexpected response.")


def canvas_magic_link_absolute_url(request, magic_link: CanvasMagicLink) -> str:
    return request.build_absolute_uri(reverse("standalone:canvas_magic", args=[magic_link.token]))
