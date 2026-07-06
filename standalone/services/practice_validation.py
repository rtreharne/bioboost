from django.utils import timezone

from standalone.models import Course, CourseBlock, QuestionBankItem


_BASE_PRACTICE_VALIDATION_TYPES = (
    QuestionBankItem.QuestionType.MCQ,
    QuestionBankItem.QuestionType.MAQ,
)


def practice_validation_enabled_question_types(
    block: CourseBlock,
    *,
    include_written: bool = True,
) -> tuple[str, ...]:
    enabled = list(_BASE_PRACTICE_VALIDATION_TYPES)
    if float(block.question_numeric_ratio_percent or 0) > 0:
        enabled.append(QuestionBankItem.QuestionType.NUM)
    if include_written:
        enabled.append(QuestionBankItem.QuestionType.WAQ)
    return tuple(enabled)


def question_is_practice_validation_eligible(
    question: QuestionBankItem,
    *,
    include_written: bool = True,
) -> bool:
    question_type = str(getattr(question, "question_type", "") or "")
    if question_type not in {
        QuestionBankItem.QuestionType.MCQ,
        QuestionBankItem.QuestionType.NUM,
        QuestionBankItem.QuestionType.MAQ,
        QuestionBankItem.QuestionType.WAQ,
    }:
        return False
    if question_type == QuestionBankItem.QuestionType.NUM:
        return float(question.block.question_numeric_ratio_percent or 0) > 0
    if question_type == QuestionBankItem.QuestionType.WAQ:
        return include_written
    return True


def released_practice_validation_pool_count(
    course: Course,
    *,
    approved_only: bool = False,
    today=None,
    include_written: bool = True,
) -> int:
    today = today or timezone.localdate()
    queryset = course.question_bank_items.filter(
        bank_type=QuestionBankItem.BankType.PRACTICE,
        block__available_from__lte=today,
    ).select_related("block", "block__config")
    if approved_only:
        queryset = queryset.filter(status=QuestionBankItem.Status.APPROVED)
    return sum(
        1
        for question in queryset
        if question_is_practice_validation_eligible(question, include_written=include_written)
    )


def released_validation_pool_count(
    course: Course,
    *,
    approved_only: bool = False,
    today=None,
    include_written: bool = True,
) -> int:
    today = today or timezone.localdate()
    queryset = course.question_bank_items.filter(
        bank_type=QuestionBankItem.BankType.VALIDATION,
        block__available_from__lte=today,
    )
    if approved_only:
        queryset = queryset.filter(status=QuestionBankItem.Status.APPROVED)
    if not include_written:
        queryset = queryset.exclude(question_type=QuestionBankItem.QuestionType.WAQ)
    return queryset.count()
