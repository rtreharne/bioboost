from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable

from sympy import Eq, Symbol, diff, expand, factor, integrate, latex, simplify

from standalone.models import ContentChunk, CourseBlock, CourseImport, LearningObjective, MathsGeneratorSpec
from standalone.services.math_questions import (
    MATH_NOTATION_PROFILE,
    is_math_generation_target,
    validate_math_mcq_payload,
)


SUPPORTED_ARCHETYPES = {
    "linear_equation_one_variable",
    "expand_single_bracket",
    "expand_double_bracket",
    "factorise_quadratic_monic",
    "solve_quadratic_factorisable",
    "simultaneous_linear_equations",
    "simplify_indices",
    "differentiate_polynomial",
    "integrate_polynomial",
    "equation_of_straight_line",
    "arithmetic_sequence_nth_term",
}

ARCHETYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("simultaneous_linear_equations", re.compile(r"\bsimultaneous|two equations\b", re.IGNORECASE)),
    ("solve_quadratic_factorisable", re.compile(r"\bsolve\b.*\bquadratic|\bquadratic\b.*\bsolve\b", re.IGNORECASE)),
    ("factorise_quadratic_monic", re.compile(r"\bfactoris\w*\b.*\bquadratic|\bquadratic\b.*\bfactoris\w*\b", re.IGNORECASE)),
    ("expand_double_bracket", re.compile(r"\bexpand\b.*\bdouble bracket|\btwo brackets|\bbinom", re.IGNORECASE)),
    ("expand_single_bracket", re.compile(r"\bexpand\b.*\bbracket", re.IGNORECASE)),
    ("simplify_indices", re.compile(r"\bindices|index laws|powers\b", re.IGNORECASE)),
    ("differentiate_polynomial", re.compile(r"\bdifferentiat\w*\b", re.IGNORECASE)),
    ("integrate_polynomial", re.compile(r"\bintegrat\w*\b", re.IGNORECASE)),
    ("equation_of_straight_line", re.compile(r"\bstraight line|gradient|intercept\b", re.IGNORECASE)),
    ("arithmetic_sequence_nth_term", re.compile(r"\barithmetic sequence|nth term|sequence rule\b", re.IGNORECASE)),
    ("linear_equation_one_variable", re.compile(r"\bsolve\b.*\blinear equation|\bone variable\b", re.IGNORECASE)),
]

DISTRACTOR_MODELS = {
    "linear_equation_one_variable": ["sign_error", "inverse_operation_error", "coefficient_division_error"],
    "expand_single_bracket": ["distribution_error", "sign_error", "dropped_constant"],
    "expand_double_bracket": ["missing_middle_term", "sign_error", "constant_product_error"],
    "factorise_quadratic_monic": ["sign_error", "factor_pair_error", "constant_sign_error"],
    "solve_quadratic_factorisable": ["sign_error", "factor_pair_error", "missing_root"],
    "simultaneous_linear_equations": ["coordinate_swap", "sign_error", "substitution_error"],
    "simplify_indices": ["add_powers_incorrectly", "subtract_powers_incorrectly", "multiply_coefficients"],
    "differentiate_polynomial": ["power_unchanged", "missed_coefficient", "integrated_instead"],
    "integrate_polynomial": ["missed_division", "missing_constant", "differentiated_instead"],
    "equation_of_straight_line": ["swapped_gradient_intercept", "sign_error", "point_substitution_error"],
    "arithmetic_sequence_nth_term": ["off_by_one", "wrong_difference", "swapped_coefficient_constant"],
}
MATH_OBJECTIVE_FALLBACK_PATTERN = re.compile(
    r"\b("
    r"algebra|equation|simultaneous|quadratic|factoris|expand|simplif|indices|surd|"
    r"differentiat|integrat|gradient|straight line|sequence|nth term|trigon|identity|"
    r"modular|congruence|proof|graph|coordinate"
    r")\b",
    re.IGNORECASE,
)


def _trace_structured_maths(event: str, **context) -> None:
    payload = {"event": event, **context}
    print(f"[structured-maths] {json.dumps(payload, default=str, ensure_ascii=False)}", flush=True)


def source_import_for_block(block: CourseBlock) -> CourseImport | None:
    return (
        CourseImport.objects.filter(chapters__created_block=block)
        .order_by("-created_at", "-pk")
        .first()
    )


def use_structured_maths_for_block(block: CourseBlock) -> bool:
    course_import = source_import_for_block(block)
    return bool(course_import and course_import.use_structured_maths_generation)


def objective_requires_structured_maths(block: CourseBlock, objective: LearningObjective | None, chunk_text: str = "") -> bool:
    if objective is None:
        return False
    source_filename = ""
    asset = block.assets.order_by("pk").first()
    if asset is not None:
        source_filename = asset.original_filename
    return is_math_generation_target(
        objective_text=objective.text,
        chunk_text=chunk_text,
        block_title=block.title,
        source_filename=source_filename,
    )


def objective_is_maths_like(block: CourseBlock, objective: LearningObjective | None, chunk_text: str = "") -> bool:
    if objective is None:
        return False
    if objective_requires_structured_maths(block, objective, chunk_text):
        return True
    combined = "\n".join(part for part in [objective.text, block.title, chunk_text] if part)
    return bool(MATH_OBJECTIVE_FALLBACK_PATTERN.search(combined))


def infer_archetype(objective_text: str, *, block_title: str = "") -> str:
    combined = f"{objective_text}\n{block_title}"
    for archetype, pattern in ARCHETYPE_PATTERNS:
        if pattern.search(combined):
            return archetype
    return ""


def _spec_generator_id(archetype: str, objective: LearningObjective) -> str:
    base = archetype or "unsupported"
    return f"{base}:{objective.pk}"


def sync_structured_maths_specs_for_block(block: CourseBlock) -> list[MathsGeneratorSpec]:
    course_import = source_import_for_block(block)
    if not course_import or not course_import.use_structured_maths_generation:
        return []

    combined_text = "\n\n".join(
        asset.extracted_text for asset in block.assets.order_by("pk") if getattr(asset, "extracted_text", "").strip()
    )
    synced_specs: list[MathsGeneratorSpec] = []
    for objective in block.learning_objectives.order_by("position", "pk"):
        if not objective_is_maths_like(block, objective, combined_text):
            continue
        archetype = infer_archetype(objective.text, block_title=block.title)
        generator_id = _spec_generator_id(archetype, objective)
        defaults = {
            "course": block.course,
            "source_import": course_import,
            "subject": "maths",
            "exam_level": "A-level",
            "topic": block.title,
            "chapter": block.title,
            "learning_objective_text": objective.text,
            "question_archetype": archetype or "unsupported",
            "difficulty": "core",
            "parameter_ranges": {"seeded": True},
            "constraints": {"deterministic_generation": True, "validated_with_sympy": True},
            "question_template_latex": "",
            "answer_logic": {"generate_backwards": True},
            "distractor_models": DISTRACTOR_MODELS.get(archetype, []),
            "validation_rules": [
                "exactly_one_correct_option",
                "all_options_unique",
                "sympy_validation",
                "safe_maths_only",
            ],
            "worked_solution_style": "concise_exam_steps",
        }
        spec, _ = MathsGeneratorSpec.objects.update_or_create(
            block=block,
            learning_objective=objective,
            generator_id=generator_id,
            defaults=defaults,
        )
        errors: list[str] = []
        status = MathsGeneratorSpec.Status.DRAFT
        if not archetype:
            status = MathsGeneratorSpec.Status.UNSUPPORTED
            errors.append("unsupported_archetype")
        elif archetype not in SUPPORTED_ARCHETYPES:
            status = MathsGeneratorSpec.Status.UNSUPPORTED
            errors.append("generator_not_implemented")
        else:
            status = MathsGeneratorSpec.Status.VALIDATED
        if spec.status != status or spec.validation_errors != errors:
            spec.status = status
            spec.validation_errors = errors
            spec.save(update_fields=["status", "validation_errors", "updated_at"])
        synced_specs.append(spec)
        _trace_structured_maths(
            "maths_spec_synced",
            block=block.title,
            block_id=block.pk,
            import_id=course_import.pk,
            use_structured_maths_generation=course_import.use_structured_maths_generation,
            objective=objective.text,
            archetype=spec.question_archetype,
            status=spec.status,
            errors=errors,
        )
    return synced_specs


@dataclass(frozen=True)
class GeneratedMathsQuestion:
    question_text: str
    correct_answer: str
    options: list[str]
    worked_solution: str
    answer_family: str
    equivalence_mode: str
    equivalence_variables: list[str]
    distractor_tags: list[str]
    source_subtopic: str
    generator_id: str
    seed: int
    validation_report: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        return {
            "question_type": "mcq",
            "stem": self.question_text,
            "correct_answers": [self.correct_answer],
            "distractors": self.options[1:],
            "further_study_questions": [
                "Which step in the method is most likely to cause an error here?",
                "How could you check the answer efficiently?",
                "What variation of this question would change the method slightly?",
            ],
            "explanation": self.worked_solution,
            "difficulty": "core",
            "math_metadata": {
                "answer_family": self.answer_family,
                "canonical_tex": self.correct_answer,
                "canonical_plain": self.correct_answer,
                "equivalence_mode": self.equivalence_mode,
                "equivalence_variables": self.equivalence_variables,
                "notation_profile": MATH_NOTATION_PROFILE,
                "distractor_tags": self.distractor_tags,
                "source_subtopic": self.source_subtopic,
                "generator_id": self.generator_id,
                "generator_seed": self.seed,
                "validation_report": self.validation_report,
                "structured_generation": True,
            },
        }


def _wrap_math(value: str) -> str:
    stripped = str(value).strip()
    if stripped.startswith(r"\(") and stripped.endswith(r"\)"):
        return stripped
    return rf"\({stripped}\)"


def _sympy_tex(expr) -> str:
    return _wrap_math(latex(simplify(expr)))


def _line_tex(m: int, c: int) -> str:
    if c == 0:
        rhs = f"{m}x"
    elif c > 0:
        rhs = f"{m}x + {c}"
    else:
        rhs = f"{m}x - {abs(c)}"
    return _wrap_math(f"y = {rhs}")


def _equation_solution_tex(values: list[int]) -> str:
    ordered = sorted(set(values))
    if len(ordered) == 1:
        return _wrap_math(f"x = {ordered[0]}")
    return _wrap_math(rf"x = {ordered[0]} \text{{ or }} x = {ordered[1]}")


def _coordinate_tex(x_value: int, y_value: int) -> str:
    return _wrap_math(f"({x_value},{y_value})")


def _sequence_rule_tex(difference: int, first_term: int) -> str:
    constant = first_term - difference
    if constant == 0:
        body = f"{difference}n"
    elif constant > 0:
        body = f"{difference}n + {constant}"
    else:
        body = f"{difference}n - {abs(constant)}"
    return _wrap_math(f"a_n = {body}")


def _validated_generated_question(
    *,
    stem: str,
    correct_answer: str,
    distractors: list[str],
    answer_family: str,
    equivalence_mode: str,
    equivalence_variables: list[str],
    distractor_tags: list[str],
    source_subtopic: str,
    worked_solution: str,
    generator_id: str,
    seed: int,
) -> GeneratedMathsQuestion:
    payload = validate_math_mcq_payload(
        {
            "stem": stem,
            "correct_answers": [correct_answer],
            "distractors": distractors,
            "math_metadata": {
                "answer_family": answer_family,
                "canonical_tex": correct_answer,
                "canonical_plain": correct_answer,
                "equivalence_mode": equivalence_mode,
                "equivalence_variables": equivalence_variables,
                "notation_profile": MATH_NOTATION_PROFILE,
                "distractor_tags": distractor_tags,
                "source_subtopic": source_subtopic,
            },
        },
        distractor_count=len(distractors),
        objective_text=source_subtopic,
        chunk_text=source_subtopic,
        explanation_text=worked_solution,
    )
    options = [payload["correct_answer"], *payload["distractors"]]
    validation_report = {
        "passed": True,
        "option_count": len(options),
        "unique_options": len(set(options)) == len(options),
        "validated_with_sympy": True,
    }
    return GeneratedMathsQuestion(
        question_text=payload["stem"],
        correct_answer=payload["correct_answer"],
        options=options,
        worked_solution=worked_solution,
        answer_family=answer_family,
        equivalence_mode=equivalence_mode,
        equivalence_variables=equivalence_variables,
        distractor_tags=distractor_tags,
        source_subtopic=source_subtopic,
        generator_id=generator_id,
        seed=seed,
        validation_report=validation_report,
    )


def _generate_linear_equation(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    solution = rng.choice([value for value in range(-6, 7) if value != 0])
    coefficient = rng.choice([2, 3, 4, 5, 6])
    constant = rng.randint(-9, 9)
    rhs = coefficient * solution + constant
    correct = _wrap_math(f"x = {solution}")
    distractors = [
        _wrap_math(f"x = {rhs - constant}"),
        _wrap_math(f"x = {-solution}"),
        _wrap_math(f"x = {solution + 1}"),
    ]
    stem = rf"Solve {_wrap_math(f'{coefficient}x + {constant} = {rhs}')}. Which answer is correct?"
    worked = (
        rf"Rearrange to get {_wrap_math(f'{coefficient}x = {rhs - constant}')}. "
        rf"Then divide by {coefficient}, so {correct}."
    )
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="equation_solution",
        equivalence_mode="literal",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["linear_equation_one_variable"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_expand_single_bracket(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    a = rng.choice([2, 3, 4, 5])
    b = rng.choice([value for value in range(-5, 6) if value not in {0}])
    c = rng.choice([value for value in range(-8, 9) if value not in {0}])
    expr = a * (b * x + c)
    correct_expr = expand(expr)
    correct = _sympy_tex(correct_expr)
    distractors = [
        _sympy_tex(a * b * x + c),
        _sympy_tex(a * (b * x) - a * c),
        _sympy_tex((a + b) * x + a * c),
    ]
    stem = rf"Expand {_wrap_math(latex(expr))}."
    worked = rf"Distribute {a} across the bracket: {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="expression",
        equivalence_mode="sympy",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["expand_single_bracket"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_expand_double_bracket(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    a = rng.choice([value for value in range(-6, 7) if value not in {0}])
    b = rng.choice([value for value in range(-6, 7) if value not in {0, a}])
    expr = (x + a) * (x + b)
    correct_expr = expand(expr)
    correct = _sympy_tex(correct_expr)
    distractors = [
        _sympy_tex(x**2 + (a + b) * x + a + b),
        _sympy_tex(x**2 + (a * b) * x + a + b),
        _sympy_tex(x**2 + (a - b) * x + a * b),
    ]
    stem = rf"Expand {_wrap_math(latex(expr))}."
    worked = rf"Use FOIL or distribution to get {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="expression",
        equivalence_mode="sympy",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["expand_double_bracket"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_factorise_quadratic(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    r1 = rng.choice([value for value in range(-6, 7) if value not in {0}])
    r2 = rng.choice([value for value in range(-6, 7) if value not in {0, r1}])
    expr = expand((x - r1) * (x - r2))
    correct = _sympy_tex(factor(expr))
    distractors = [
        _wrap_math(latex((x + r1) * (x + r2))),
        _wrap_math(latex((x - r1) * (x + r2))),
        _wrap_math(latex((x + r1) * (x - r2))),
    ]
    stem = rf"Factorise {_wrap_math(latex(expr))}."
    worked = rf"Look for two numbers with sum {-(r1 + r2)} and product {r1 * r2}. So the factorised form is {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="expression",
        equivalence_mode="sympy",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["factorise_quadratic_monic"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_solve_quadratic(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    r1 = rng.choice([value for value in range(-6, 7) if value != 0])
    r2 = rng.choice([value for value in range(-6, 7) if value not in {0, r1}])
    expr = expand((x - r1) * (x - r2))
    correct = _equation_solution_tex([r1, r2])
    distractors = [
        _equation_solution_tex([-r1, -r2]),
        _equation_solution_tex([r1, r2 + 1]),
        _wrap_math(f"x = {r1}"),
    ]
    stem = rf"Solve {_wrap_math(latex(Eq(expr, 0)))}. Which answer is correct?"
    worked = rf"Factorise the quadratic and set each factor equal to zero, giving {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="equation_solution",
        equivalence_mode="literal",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["solve_quadratic_factorisable"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_simultaneous_equations(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x_value = rng.choice([value for value in range(-5, 6) if value != 0])
    y_value = rng.choice([value for value in range(-5, 6) if value not in {0, x_value}])
    a, b, d, e = 2, -3, 1, 4
    c = a * x_value + b * y_value
    f = d * x_value + e * y_value
    correct = _coordinate_tex(x_value, y_value)
    distractors = [
        _coordinate_tex(y_value, x_value),
        _coordinate_tex(-x_value, y_value),
        _coordinate_tex(x_value, -y_value),
    ]
    stem = (
        rf"Solve the simultaneous equations {_wrap_math(f'{a}x - 3y = {c}')}"
        rf" and {_wrap_math(f'x + 4y = {f}')}. Which ordered pair is correct?"
    )
    worked = rf"Substitute or eliminate one variable, then solve for the pair. The solution is {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="coordinate",
        equivalence_mode="ordered_pair",
        equivalence_variables=["x", "y"],
        distractor_tags=DISTRACTOR_MODELS["simultaneous_linear_equations"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_simplify_indices(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    a = rng.randint(2, 6)
    b = rng.randint(2, 6)
    c = rng.randint(1, 4)
    expr = (x**a * x**b) / x**c
    correct_expr = simplify(expr)
    correct = _sympy_tex(correct_expr)
    distractors = [
        _sympy_tex(x ** (a + b + c)),
        _sympy_tex(x ** (a + b - c + 1)),
        _sympy_tex(x ** (a * b - c)),
    ]
    stem = rf"Simplify {_wrap_math(latex(expr))}."
    worked = rf"Add powers when multiplying and subtract powers when dividing, so {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="expression",
        equivalence_mode="sympy",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["simplify_indices"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_differentiate_polynomial(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    coefficients = [rng.choice([2, 3, 4, 5]), rng.choice([2, 3, 4]), rng.choice([-5, -3, 3, 5])]
    expr = coefficients[0] * x**3 + coefficients[1] * x**2 + coefficients[2] * x
    derivative = diff(expr, x)
    correct = _sympy_tex(derivative)
    distractors = [
        _sympy_tex(coefficients[0] * x**3 + coefficients[1] * x + coefficients[2]),
        _sympy_tex(coefficients[0] * 3 * x**2 + coefficients[1] * x**2 + coefficients[2]),
        _sympy_tex(integrate(expr, x)),
    ]
    stem = rf"Differentiate {_wrap_math(latex(expr))} with respect to {_wrap_math('x')}."
    worked = rf"Apply the power rule term by term. The derivative is {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="derivative",
        equivalence_mode="sympy",
        equivalence_variables=["x"],
        distractor_tags=DISTRACTOR_MODELS["differentiate_polynomial"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_integrate_polynomial(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    x = Symbol("x")
    coefficients = [rng.choice([2, 3, 4, 5]), rng.choice([2, 3, 4]), rng.choice([-6, -4, 4, 6])]
    expr = coefficients[0] * x**2 + coefficients[1] * x + coefficients[2]
    antiderivative = integrate(expr, x)
    correct = _wrap_math(f"{latex(antiderivative)} + C")
    distractors = [
        _wrap_math(latex(diff(expr, x))),
        _wrap_math(latex(antiderivative)),
        _wrap_math(f"{latex(coefficients[0] * x**3 + coefficients[1] * x**2 + coefficients[2] * x)} + C"),
    ]
    stem = rf"Integrate {_wrap_math(latex(expr))} with respect to {_wrap_math('x')}."
    worked = rf"Increase each power by 1, divide by the new power, and add a constant. So the answer is {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="antiderivative",
        equivalence_mode="sympy",
        equivalence_variables=["x", "C"],
        distractor_tags=DISTRACTOR_MODELS["integrate_polynomial"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_equation_of_straight_line(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    m = rng.choice([value for value in range(-5, 6) if value not in {0}])
    c = rng.randint(-6, 6)
    x_value = rng.randint(-3, 4)
    y_value = m * x_value + c
    correct = _line_tex(m, c)
    distractors = [
        _line_tex(c if c != 0 else 1, m),
        _line_tex(-m, c),
        _line_tex(m, -c),
    ]
    stem = (
        rf"Which equation represents the straight line with gradient {m} "
        rf"that passes through {_coordinate_tex(x_value, y_value)}?"
    )
    worked = rf"Use {_wrap_math('y = mx + c')} and substitute the point to find the intercept. The equation is {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="function_rule",
        equivalence_mode="literal",
        equivalence_variables=["x", "y"],
        distractor_tags=DISTRACTOR_MODELS["equation_of_straight_line"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


def _generate_arithmetic_sequence(seed: int, spec: MathsGeneratorSpec) -> GeneratedMathsQuestion:
    rng = random.Random(seed)
    first_term = rng.randint(-5, 8)
    difference = rng.choice([value for value in range(-5, 6) if value not in {0}])
    second_term = first_term + difference
    third_term = second_term + difference
    correct = _sequence_rule_tex(difference, first_term)
    distractors = [
        _sequence_rule_tex(difference, second_term),
        _sequence_rule_tex(second_term if second_term != 0 else 1, first_term),
        _sequence_rule_tex(-difference, first_term),
    ]
    stem = rf"The first three terms of an arithmetic sequence are {first_term}, {second_term}, {third_term}. Find the nth term."
    worked = rf"The common difference is {difference}. Using {_wrap_math('a_n = a_1 + (n-1)d')}, the nth term is {correct}."
    return _validated_generated_question(
        stem=stem,
        correct_answer=correct,
        distractors=distractors,
        answer_family="function_rule",
        equivalence_mode="literal",
        equivalence_variables=["n"],
        distractor_tags=DISTRACTOR_MODELS["arithmetic_sequence_nth_term"],
        source_subtopic=spec.learning_objective_text,
        worked_solution=worked,
        generator_id=spec.generator_id,
        seed=seed,
    )


GENERATOR_REGISTRY: dict[str, Callable[[int, MathsGeneratorSpec], GeneratedMathsQuestion]] = {
    "linear_equation_one_variable": _generate_linear_equation,
    "expand_single_bracket": _generate_expand_single_bracket,
    "expand_double_bracket": _generate_expand_double_bracket,
    "factorise_quadratic_monic": _generate_factorise_quadratic,
    "solve_quadratic_factorisable": _generate_solve_quadratic,
    "simultaneous_linear_equations": _generate_simultaneous_equations,
    "simplify_indices": _generate_simplify_indices,
    "differentiate_polynomial": _generate_differentiate_polynomial,
    "integrate_polynomial": _generate_integrate_polynomial,
    "equation_of_straight_line": _generate_equation_of_straight_line,
    "arithmetic_sequence_nth_term": _generate_arithmetic_sequence,
}


def generate_structured_maths_payload(
    *,
    chunk: ContentChunk,
    objective: LearningObjective,
    distractor_count: int,
    question_variant_index: int = 0,
) -> dict[str, object]:
    if distractor_count != 3:
        raise ValueError("Structured maths generators currently require exactly 3 distractors.")
    spec = (
        MathsGeneratorSpec.objects.filter(
            block=chunk.block,
            learning_objective=objective,
            status=MathsGeneratorSpec.Status.VALIDATED,
        )
        .order_by("pk")
        .first()
    )
    if spec is None:
        unsupported = (
            MathsGeneratorSpec.objects.filter(block=chunk.block, learning_objective=objective)
            .order_by("pk")
            .first()
        )
        reason = "unsupported_archetype"
        if unsupported is not None and unsupported.validation_errors:
            reason = ", ".join(str(item) for item in unsupported.validation_errors)
        raise ValueError(f"Structured maths generation is enabled for this upload but this objective is unavailable: {reason}.")
    generator = GENERATOR_REGISTRY.get(spec.question_archetype)
    if generator is None:
        raise ValueError("Structured maths generation is enabled for this upload but no validated generator is available.")
    seed_material = f"{spec.pk}:{chunk.pk}:{objective.pk}:{question_variant_index}"
    seed = int(sha256(seed_material.encode("utf-8")).hexdigest()[:12], 16)
    generated = generator(seed, spec)
    payload = generated.to_payload()
    _trace_structured_maths(
        "maths_question_generated",
        block=chunk.block.title,
        block_id=chunk.block.pk,
        objective=objective.text,
        generator_id=spec.generator_id,
        archetype=spec.question_archetype,
        seed=seed,
        use_structured_maths_generation=True,
    )
    return payload
