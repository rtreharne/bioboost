from __future__ import annotations

import json
import re
from typing import Any

from django.conf import settings
from openai import OpenAI
from sympy import Symbol, simplify, solve
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


MATH_NOTATION_PROFILE = "edexcel_pure_y1"
MATH_ANSWER_FAMILIES = {
    "expression",
    "equation_solution",
    "inequality",
    "interval_set",
    "coordinate",
    "function_rule",
    "derivative",
    "antiderivative",
    "trig_identity",
    "probability_notation",
    "vector",
    "conceptual",
}
MATH_EQUIVALENCE_MODES = {"sympy", "inequality", "interval", "ordered_pair", "literal"}
MATH_GENERATION_MODE_SYMBOLIC = "symbolic_math"
MATH_GENERATION_MODE_CONTEXTUAL_NUMERIC = "contextual_numeric_math"
MATH_GENERATION_MODE_GENERIC = "non_math_or_generic"
MATH_KEYWORD_PATTERN = re.compile(
    r"\b("
    r"algebra|quadratic|inequalit|binomial|surd|factor|indices|graph|circle|polynomial|"
    r"trigon|sine|cosine|tangent|vector|differentiat|integrat|logarithm|exponent|"
    r"stationary point|gradient|normal|tangent|proof|function|equation|solve|expand|simplif|"
    r"probability|union|intersection|complement|conditional"
    r")",
    re.IGNORECASE,
)
MATH_SUBTOPIC_RE = re.compile(
    r"^\s*(?P<number>\d{1,2}\.\d{1,2})\.?\s+(?P<title>[A-Z][A-Za-z0-9 ,:;'\-/()&=+*^<>≤≥∩∪]+?)(?:\s+\d{1,4})?\s*$",
    re.MULTILINE,
)
MATH_SKIP_TITLES = {
    "mixed exercise",
    "review exercise",
    "practice exam paper",
    "answers",
    "index",
    "overarching themes",
}
MATH_PROFILE_FILENAME_RE = re.compile(
    r"(edexcel.*pure.*year\s*1|pure mathematics.*year\s*1|new edexcel pure year 1)",
    re.IGNORECASE,
)
MATH_INLINE_DELIMITER_RE = re.compile(r"\\\(|\\\)|\\\[|\\\]")
MATH_DELIMITED_BLOCK_RE = re.compile(r"(\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))")
LATEX_FRACTION_RE = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
ORDERED_PAIR_RE = re.compile(r"^\(?\s*(.+?)\s*,\s*(.+?)\s*\)?$")
COORDINATE_OR_INTERVAL_SNIPPET_RE = re.compile(r"[\(\[]\s*[^()\[\]\n]+?\s*,\s*[^()\[\]\n]+?\s*[\)\]]")
INEQUALITY_RE = re.compile(
    r"^(?P<left>.+?)\s*(?P<op>\\\\leq|\\\\le|<=|≤|\\\\geq|\\\\ge|>=|≥|<|>|=)\s*(?P<right>.+)$"
)
INTERVAL_RE = re.compile(
    r"^(?:[A-Za-z]\s*\\\\in\s*)?(?P<left_bracket>[\(\[])\s*(?P<left>.+?)\s*,\s*(?P<right>.+?)\s*(?P<right_bracket>[\)\]])$"
)
MATH_ANSWER_TAIL_RE = re.compile(r"\b(?:is|are|was|were|equals?|equal to|given by|at)\b\s*(?P<tail>.+)$", re.IGNORECASE)
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)
SYMPY_FUNCTIONS = {
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "log",
    "ln",
    "exp",
    "sqrt",
    "Abs",
}
LATEX_TO_TEXT_REPLACEMENTS = {
    r"\times": "×",
    r"\cdot": "·",
    r"\leq": "≤",
    r"\le": "≤",
    r"\geq": "≥",
    r"\ge": "≥",
    r"\neq": "≠",
    r"\ne": "≠",
    r"\cup": "∪",
    r"\cap": "∩",
    r"\in": "∈",
    r"\infty": "∞",
    r"\theta": "θ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\lambda": "λ",
    r"\pi": "π",
}
MATH_EXPLANATION_INLINE_BOUNDARY_WORDS = {
    "and",
    "as",
    "at",
    "because",
    "before",
    "between",
    "but",
    "by",
    "for",
    "from",
    "gives",
    "if",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "since",
    "that",
    "then",
    "therefore",
    "thus",
    "to",
    "when",
    "where",
    "while",
    "with",
}
RAW_MATH_EXPLANATION_CLAUSE_RE = re.compile(
    r"(?P<expr>(?:(?<!\\)(?:Delta|alpha|beta|gamma|delta|theta|lambda|pi|sigma|phi|omega)|\\[A-Za-z]+|[Δα-ωΑ-Ω])\s*=\s*[^.?!]+)"
)
MATH_EXPLANATION_CONCLUSION_MARKER_RE = re.compile(
    r"\b(?:therefore|hence|thus|so|correct answer|answer is|solution is|simplified answer)\b",
    re.IGNORECASE,
)
MATH_EXPLANATION_OPTION_DISCLAIMER_RE = re.compile(
    r"\b(?:given the options|problem had errors|intentional distractor|intended error correction|best .* matching the intended error correction)\b",
    re.IGNORECASE,
)
MULTI_VALUE_MATH_STEM_RE = re.compile(
    r"\b(?:roots|solutions|points of intersection|intersections|x-coordinates|stationary points|turning points)\b",
    re.IGNORECASE,
)
GREEK_WORD_TO_TEX = {
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "delta": r"\delta",
    "theta": r"\theta",
    "lambda": r"\lambda",
    "pi": r"\pi",
    "sigma": r"\sigma",
    "phi": r"\phi",
    "omega": r"\omega",
    "Delta": r"\Delta",
}
SYMBOLIC_MATH_OBJECTIVE_PATTERN = re.compile(
    r"\b("
    r"algebra|algebraic|manipulation|expression|factoris|expand|simplif|surd|exact form|"
    r"equation|inequalit|identity|differentiat|integrat|derivative|antiderivative|"
    r"stationary point|graph|turning point|coordinate|vector|probability notation|"
    r"union|intersection|complement|conditional|function rule|proof"
    r")",
    re.IGNORECASE,
)
CONTEXTUAL_NUMERIC_OBJECTIVE_PATTERN = re.compile(
    r"\b("
    r"calculate|estimate|determine|work out|find|evaluate|model|interpret"
    r")\b",
    re.IGNORECASE,
)
CONTEXTUAL_NUMERIC_TARGET_PATTERN = re.compile(
    r"\b("
    r"area|areas|volume|volumes|surface area|perimeter|length|width|height|distance|speed|"
    r"time|rate|gradient|probability|percentage|profit|revenue|cost|mass|angle|temperature"
    r")\b",
    re.IGNORECASE,
)
GEOMETRY_ALGEBRA_OBJECTIVE_PATTERN = re.compile(
    r"\b(area|areas|volume|volumes|surface area|perimeter|geometr(?:y|ic)|length|width|height)\b",
    re.IGNORECASE,
)
SYMBOLIC_MARKER_PATTERN = re.compile(
    r"(\\[A-Za-z]+|[A-Za-z]\s*\(|\b(?:x|y|n|k|theta)\b|\bP\s*\(|[=<>≤≥∪∩^])"
)


def edexcel_pure_math_guidance() -> str:
    return (
        "Use Edexcel Pure Year 1 / AS notation. Keep mathematical expressions in LaTeX-style delimiters such as "
        r"\(...\) or \[...\]. Prefer concise symbolic MCQ options, keep one best answer only, and avoid mixing "
        "notation styles inside one question. When integration is tested, include + C in antiderivatives. Use "
        "interval notation only when the question angle clearly asks for solution sets."
    )


def looks_like_edexcel_pure_math_source(*texts: str) -> bool:
    joined = "\n".join(str(text or "") for text in texts if str(text or "").strip())
    if not joined:
        return False
    if _looks_like_curve_intersection_context(joined):
        return True
    return bool(MATH_PROFILE_FILENAME_RE.search(joined) or len(MATH_KEYWORD_PATTERN.findall(joined)) >= 3)


def extract_math_subtopic_objectives(text: str, *, max_items: int = 8) -> list[str]:
    matches = list(MATH_SUBTOPIC_RE.finditer(str(text or "")))
    if len(matches) < 2:
        return []

    objectives: list[str] = []
    seen: set[str] = set()
    for match in matches:
        title = re.sub(r"\s+", " ", match.group("title")).strip(" .:-")
        lowered = title.lower()
        if not title:
            continue
        if any(lowered.startswith(skip) for skip in MATH_SKIP_TITLES):
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        objectives.append(title)
        if len(objectives) >= max_items:
            break
    return objectives


def is_math_generation_target(*, objective_text: str = "", chunk_text: str = "", block_title: str = "", source_filename: str = "") -> bool:
    return looks_like_edexcel_pure_math_source(objective_text, chunk_text, block_title, source_filename)


def math_topic_family(objective_text: str, context_text: str = "") -> str:
    combined = f"{objective_text} {context_text}".lower()
    if _looks_like_curve_intersection_context(combined):
        return "algebra"
    if any(term in combined for term in ("integrat", "antiderivative", "area under")):
        return "calculus"
    if any(term in combined for term in ("differentiat", "gradient", "stationary point", "normal", "tangent")):
        return "calculus"
    if any(term in combined for term in ("trigon", "sine", "cosine", "tangent", "quadrant")):
        return "trigonometry"
    if any(term in combined for term in ("vector", "position vector", "magnitude")):
        return "vector"
    if any(term in combined for term in ("probability", "union", "intersection", "complement", "conditional")):
        return "probability"
    if any(term in combined for term in ("logarithm", "exponential", "indices", "binomial", "quadratic", "surd", "polynomial", "inequalit")):
        return "algebra"
    return "mathematics"


def classify_math_objective(objective_text: str = "", chunk_text: str = "") -> str:
    if not is_math_generation_target(objective_text=objective_text, chunk_text=chunk_text):
        return MATH_GENERATION_MODE_GENERIC

    combined = f"{objective_text} {chunk_text}".lower()
    if SYMBOLIC_MATH_OBJECTIVE_PATTERN.search(combined):
        return MATH_GENERATION_MODE_SYMBOLIC
    if CONTEXTUAL_NUMERIC_OBJECTIVE_PATTERN.search(combined) and CONTEXTUAL_NUMERIC_TARGET_PATTERN.search(combined):
        return MATH_GENERATION_MODE_CONTEXTUAL_NUMERIC
    if math_topic_family(objective_text, chunk_text) in {"algebra", "calculus", "trigonometry", "vector", "probability"}:
        return MATH_GENERATION_MODE_SYMBOLIC
    return MATH_GENERATION_MODE_CONTEXTUAL_NUMERIC


def preferred_math_answer_families(objective_text: str, context_text: str = "") -> list[str]:
    combined = f"{objective_text} {context_text}".lower()
    if _looks_like_curve_intersection_context(combined):
        return ["equation_solution", "coordinate"]
    if any(term in combined for term in ("inequalit", "solution set", "interval")):
        return ["inequality", "interval_set"]
    if any(term in combined for term in ("turning point", "coordinate", "stationary point")):
        return ["coordinate", "equation_solution"]
    if any(term in combined for term in ("differentiat", "gradient")):
        return ["derivative", "function_rule"]
    if any(term in combined for term in ("integrat", "antiderivative")):
        return ["antiderivative", "function_rule"]
    if any(term in combined for term in ("probability", "union", "intersection", "complement", "conditional")):
        return ["probability_notation"]
    if any(term in combined for term in ("trigon", "identity")):
        return ["trig_identity", "expression"]
    if any(term in combined for term in ("vector", "position vector")):
        return ["vector"]
    if any(term in combined for term in ("solve", "roots", "equation")):
        return ["equation_solution", "expression"]
    return ["expression", "function_rule"]


def math_symbol_heuristics(objective_text: str, context_text: str = "") -> dict[str, Any]:
    if not is_math_generation_target(objective_text=objective_text, chunk_text=context_text):
        return {}

    combined = f"{objective_text} {context_text}".lower()
    preferred_variables = ["x"]
    if any(term in combined for term in ("circle", "coordinate", "graph", "function")):
        preferred_variables = ["x", "y"]
    if any(term in combined for term in ("vector", "position vector")):
        preferred_variables = ["a", "b"]
    if any(term in combined for term in ("probability", "union", "intersection", "complement", "conditional")):
        preferred_variables = ["A", "B"]
    if any(term in combined for term in ("trigon", "sine", "cosine", "tangent", "quadrant")):
        preferred_variables = ["x", "theta"]

    return {
        "topic_family": math_topic_family(objective_text, context_text),
        "preferred_variables": preferred_variables,
        "preferred_notation": MATH_NOTATION_PROFILE,
        "angle_mode": "symbolic_mcq",
        "requires_constant_of_integration": any(term in combined for term in ("integrat", "antiderivative")),
        "source": "deterministic_math",
    }


def _looks_like_curve_intersection_context(text: str) -> bool:
    lowered = str(text or "").lower()
    if _looks_like_axis_intercept_transformation_context(lowered):
        return False
    return "intersection" in lowered and any(
        term in lowered
        for term in (
            "curve",
            "curves",
            "graph",
            "graphs",
            "simultaneous",
            "coordinate",
            "coordinates",
            "x-coordinate",
            "points of intersection",
        )
    )


def _looks_like_axis_intercept_transformation_context(text: str) -> bool:
    lowered = str(text or "").lower()
    has_axis_signal = any(term in lowered for term in ("axis", "axes", "x-intercept", "y-intercept", "intercept"))
    has_graph_signal = any(term in lowered for term in ("graph", "curve", "function"))
    has_transform_signal = any(term in lowered for term in ("transform", "translation", "translated", "shift", "reflection", "stretch"))
    return has_axis_signal and has_graph_signal and has_transform_signal


def _parse_json_object(raw_output: str) -> dict[str, Any]:
    cleaned = (raw_output or "").strip()
    if not cleaned:
        raise ValueError("OpenAI returned an empty maths question payload.")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))
    object_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if object_match:
        return json.loads(object_match.group(0))
    raise ValueError("OpenAI did not return parseable JSON for maths question generation.")


def _math_mcq_candidate_schema(distractor_count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question_type": {"type": "string", "enum": ["mcq"]},
            "stem": {"type": "string", "minLength": 1},
            "correct_answers": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
            "distractors": {
                "type": "array",
                "minItems": distractor_count,
                "maxItems": distractor_count,
                "items": {"type": "string", "minLength": 1},
            },
            "further_study_questions": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string", "minLength": 1},
            },
            "explanation": {"type": "string", "minLength": 1},
            "difficulty": {"type": "string", "minLength": 1},
            "math_metadata": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "answer_family": {"type": "string", "enum": sorted(MATH_ANSWER_FAMILIES)},
                    "canonical_tex": {"type": "string", "minLength": 1},
                    "canonical_plain": {"type": "string", "minLength": 1},
                    "equivalence_mode": {"type": "string", "enum": sorted(MATH_EQUIVALENCE_MODES)},
                    "equivalence_variables": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "maxItems": 4,
                    },
                    "notation_profile": {"type": "string", "minLength": 1},
                    "distractor_tags": {
                        "type": "array",
                        "minItems": distractor_count,
                        "maxItems": distractor_count,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "source_subtopic": {"type": "string", "minLength": 1},
                },
                "required": [
                    "answer_family",
                    "canonical_tex",
                    "canonical_plain",
                    "equivalence_mode",
                    "equivalence_variables",
                    "notation_profile",
                    "distractor_tags",
                    "source_subtopic",
                ],
            },
        },
        "required": [
            "question_type",
            "stem",
            "correct_answers",
            "distractors",
            "further_study_questions",
            "explanation",
            "difficulty",
            "math_metadata",
        ],
    }


def _format_int_tex(value: int) -> str:
    return str(int(value))


def _format_linear_tex(coefficient: int, constant: int) -> str:
    if coefficient == 0:
        expression = _format_int_tex(constant)
    elif coefficient == 1:
        expression = "x"
    elif coefficient == -1:
        expression = "-x"
    else:
        expression = f"{coefficient}x"

    if constant > 0:
        expression += f" + {constant}"
    elif constant < 0:
        expression += f" - {abs(constant)}"
    return expression


def _format_quadratic_tex(linear_coefficient: int, constant: int) -> str:
    expression = "x^2"
    if linear_coefficient > 0:
        expression += f" + {linear_coefficient}x"
    elif linear_coefficient < 0:
        expression += f" - {abs(linear_coefficient)}x"
    if constant > 0:
        expression += f" + {constant}"
    elif constant < 0:
        expression += f" - {abs(constant)}"
    return expression


def _solution_set_option_tex(values: tuple[int, int]) -> str:
    left, right = sorted(values)
    return rf"\(x = {left} \text{{ or }} x = {right}\)"


def _factor_from_root_tex(root: int) -> str:
    if root < 0:
        return f"(x + {abs(root)})"
    if root == 0:
        return "x"
    return f"(x - {root})"


def _math_seed(*parts: Any) -> int:
    joined = "|".join(str(part or "") for part in parts)
    return sum((index + 1) * ord(character) for index, character in enumerate(joined))


def _combined_topic_text(objective_text: str, chunk_text: str = "") -> str:
    return f"{objective_text} {chunk_text}".lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _clean_topic_label(objective_text: str, context_text: str = "") -> str:
    source = _normalize_whitespace(objective_text or context_text or "this maths topic")
    source = re.sub(r"^(?:understand|use|apply|solve|find|calculate|simplify|differentiate|integrate)\b\s*", "", source, flags=re.IGNORECASE)
    words = re.findall(r"[A-Za-z0-9+\-^]+", source)
    if not words:
        return "this maths topic"
    return " ".join(words[:7]).lower()


def _select_template(templates: list[dict[str, Any]], *, seed_parts: tuple[Any, ...], variant_index: int) -> dict[str, Any]:
    return templates[(_math_seed(*seed_parts) + variant_index) % len(templates)]


def _local_template_payload(
    template: dict[str, Any],
    *,
    source_subtopic: str,
    distractor_count: int,
) -> dict[str, Any] | None:
    correct_answer = normalize_math_tex(str(template["correct"]), wrap_if_formula=True)
    distractors: list[str] = []
    distractor_tags: list[str] = []
    seen_options = {math_tex_to_plain(correct_answer).lower()}

    for raw_option, tag in template["distractors"]:
        option = normalize_math_tex(str(raw_option), wrap_if_formula=True)
        key = math_tex_to_plain(option).lower()
        if not option or key in seen_options:
            continue
        seen_options.add(key)
        distractors.append(option)
        distractor_tags.append(str(tag))
        if len(distractors) >= distractor_count:
            break

    if len(distractors) < distractor_count:
        return None

    return {
        "question_type": "mcq",
        "stem": normalize_math_stem_text(str(template["stem"])),
        "correct_answers": [correct_answer],
        "distractors": distractors,
        "further_study_questions": list(template["further_study_questions"])[:3],
        "explanation": normalize_math_explanation_text(str(template["explanation"])),
        "difficulty": str(template.get("difficulty") or "core"),
        "math_metadata": {
            "answer_family": str(template["answer_family"]),
            "canonical_tex": correct_answer,
            "canonical_plain": math_tex_to_plain(correct_answer),
            "equivalence_mode": str(template.get("equivalence_mode") or "literal"),
            "equivalence_variables": list(template.get("equivalence_variables") or ["x"])[:4],
            "notation_profile": MATH_NOTATION_PROFILE,
            "distractor_tags": distractor_tags,
            "source_subtopic": source_subtopic,
        },
    }


def _local_surd_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("surd", "sqrt", "radical", "rationalis", "exact form")):
        return None
    templates = [
        {
            "stem": r"Which option is equivalent to \(\sqrt{18}\) in simplified surd form?",
            "correct": r"\(3\sqrt{2}\)",
            "distractors": [
                (r"\(2\sqrt{2}\)", "missed_square_factor"),
                (r"\(9\sqrt{2}\)", "square_root_multiplier_error"),
                (r"\(3\sqrt{3}\)", "wrong_remaining_factor"),
                (r"\(6\sqrt{2}\)", "doubled_multiplier"),
            ],
            "explanation": r"Use the square factor: \(\sqrt{18} = \sqrt{9 \times 2} = 3\sqrt{2}\). Therefore, the correct answer is \(3\sqrt{2}\).",
        },
        {
            "stem": r"Which option is equivalent to \(\sqrt{48}\) in simplified surd form?",
            "correct": r"\(4\sqrt{3}\)",
            "distractors": [
                (r"\(3\sqrt{4}\)", "not_simplified"),
                (r"\(8\sqrt{3}\)", "square_root_multiplier_error"),
                (r"\(4\sqrt{6}\)", "wrong_remaining_factor"),
                (r"\(2\sqrt{12}\)", "partly_simplified"),
            ],
            "explanation": r"Use the square factor: \(\sqrt{48} = \sqrt{16 \times 3} = 4\sqrt{3}\). Therefore, the correct answer is \(4\sqrt{3}\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "surd"), variant_index=variant_index)
    template = {**template, "answer_family": "expression", "equivalence_mode": "sympy", "equivalence_variables": ["x"], "further_study_questions": [
        "How do square factors help simplify surds?",
        "How can you check that a surd is fully simplified?",
        "Why is exact form useful before decimal approximation?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_quadratic_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("quadratic", "factoris", "factoriz", "roots", "solve", "equation")):
        return None
    templates = [
        {
            "stem": r"Solve \(x^2 - 5x + 6 = 0\).",
            "correct": r"\(x = 2 \text{ or } x = 3\)",
            "distractors": [
                (r"\(x = -2 \text{ or } x = -3\)", "sign_error"),
                (r"\(x = 1 \text{ or } x = 6\)", "factor_pair_error"),
                (r"\(x = 2\)", "missed_solution"),
                (r"\(x = -1 \text{ or } x = -6\)", "constant_sign_confusion"),
            ],
            "explanation": r"Factorise \(x^2 - 5x + 6\) as \((x - 2)(x - 3)\), then set each factor equal to zero. Therefore, the correct answer is \(x = 2 \text{ or } x = 3\).",
        },
        {
            "stem": r"Solve \(x^2 + x - 12 = 0\).",
            "correct": r"\(x = -4 \text{ or } x = 3\)",
            "distractors": [
                (r"\(x = 4 \text{ or } x = -3\)", "sign_error"),
                (r"\(x = -2 \text{ or } x = 6\)", "factor_pair_error"),
                (r"\(x = 3\)", "missed_solution"),
                (r"\(x = 4 \text{ or } x = 3\)", "sum_product_confusion"),
            ],
            "explanation": r"Factorise \(x^2 + x - 12\) as \((x + 4)(x - 3)\), then set each factor equal to zero. Therefore, the correct answer is \(x = -4 \text{ or } x = 3\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "quadratic"), variant_index=variant_index)
    template = {**template, "answer_family": "equation_solution", "equivalence_mode": "literal", "equivalence_variables": ["x"], "further_study_questions": [
        "How do the factors of the constant term connect to the roots?",
        "Why must both factors be set equal to zero?",
        "How can substitution check both solutions?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_inequality_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if "inequalit" not in combined:
        return None
    templates = [
        {
            "stem": r"Solve the inequality \(2x + 3 < 11\).",
            "correct": r"\(x < 4\)",
            "distractors": [
                (r"\(x > 4\)", "reversed_inequality"),
                (r"\(x < 7\)", "missed_division"),
                (r"\(x > 7\)", "missed_division_and_reversed"),
                (r"\(x < 14\)", "added_instead_of_subtracted"),
            ],
            "explanation": r"Subtract 3 to get \(2x < 8\), then divide by 2. Therefore, the correct answer is \(x < 4\).",
        },
        {
            "stem": r"Solve the inequality \(5 - 3x \leq 14\).",
            "correct": r"\(x \geq -3\)",
            "distractors": [
                (r"\(x \leq -3\)", "did_not_reverse_after_negative_division"),
                (r"\(x \geq 3\)", "sign_error"),
                (r"\(x \leq 3\)", "sign_and_direction_error"),
                (r"\(x \geq -19\)", "missed_division"),
            ],
            "explanation": r"Subtract 5 to get \(-3x \leq 9\), then divide by \(-3\) and reverse the inequality. Therefore, the correct answer is \(x \geq -3\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "inequality"), variant_index=variant_index)
    template = {**template, "answer_family": "inequality", "equivalence_mode": "inequality", "equivalence_variables": ["x"], "further_study_questions": [
        "When does an inequality sign reverse?",
        "How can a boundary value check the solution?",
        "How would the solution appear on a number line?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_derivative_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("differentiat", "derivative", "gradient")):
        return None
    templates = [
        {
            "stem": r"Differentiate \(f(x) = 3x^2 + 4x\).",
            "correct": r"\(6x + 4\)",
            "distractors": [
                (r"\(3x + 4\)", "power_not_multiplied"),
                (r"\(6x^2 + 4\)", "power_not_reduced"),
                (r"\(x^3 + 2x^2\)", "integrated_instead"),
                (r"\(6x\)", "lost_linear_term"),
            ],
            "explanation": r"Apply the power rule: \(\frac{d}{dx}(3x^2)=6x\) and \(\frac{d}{dx}(4x)=4\). Therefore, the correct answer is \(6x + 4\).",
        },
        {
            "stem": r"Differentiate \(y = 5x^3 - 2x\).",
            "correct": r"\(15x^2 - 2\)",
            "distractors": [
                (r"\(5x^2 - 2\)", "power_not_multiplied"),
                (r"\(15x^3 - 2\)", "power_not_reduced"),
                (r"\(\frac{5}{4}x^4 - x^2\)", "integrated_instead"),
                (r"\(15x^2\)", "lost_linear_term"),
            ],
            "explanation": r"Apply the power rule: \(\frac{d}{dx}(5x^3)=15x^2\) and \(\frac{d}{dx}(-2x)=-2\). Therefore, the correct answer is \(15x^2 - 2\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "derivative"), variant_index=variant_index)
    template = {**template, "answer_family": "derivative", "equivalence_mode": "sympy", "equivalence_variables": ["x"], "further_study_questions": [
        "How does the power rule change the coefficient?",
        "What happens to a linear term when differentiating?",
        "How could the derivative be checked from the original graph?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_antiderivative_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("integrat", "antiderivative")):
        return None
    templates = [
        {
            "stem": r"Find \(\int (3x^2 + 4)\,dx\).",
            "correct": r"\(x^3 + 4x + C\)",
            "distractors": [
                (r"\(x^3 + 4x\)", "missing_constant"),
                (r"\(6x + 4 + C\)", "differentiated_instead"),
                (r"\(3x^3 + 4x + C\)", "coefficient_not_divided"),
                (r"\(\frac{3}{2}x^3 + 4x + C\)", "wrong_power_rule"),
            ],
            "explanation": r"Increase the power by 1 and divide by the new power: \(\int 3x^2\,dx = x^3\) and \(\int 4\,dx = 4x\). Therefore, the correct answer is \(x^3 + 4x + C\).",
        },
        {
            "stem": r"Find \(\int (8x^3 - 6x)\,dx\).",
            "correct": r"\(2x^4 - 3x^2 + C\)",
            "distractors": [
                (r"\(2x^4 - 3x^2\)", "missing_constant"),
                (r"\(24x^2 - 6 + C\)", "differentiated_instead"),
                (r"\(8x^4 - 6x^2 + C\)", "coefficient_not_divided"),
                (r"\(4x^4 - 6x^2 + C\)", "partial_power_rule_error"),
            ],
            "explanation": r"Increase each power by 1 and divide by the new power: \(\int 8x^3\,dx = 2x^4\) and \(\int -6x\,dx = -3x^2\). Therefore, the correct answer is \(2x^4 - 3x^2 + C\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "antiderivative"), variant_index=variant_index)
    template = {**template, "answer_family": "antiderivative", "equivalence_mode": "sympy", "equivalence_variables": ["x", "C"], "further_study_questions": [
        "Why is the constant of integration needed?",
        "How is integration related to differentiation?",
        "How can differentiating your answer check it?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_turning_point_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("turning point", "stationary point", "vertex")):
        return None
    templates = [
        {
            "stem": r"The curve \(y = (x - 2)^2 - 3\) has a turning point. Which option gives its coordinates?",
            "correct": r"\((2, -3)\)",
            "distractors": [
                (r"\((-2, -3)\)", "horizontal_sign_error"),
                (r"\((2, 3)\)", "vertical_sign_error"),
                (r"\((-3, 2)\)", "coordinates_swapped"),
                (r"\((0, -3)\)", "ignored_horizontal_shift"),
            ],
            "explanation": r"In completed square form \(y = (x - h)^2 + k\), the turning point is \((h, k)\). Here \(h=2\) and \(k=-3\). Therefore, the correct answer is \((2, -3)\).",
        },
        {
            "stem": r"The curve \(y = (x + 1)^2 + 4\) has a turning point. Which option gives its coordinates?",
            "correct": r"\((-1, 4)\)",
            "distractors": [
                (r"\((1, 4)\)", "horizontal_sign_error"),
                (r"\((-1, -4)\)", "vertical_sign_error"),
                (r"\((4, -1)\)", "coordinates_swapped"),
                (r"\((0, 4)\)", "ignored_horizontal_shift"),
            ],
            "explanation": r"In completed square form \(y = (x - h)^2 + k\), the turning point is \((h, k)\). Here \(h=-1\) and \(k=4\). Therefore, the correct answer is \((-1, 4)\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "turning_point"), variant_index=variant_index)
    template = {**template, "answer_family": "coordinate", "equivalence_mode": "ordered_pair", "equivalence_variables": ["x", "y"], "further_study_questions": [
        "How does completed square form reveal a turning point?",
        "Why does the sign inside the bracket reverse?",
        "How could a quick sketch check the coordinate?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_axis_intercepts_transformation_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _looks_like_axis_intercept_transformation_context(combined):
        return None
    templates = [
        {
            "stem": r"The graph \(y=(x-2)^2-1\) is a translation of \(y=x^2\). Which option gives all the points where the graph meets the coordinate axes?",
            "correct": r"\((1,0), (3,0), (0,3)\)",
            "distractors": [
                (r"\((-1,0), (3,0), (0,3)\)", "horizontal_translation_sign_error"),
                (r"\((1,0), (3,0), (0,-1)\)", "used_vertical_shift_as_y_intercept"),
                (r"\((2,0), (0,3)\)", "confused_vertex_with_intercept"),
                (r"\((0,1), (0,3), (3,0)\)", "swapped_axis_coordinates"),
            ],
            "explanation": r"For x-axis intercepts set \(y=0\): \((x-2)^2-1=0\), so \(x=1\) or \(x=3\). For the y-axis intercept set \(x=0\), giving \(y=3\). Therefore, the intercept points are \((1,0), (3,0), (0,3)\).",
        },
        {
            "stem": r"The graph \(y=(x+1)^2-4\) is a translation of \(y=x^2\). Which option gives all the points where the graph meets the coordinate axes?",
            "correct": r"\((-3,0), (1,0), (0,-3)\)",
            "distractors": [
                (r"\((3,0), (-1,0), (0,-3)\)", "horizontal_translation_sign_error"),
                (r"\((-3,0), (1,0), (0,-4)\)", "used_vertical_shift_as_y_intercept"),
                (r"\((-1,0), (0,-3)\)", "confused_vertex_with_intercept"),
                (r"\((0,-3), (-3,0), (1,0)\)", "swapped_axis_labels"),
            ],
            "explanation": r"For x-axis intercepts set \(y=0\): \((x+1)^2-4=0\), so \(x=-3\) or \(x=1\). For the y-axis intercept set \(x=0\), giving \(y=-3\). Therefore, the intercept points are \((-3,0), (1,0), (0,-3)\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "axis_intercepts_transformation"), variant_index=variant_index)
    template = {**template, "answer_family": "coordinate", "equivalence_mode": "literal", "equivalence_variables": ["x", "y"], "further_study_questions": [
        "How do you find x-axis intercepts from a graph equation?",
        "How do you find the y-axis intercept after a transformation?",
        "How can a sketch check whether the intercepts make sense?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_probability_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("probability", "union", "intersection", "complement", "conditional")):
        return None
    templates = [
        {
            "stem": r"Which notation represents the probability that event \(A\) or event \(B\) occurs?",
            "correct": r"\(P(A \cup B)\)",
            "distractors": [
                (r"\(P(A \cap B)\)", "intersection_not_union"),
                (r"\(P(A')\)", "complement_not_union"),
                (r"\(P(A \mid B)\)", "conditional_not_union"),
                (r"\(P(A)P(B)\)", "independence_product_confusion"),
            ],
            "explanation": r"The word or corresponds to the union symbol \(\cup\). Therefore, the correct answer is \(P(A \cup B)\).",
        },
        {
            "stem": r"Which notation represents the probability that event \(A\) occurs given that event \(B\) has occurred?",
            "correct": r"\(P(A \mid B)\)",
            "distractors": [
                (r"\(P(B \mid A)\)", "conditional_reversed"),
                (r"\(P(A \cap B)\)", "intersection_not_conditional"),
                (r"\(P(A \cup B)\)", "union_not_conditional"),
                (r"\(P(A')\)", "complement_not_conditional"),
            ],
            "explanation": r"The vertical bar means given that, with the event after the bar as the condition. Therefore, the correct answer is \(P(A \mid B)\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "probability"), variant_index=variant_index)
    template = {**template, "answer_family": "probability_notation", "equivalence_mode": "literal", "equivalence_variables": ["A", "B"], "further_study_questions": [
        "How do union and intersection differ in probability notation?",
        "What does the vertical bar mean in conditional probability?",
        "How can a Venn diagram represent the notation?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_vector_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if "vector" not in combined:
        return None
    templates = [
        {
            "stem": r"Given \(\mathbf{a}=\begin{pmatrix}2\\-1\end{pmatrix}\) and \(\mathbf{b}=\begin{pmatrix}3\\4\end{pmatrix}\), find \(\mathbf{a}+\mathbf{b}\).",
            "correct": r"\(\begin{pmatrix}5\\3\end{pmatrix}\)",
            "distractors": [
                (r"\(\begin{pmatrix}1\\5\end{pmatrix}\)", "subtracted_components"),
                (r"\(\begin{pmatrix}6\\-4\end{pmatrix}\)", "multiplied_components"),
                (r"\(\begin{pmatrix}5\\-5\end{pmatrix}\)", "sign_error"),
                (r"\(\begin{pmatrix}3\\5\end{pmatrix}\)", "swapped_component_sum"),
            ],
            "explanation": r"Add corresponding components: \(2+3=5\) and \(-1+4=3\). Therefore, the correct answer is \(\begin{pmatrix}5\\3\end{pmatrix}\).",
        },
        {
            "stem": r"Given \(\mathbf{p}=\begin{pmatrix}4\\1\end{pmatrix}\) and \(\mathbf{q}=\begin{pmatrix}-2\\5\end{pmatrix}\), find \(\mathbf{p}-\mathbf{q}\).",
            "correct": r"\(\begin{pmatrix}6\\-4\end{pmatrix}\)",
            "distractors": [
                (r"\(\begin{pmatrix}2\\6\end{pmatrix}\)", "added_components"),
                (r"\(\begin{pmatrix}-6\\4\end{pmatrix}\)", "subtraction_reversed"),
                (r"\(\begin{pmatrix}6\\4\end{pmatrix}\)", "sign_error"),
                (r"\(\begin{pmatrix}-8\\5\end{pmatrix}\)", "multiplied_components"),
            ],
            "explanation": r"Subtract corresponding components: \(4-(-2)=6\) and \(1-5=-4\). Therefore, the correct answer is \(\begin{pmatrix}6\\-4\end{pmatrix}\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "vector"), variant_index=variant_index)
    template = {**template, "answer_family": "vector", "equivalence_mode": "literal", "equivalence_variables": ["a", "b"], "further_study_questions": [
        "Why are vector operations performed component by component?",
        "How does subtraction differ from addition for vectors?",
        "How could the result be represented geometrically?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_trig_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not (
        _contains_any(combined, ("trigon", "sine", "cosine", "tangent"))
        or re.search(r"(?<![A-Za-z])(?:sin|cos|tan)(?![A-Za-z])", combined)
    ):
        return None
    templates = [
        {
            "stem": r"Which option states the Pythagorean trigonometric identity?",
            "correct": r"\(\sin^2 x + \cos^2 x = 1\)",
            "distractors": [
                (r"\(\sin x + \cos x = 1\)", "missing_squares"),
                (r"\(\sin^2 x - \cos^2 x = 1\)", "wrong_operation"),
                (r"\(\tan^2 x + \cos^2 x = 1\)", "wrong_function"),
                (r"\(\sin^2 x + \cos^2 x = 0\)", "wrong_constant"),
            ],
            "explanation": r"The standard Pythagorean identity links squared sine and cosine. Therefore, the correct answer is \(\sin^2 x + \cos^2 x = 1\).",
        },
        {
            "stem": r"Which option is equivalent to \(\tan x\) where the expression is defined?",
            "correct": r"\(\frac{\sin x}{\cos x}\)",
            "distractors": [
                (r"\(\frac{\cos x}{\sin x}\)", "reciprocal_error"),
                (r"\(\sin x \cos x\)", "product_confusion"),
                (r"\(\frac{1}{\cos x}\)", "secant_confusion"),
                (r"\(\frac{1}{\sin x}\)", "cosecant_confusion"),
            ],
            "explanation": r"The quotient identity for tangent is sine divided by cosine. Therefore, the correct answer is \(\frac{\sin x}{\cos x}\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "trig"), variant_index=variant_index)
    template = {**template, "answer_family": "trig_identity", "equivalence_mode": "literal", "equivalence_variables": ["x"], "further_study_questions": [
        "Which identities connect sine, cosine, and tangent?",
        "How can the unit circle explain the identity?",
        "When is a quotient identity undefined?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_algebra_expression_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    combined = _combined_topic_text(objective_text, chunk_text)
    if not _contains_any(combined, ("algebra", "expand", "simplif", "expression", "polynomial", "indices", "binomial")):
        return None
    templates = [
        {
            "stem": r"Expand and simplify \((2x + 1)(x + 3)\).",
            "correct": r"\(2x^2 + 7x + 3\)",
            "distractors": [
                (r"\(2x^2 + 6x + 3\)", "missed_inner_term"),
                (r"\(2x^2 + x + 3\)", "missed_outer_term"),
                (r"\(2x^2 + 5x + 3\)", "combined_coefficients_only"),
                (r"\(2x^2 + 7x\)", "lost_constant"),
            ],
            "explanation": r"Multiply each term: \(2x \cdot x = 2x^2\), \(2x \cdot 3 = 6x\), \(1 \cdot x = x\), and \(1 \cdot 3 = 3\). Therefore, the correct answer is \(2x^2 + 7x + 3\).",
        },
        {
            "stem": r"Simplify \(3x + 2(4x - 5)\).",
            "correct": r"\(11x - 10\)",
            "distractors": [
                (r"\(7x - 10\)", "missed_distribution"),
                (r"\(11x - 5\)", "constant_not_multiplied"),
                (r"\(11x + 10\)", "sign_error"),
                (r"\(5(4x - 5)\)", "combined_unlike_terms"),
            ],
            "explanation": r"Distribute first: \(2(4x - 5)=8x-10\), then combine like terms with \(3x\). Therefore, the correct answer is \(11x - 10\).",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "algebra_expression"), variant_index=variant_index)
    template = {**template, "answer_family": "expression", "equivalence_mode": "sympy", "equivalence_variables": ["x"], "further_study_questions": [
        "How can expanding brackets be checked term by term?",
        "Which terms are like terms?",
        "What common sign errors happen when simplifying?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_conceptual_math_mcq_payload(
    objective_text: str,
    chunk_text: str,
    source_subtopic: str,
    distractor_count: int,
    variant_index: int,
) -> dict[str, Any] | None:
    topic_label = _clean_topic_label(objective_text, chunk_text)
    family = math_topic_family(objective_text, chunk_text)
    templates = [
        {
            "stem": f"When working on {topic_label}, which habit gives the most reliable mathematical solution?",
            "correct": "Set up the mathematical relationship first, solve it step by step, then check the result against the question.",
            "distractors": [
                ("Choose the option with the largest number because it is usually the most complete answer.", "largest_value_guess"),
                ("Skip the setup and try to match surface words in the question to an answer option.", "keyword_matching"),
                ("Round every value at the start so the arithmetic looks simpler.", "premature_rounding"),
                ("Use only the final line of working and ignore whether the result answers the question.", "unchecked_result"),
                ("Change notation between lines whenever it makes the expression shorter.", "notation_drift"),
            ],
            "explanation": "A reliable solution keeps the mathematical structure visible, works through each step, and checks that the final result answers the question. Therefore, the correct answer is set up the relationship, solve carefully, then check the result.",
        },
        {
            "stem": f"For a new {topic_label} question in {family}, which response best supports accurate problem solving?",
            "correct": "Identify the target quantity or object, write the relevant mathematical statement, and test the final answer.",
            "distractors": [
                ("Copy any formula that contains a familiar symbol, even if the quantities do not match.", "formula_grab"),
                ("Use the first numerical answer that appears during working as the final answer.", "intermediate_value"),
                ("Treat all answer choices as interchangeable if they use similar notation.", "notation_blur"),
                ("Ignore restrictions, signs, or domains unless the answer looks unusual.", "ignored_conditions"),
                ("Prefer a decimal answer even when the question calls for exact or symbolic form.", "format_mismatch"),
            ],
            "explanation": "Accurate problem solving starts by identifying the target, representing the situation mathematically, and checking the final answer. Therefore, the correct answer is identify the target, write the mathematical statement, and test the final answer.",
        },
    ]
    template = _select_template(templates, seed_parts=(objective_text, chunk_text, "conceptual"), variant_index=variant_index)
    template = {**template, "answer_family": "conceptual", "equivalence_mode": "literal", "equivalence_variables": ["x"], "further_study_questions": [
        f"What is the target object or quantity in {topic_label}?",
        "Which notation or relationship should be written before solving?",
        "How can the final answer be checked against the original question?",
    ]}
    return _local_template_payload(template, source_subtopic=source_subtopic, distractor_count=distractor_count)


def _local_math_mcq_payload(
    chunk,
    objective_text: str,
    source_subtopic: str,
    distractor_count: int,
    *,
    variant_index: int = 0,
) -> dict[str, Any] | None:
    chunk_text = getattr(chunk, "text", "") or ""
    generators = [
        lambda: _local_axis_intercepts_transformation_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_curve_intersection_mcq_payload(chunk, objective_text, source_subtopic, distractor_count),
        lambda: _local_turning_point_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_surd_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_inequality_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_antiderivative_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_derivative_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_probability_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_vector_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_trig_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_quadratic_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_algebra_expression_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
        lambda: _local_conceptual_math_mcq_payload(objective_text, chunk_text, source_subtopic, distractor_count, variant_index),
    ]
    for generator in generators:
        payload = generator()
        if payload:
            return payload
    return None


def _local_curve_intersection_mcq_payload(
    chunk,
    objective_text: str,
    source_subtopic: str,
    distractor_count: int,
) -> dict[str, Any] | None:
    if not _looks_like_curve_intersection_context(f"{objective_text} {getattr(chunk, 'text', '')}"):
        return None

    templates = [
        {"roots": (1, 3), "line_m": 2, "line_c": -1},
        {"roots": (-2, 4), "line_m": 1, "line_c": 3},
        {"roots": (-1, 2), "line_m": -1, "line_c": 4},
        {"roots": (2, 5), "line_m": 3, "line_c": -4},
    ]
    seed = int(getattr(chunk, "pk", 0) or 0) + sum(ord(character) for character in objective_text)
    template = templates[seed % len(templates)]
    root_a, root_b = template["roots"]
    line_m = template["line_m"]
    line_c = template["line_c"]

    quadratic_linear = line_m - (root_a + root_b)
    quadratic_constant = line_c + (root_a * root_b)
    quadratic_rhs = _format_quadratic_tex(quadratic_linear, quadratic_constant)
    linear_rhs = _format_linear_tex(line_m, line_c)
    intersection_equation = _format_quadratic_tex(-(root_a + root_b), root_a * root_b)
    factorised_equation = f"{_factor_from_root_tex(root_a)}{_factor_from_root_tex(root_b)}"
    correct_answer = _solution_set_option_tex((root_a, root_b))

    raw_distractors: list[tuple[tuple[int, int], str]] = [
        ((-root_a, -root_b), "sign_error"),
        ((root_a, root_b + 1), "constant_error"),
        ((root_a - 1, root_b), "factor_pair_error"),
        ((root_a + root_b, root_a * root_b), "sum_product_confusion"),
        ((root_a - 1, root_b + 1), "line_substitution_error"),
    ]
    distractors: list[str] = []
    distractor_tags: list[str] = []
    seen_options = {correct_answer}
    for values, tag in raw_distractors:
        option = _solution_set_option_tex(values)
        if option in seen_options:
            continue
        seen_options.add(option)
        distractors.append(option)
        distractor_tags.append(tag)
        if len(distractors) >= distractor_count:
            break

    if len(distractors) < distractor_count:
        return None

    return {
        "question_type": "mcq",
        "stem": (
            rf"Given the curves \(y = {quadratic_rhs}\) and \(y = {linear_rhs}\), "
            "which option gives the x-coordinates of their points of intersection?"
        ),
        "correct_answers": [correct_answer],
        "distractors": distractors,
        "further_study_questions": [
            "How do you form the equation for the intersection of two curves?",
            "How does factorising identify both intersection values?",
            "How can substitution check each x-coordinate?",
        ],
        "explanation": (
            rf"Set the two expressions for \(y\) equal: \({quadratic_rhs} = {linear_rhs}\). "
            rf"This simplifies to \({intersection_equation} = 0\), "
            rf"which factorises to \({factorised_equation} = 0\). "
            f"Therefore, the x-coordinates are {correct_answer}."
        ),
        "difficulty": "core",
        "math_metadata": {
            "answer_family": "equation_solution",
            "canonical_tex": correct_answer,
            "canonical_plain": f"x = {min(root_a, root_b)} or x = {max(root_a, root_b)}",
            "equivalence_mode": "literal",
            "equivalence_variables": ["x"],
            "notation_profile": MATH_NOTATION_PROFILE,
            "distractor_tags": distractor_tags,
            "source_subtopic": source_subtopic,
        },
    }


def build_math_mcq_payload(
    chunk,
    objective,
    distractor_count: int,
    *,
    teacher_guidance: str = "",
    avoid_question_angles: list[str] | None = None,
    question_variant_index: int = 0,
) -> dict[str, Any]:
    objective_text = getattr(objective, "text", "") or "Pure mathematics"
    source_subtopic = objective_text
    heuristics = math_symbol_heuristics(objective_text, chunk.text)
    generation_mode = classify_math_objective(objective_text, chunk.text)
    preferred_families = preferred_math_answer_families(objective_text, chunk.text)
    avoidance_prompt = ""
    if avoid_question_angles:
        avoidance_prompt = "\nAvoid repeating these recent angles:\n" + "\n".join(f"- {item}" for item in avoid_question_angles[:6])
    family_prompt = ", ".join(preferred_families)
    heuristics_prompt = json.dumps(heuristics, ensure_ascii=False, sort_keys=True)
    local_payload = _local_math_mcq_payload(
        chunk,
        objective_text,
        source_subtopic,
        distractor_count,
        variant_index=question_variant_index + len(avoid_question_angles or []),
    )
    if local_payload:
        return local_payload
    if not settings.OPENAI_API_KEY:
        raise ValueError("Maths question generation needs either a local template match or OPENAI_API_KEY.")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    prompt = f"""
Create one single-answer mathematics MCQ for Edexcel Pure Year 1 / AS and return strict JSON.

Rules:
- set question_type to "mcq"
- use TeX-first maths notation and delimit all mathematical expressions with \\(...\\) or \\[...\\]
- the item must be standalone and must not mention the textbook, chapter, source text, page, figure, or worked example
- produce exactly one mathematically best answer
- if the stem asks for roots, solutions, x-coordinates, stationary points, turning points, or points of intersection in the plural, the correct option must give the complete set of values together in one option
- do not use None of the above or All of the above
- keep all options in the same mathematical answer family
- make distractors plausible by reflecting real misconceptions such as sign errors, missed factors, missing + C, wrong branch, endpoint mistakes, wrong identity, or notation mixups
- if answer_family is antiderivative, the correct answer must include + C
- if answer_family is derivative, the correct answer must not include + C
- use concise symbolic options rather than prose when the topic allows it
- for answer families such as coordinate, interval_set, inequality, equation_solution, function_rule, derivative, antiderivative, vector, trig_identity, and probability_notation, make each option the mathematical object itself rather than a sentence like "The turning point is ..."
- canonical_tex must match the correct answer mathematically
- canonical_tex should usually be the exact symbolic content shown in the correct option, without any extra prose wrapper
- canonical_plain must be a readable plain-text fallback
- notation_profile must be "{MATH_NOTATION_PROFILE}"
- source_subtopic must be "{source_subtopic}"
- distractor_tags must have one tag per distractor in order
- use equivalence_mode "sympy" for standard algebraic/calculus expression equivalence when possible
- use equivalence_mode "inequality", "interval", "ordered_pair", or "literal" for the relevant families
- do not make the question purely numeric-only arithmetic if the objective is algebraic{avoidance_prompt}
- objective_mode is "{generation_mode}"
- prefer answer_family from: {family_prompt}
- use these deterministic maths heuristics: {heuristics_prompt}
- when the objective combines algebra with geometry or volume, ask for an expression, equation, or symbolic result rather than direct substitution into a numeric area or volume formula
- if objective_mode is "{MATH_GENERATION_MODE_SYMBOLIC}", the question must visibly involve symbolic unknowns, expressions, notation, or a solution set

Learning objective:
{objective_text}

Source text:
{chunk.text}

Teacher guidance:
{teacher_guidance or "(none)"}
""".strip()

    response = client.responses.create(
        model=settings.OPENAI_QUESTION_MODEL,
        instructions="Return one valid JSON object only.",
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        text={
            "format": {
                "type": "json_schema",
                "name": "math_mcq_candidate",
                "strict": True,
                "schema": _math_mcq_candidate_schema(distractor_count),
            }
        },
    )
    return _parse_json_object(getattr(response, "output_text", ""))


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_math_tex(value: str, *, wrap_if_formula: bool = False) -> str:
    cleaned = _normalize_whitespace(value)
    if not cleaned:
        return ""
    cleaned = re.sub(r"\$\$(.+?)\$\$", lambda match: rf"\[{match.group(1).strip()}\]", cleaned)
    cleaned = re.sub(r"\$(.+?)\$", lambda match: rf"\({match.group(1).strip()}\)", cleaned)
    cleaned = cleaned.replace("≤", r"\le").replace("≥", r"\ge")
    cleaned = cleaned.replace("∪", r"\cup").replace("∩", r"\cap")
    cleaned = cleaned.replace("−", "-")
    cleaned = re.sub(r"\\\(\s*", r"\(", cleaned)
    cleaned = re.sub(r"\s*\\\)", r"\)", cleaned)
    cleaned = re.sub(r"\\\[\s*", r"\[", cleaned)
    cleaned = re.sub(r"\s*\\\]", r"\]", cleaned)
    if wrap_if_formula and not MATH_INLINE_DELIMITER_RE.search(cleaned):
        formula_like = bool(re.search(r"[=^_<>]|\\[A-Za-z]+|\d+[A-Za-z]|[A-Za-z]\d|[()\[\],]", cleaned))
        if formula_like:
            cleaned = rf"\({cleaned}\)"
    return cleaned


def _consume_raw_latex_snippet(source: str, start: int) -> tuple[str, int] | None:
    if start < 0 or start >= len(source) or source[start] != "\\":
        return None

    cursor = start
    brace_depth = 0
    seen_command = False
    math_word_tokens = {"and", "or"}

    while cursor < len(source):
        character = source[cursor]

        if character == "\\":
            if cursor + 1 >= len(source):
                break
            next_character = source[cursor + 1]
            if next_character in "()[]":
                break
            if next_character.isalpha():
                seen_command = True
                cursor += 2
                while cursor < len(source) and source[cursor].isalpha():
                    cursor += 1
                continue
            if next_character in ",;:! ":
                cursor += 2
                continue
            break

        if brace_depth > 0:
            if character == "{":
                brace_depth += 1
            elif character == "}":
                brace_depth -= 1
            cursor += 1
            continue

        if character == "{":
            brace_depth = 1
            cursor += 1
            continue
        if character == "}":
            break
        if character.isdigit():
            cursor += 1
            continue
        if character.isalpha():
            word_match = re.match(r"[A-Za-z]+", source[cursor:])
            word = word_match.group(0) if word_match else ""
            if len(word) == 1 or word.lower() in math_word_tokens:
                cursor += len(word)
                continue
            break
        if character in "+-*/=^_()[]<>≤≥∪∩|,:":
            cursor += 1
            continue
        if character == ".":
            previous = source[cursor - 1] if cursor > start else ""
            next_character = source[cursor + 1] if cursor + 1 < len(source) else ""
            if previous.isdigit() and next_character.isdigit():
                cursor += 1
                continue
            break
        if character in ";!?":
            break
        if character.isspace():
            look_ahead = cursor
            while look_ahead < len(source) and source[look_ahead].isspace():
                look_ahead += 1
            if look_ahead >= len(source):
                break
            next_character = source[look_ahead]
            if next_character == "\\":
                if look_ahead + 1 < len(source) and source[look_ahead + 1].isalpha():
                    cursor = look_ahead
                    continue
                break
            if next_character.isdigit() or next_character in "+-*/=^_()[]<>≤≥∪∩|":
                cursor = look_ahead
                continue
            if next_character.isalpha():
                word_match = re.match(r"[A-Za-z]+", source[look_ahead:])
                word = word_match.group(0) if word_match else ""
                if len(word) == 1 or word.lower() in math_word_tokens:
                    cursor = look_ahead
                    continue
            break
        else:
            break

    candidate = source[start:cursor].rstrip()
    trailing_punctuation = ""
    while candidate and candidate[-1] in ",.;:":
        trailing_punctuation = candidate[-1] + trailing_punctuation
        candidate = candidate[:-1].rstrip()
    if not seen_command or not candidate or not re.search(r"\\[A-Za-z]+", candidate):
        return None
    return normalize_math_tex(candidate, wrap_if_formula=True) + trailing_punctuation, cursor


def _wrap_raw_latex_fragments_in_prose(text: str) -> str:
    protected_blocks: list[str] = []

    def protect_block(match: re.Match[str]) -> str:
        protected_blocks.append(normalize_math_tex(match.group(0)))
        return f"__MATH_BLOCK_{len(protected_blocks) - 1}__"

    cleaned = MATH_DELIMITED_BLOCK_RE.sub(protect_block, _normalize_whitespace(text))
    normalized_parts: list[str] = []
    cursor = 0

    while cursor < len(cleaned):
        if cleaned[cursor] != "\\":
            normalized_parts.append(cleaned[cursor])
            cursor += 1
            continue

        consumed = _consume_raw_latex_snippet(cleaned, cursor)
        if not consumed:
            normalized_parts.append(cleaned[cursor])
            cursor += 1
            continue

        snippet, next_cursor = consumed
        normalized_parts.append(snippet)
        cursor = next_cursor

    normalized = "".join(normalized_parts)
    for index, block in enumerate(protected_blocks):
        normalized = normalized.replace(f"__MATH_BLOCK_{index}__", block)
    return normalized


def _inline_display_blocks_in_stem(text: str) -> str:
    rebuilt: list[str] = []
    cursor = 0

    for match in MATH_DELIMITED_BLOCK_RE.finditer(text):
        rebuilt.append(text[cursor:match.start()])
        block = normalize_math_tex(match.group(0))
        if block.startswith(r"\[") and block.endswith(r"\]"):
            before = text[:match.start()]
            after = text[match.end():]
            prose_before = bool(re.search(r"[A-Za-z]", before))
            prose_after = bool(re.search(r"[A-Za-z?]", after))
            if prose_before or prose_after:
                body = block[2:-2].strip()
                while body and body[-1] in ".?!":
                    body = body[:-1].rstrip()
                block = rf"\({body}\)"
        rebuilt.append(block)
        cursor = match.end()

    rebuilt.append(text[cursor:])
    return "".join(rebuilt)


def normalize_math_stem_text(text: str) -> str:
    cleaned = _wrap_raw_latex_fragments_in_prose(text)
    if not cleaned:
        return ""
    return _inline_display_blocks_in_stem(cleaned)


def _read_braced_latex_segment(source: str, start: int) -> tuple[str, int] | None:
    if start < 0 or start >= len(source) or source[start] != "{":
        return None

    depth = 0
    for index in range(start, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:index], index + 1
    return None


def _replace_latex_fractions(source: str, replacer) -> str:
    rebuilt: list[str] = []
    cursor = 0

    while cursor < len(source):
        if source.startswith(r"\frac", cursor):
            numerator_segment = _read_braced_latex_segment(source, cursor + 5)
            if numerator_segment:
                numerator, next_cursor = numerator_segment
                denominator_segment = _read_braced_latex_segment(source, next_cursor)
                if denominator_segment:
                    denominator, cursor = denominator_segment
                    rebuilt.append(
                        replacer(
                            _replace_latex_fractions(numerator, replacer),
                            _replace_latex_fractions(denominator, replacer),
                        )
                    )
                    continue
        rebuilt.append(source[cursor])
        cursor += 1

    return "".join(rebuilt)


def math_tex_to_plain(value: str) -> str:
    plain = _normalize_whitespace(value)
    if not plain:
        return ""
    plain = _replace_latex_fractions(plain, lambda numerator, denominator: f"({numerator})/({denominator})")
    plain = plain.replace(r"\(", "").replace(r"\)", "")
    plain = plain.replace(r"\[", "").replace(r"\]", "")
    plain = plain.replace(r"\left", "").replace(r"\right", "")
    for source, target in LATEX_TO_TEXT_REPLACEMENTS.items():
        plain = plain.replace(source, target)
    plain = plain.replace("{", "").replace("}", "")
    return _normalize_whitespace(plain)


def _split_math_explanation_clause(expression: str) -> tuple[str, str]:
    source = str(expression or "").strip()
    equals_index = source.find("=")
    if equals_index < 0:
        return source, ""

    paren_depth = 0
    for index in range(equals_index + 1, len(source)):
        character = source[index]
        if character == "(":
            paren_depth += 1
            continue
        if character == ")" and paren_depth > 0:
            paren_depth -= 1
            continue
        if paren_depth != 0 or not character.isspace():
            continue
        boundary_match = re.match(r"\s+([A-Za-z][A-Za-z-]*)\b", source[index:])
        if boundary_match and boundary_match.group(1).lower() in MATH_EXPLANATION_INLINE_BOUNDARY_WORDS:
            return source[:index].rstrip(), source[index:]
    return source, ""


def _normalize_raw_math_explanation_clause(expression: str) -> str:
    cleaned = _normalize_whitespace(expression)
    if not cleaned:
        return ""
    for word, tex_command in GREEK_WORD_TO_TEX.items():
        cleaned = re.sub(rf"(?<!\\)\b{re.escape(word)}\b", lambda _match, replacement=tex_command: replacement, cleaned)
    cleaned = re.sub(r"(?<!\\)\btimes\b", r"\\times", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\\times\s*", r" \\times ", cleaned)
    return normalize_math_tex(cleaned, wrap_if_formula=True)


def normalize_math_explanation_text(text: str) -> str:
    cleaned = _normalize_whitespace(text)
    if not cleaned:
        return ""

    protected_blocks: list[str] = []

    def protect_block(match: re.Match[str]) -> str:
        protected_blocks.append(normalize_math_tex(match.group(0)))
        return f"__MATH_BLOCK_{len(protected_blocks) - 1}__"

    cleaned = MATH_DELIMITED_BLOCK_RE.sub(protect_block, cleaned)

    def replace_clause(match: re.Match[str]) -> str:
        clause, trailing_text = _split_math_explanation_clause(match.group("expr"))
        normalized_clause = _normalize_raw_math_explanation_clause(clause)
        return f"{normalized_clause}{trailing_text}"

    cleaned = RAW_MATH_EXPLANATION_CLAUSE_RE.sub(replace_clause, cleaned)
    for index, block in enumerate(protected_blocks):
        cleaned = cleaned.replace(f"__MATH_BLOCK_{index}__", block)
    return _wrap_raw_latex_fragments_in_prose(cleaned)


def _explanation_conclusion_alignment_issue(
    explanation: str,
    correct_answer: str,
    distractors: list[str],
    metadata: dict[str, Any],
) -> str:
    normalized_explanation = normalize_math_explanation_text(explanation)
    if not normalized_explanation:
        return ""

    candidate_blocks: list[str] = []
    has_conclusion_marker = False
    sentences = [segment.strip() for segment in re.split(r"(?<=[.?!])\s+", normalized_explanation) if segment.strip()]
    for sentence in reversed(sentences):
        blocks = [normalize_math_tex(block, wrap_if_formula=True) for block in MATH_DELIMITED_BLOCK_RE.findall(sentence)]
        if not blocks:
            continue
        candidate_blocks = blocks
        if MATH_EXPLANATION_CONCLUSION_MARKER_RE.search(sentence):
            has_conclusion_marker = True
            break
        break

    if not candidate_blocks:
        return ""

    conclusion_answer = candidate_blocks[-1]
    if math_options_equivalent(conclusion_answer, correct_answer, metadata):
        return ""
    if any(math_options_equivalent(conclusion_answer, distractor, metadata) for distractor in distractors):
        return "Maths MCQ explanation concludes with a distractor instead of the marked correct answer."
    if has_conclusion_marker:
        return "Maths MCQ explanation conclusion does not match any answer option."
    return ""


def _sympy_locals(expression: str) -> dict[str, Any]:
    locals_map: dict[str, Any] = {
        "pi": parse_expr("pi"),
        "E": parse_expr("E"),
    }
    tokens = set(re.findall(r"[A-Za-z]+", expression))
    for token in tokens:
        if token in SYMPY_FUNCTIONS or token in {"pi", "E"}:
            continue
        locals_map[token] = Symbol(token)
    return locals_map


def tex_to_sympy_expression(value: str) -> str:
    expression = normalize_math_tex(value)
    expression = expression.replace(r"\(", "").replace(r"\)", "")
    expression = expression.replace(r"\[", "").replace(r"\]", "")
    expression = expression.replace(r"\left", "").replace(r"\right", "")
    expression = _replace_latex_fractions(expression, lambda numerator, denominator: f"(({numerator}))/(({denominator}))")
    replacements = {
        r"\times": "*",
        r"\cdot": "*",
        r"\sin": "sin",
        r"\cos": "cos",
        r"\tan": "tan",
        r"\ln": "log",
        r"\log": "log",
        r"\exp": "exp",
        r"\sqrt": "sqrt",
        r"\pi": "pi",
        r"\theta": "theta",
        r"\alpha": "alpha",
        r"\beta": "beta",
        r"\gamma": "gamma",
        r"\lambda": "lambda",
    }
    for source, target in replacements.items():
        expression = expression.replace(source, target)
    expression = expression.replace("^", "**")
    expression = expression.replace("{", "(").replace("}", ")")
    return _normalize_whitespace(expression)


def _parse_sympy_expression(value: str):
    expression = tex_to_sympy_expression(value)
    if not expression:
        raise ValueError("Empty symbolic expression.")
    return parse_expr(expression, local_dict=_sympy_locals(expression), transformations=TRANSFORMATIONS, evaluate=True)


def _sympy_equivalent(left: str, right: str) -> bool:
    try:
        return simplify(_parse_sympy_expression(left) - _parse_sympy_expression(right)) == 0
    except Exception:  # noqa: BLE001
        return False


def _normalize_inequality_key(value: str) -> str:
    plain = math_tex_to_plain(value)
    match = INEQUALITY_RE.match(plain)
    if not match:
        raise ValueError("Invalid inequality format.")
    left = _normalize_whitespace(match.group("left"))
    op = match.group("op").replace(r"\leq", "<=").replace(r"\le", "<=").replace(r"\geq", ">=").replace(r"\ge", ">=")
    right = _normalize_whitespace(match.group("right"))
    if not left or not right:
        raise ValueError("Invalid inequality endpoints.")
    if left != "x":
        return f"{left} {op} {math_tex_to_plain(right)}"
    return f"x {op} {math_tex_to_plain(right)}"


def _normalize_interval_key(value: str) -> str:
    plain = math_tex_to_plain(value)
    plain = plain.replace("∞", "infinity")
    match = INTERVAL_RE.match(plain)
    if not match:
        raise ValueError("Invalid interval format.")
    left = _normalize_whitespace(match.group("left"))
    right = _normalize_whitespace(match.group("right"))
    return f"{match.group('left_bracket')}{left},{right}{match.group('right_bracket')}"


def _normalize_ordered_pair_key(value: str) -> str:
    plain = math_tex_to_plain(value)
    plain = plain.replace(r"\beginpmatrix", "").replace(r"\endpmatrix", "")
    match = ORDERED_PAIR_RE.match(plain)
    if not match:
        raise ValueError("Invalid ordered pair format.")
    left, right = match.groups()
    left_expr = tex_to_sympy_expression(left)
    right_expr = tex_to_sympy_expression(right)
    return f"({left_expr},{right_expr})"


def _looks_like_math_fragment(value: str) -> bool:
    plain = math_tex_to_plain(value)
    return bool(
        re.search(
            r"(\\[A-Za-z]+|[A-Za-z]\s*=|[()\[\],]|≤|≥|<|>|∪|∩|\bP\s*\(|\+\s*C\b|\btheta\b|\bpi\b|\bx\b|\by\b)",
            plain,
            flags=re.IGNORECASE,
        )
    )


def _append_math_candidate(candidates: list[str], value: str, *, wrap_if_formula: bool = True) -> None:
    normalized = normalize_math_tex(value, wrap_if_formula=wrap_if_formula)
    if normalized and normalized not in candidates:
        candidates.append(normalized)


def _math_equivalence_candidates(value: str, metadata: dict[str, Any]) -> list[str]:
    mode = str(metadata.get("equivalence_mode", "") or "").strip().lower()
    normalized = normalize_math_tex(value, wrap_if_formula=True)
    if not normalized:
        return []

    candidates: list[str] = []
    _append_math_candidate(candidates, normalized, wrap_if_formula=False)

    for block in MATH_DELIMITED_BLOCK_RE.findall(normalized):
        _append_math_candidate(candidates, block, wrap_if_formula=False)
        if block.startswith(r"\(") and block.endswith(r"\)"):
            _append_math_candidate(candidates, block[2:-2], wrap_if_formula=True)
        elif block.startswith(r"\[") and block.endswith(r"\]"):
            _append_math_candidate(candidates, block[2:-2], wrap_if_formula=True)

    plain = math_tex_to_plain(normalized)
    if mode in {"ordered_pair", "interval"}:
        for match in COORDINATE_OR_INTERVAL_SNIPPET_RE.finditer(plain):
            _append_math_candidate(candidates, match.group(0))

    if mode == "inequality":
        inequality_match = INEQUALITY_RE.search(plain)
        if inequality_match:
            _append_math_candidate(candidates, inequality_match.group(0))

    if mode == "literal" and ("P(" in plain or "∪" in plain or "∩" in plain):
        probability_match = re.search(r"(P\s*\([^()]+\)|[A-Za-z]\s*[∪∩]\s*[A-Za-z]|[A-Za-z]')", plain)
        if probability_match:
            _append_math_candidate(candidates, probability_match.group(0))

    tail_match = MATH_ANSWER_TAIL_RE.search(normalized)
    if tail_match:
        tail = tail_match.group("tail").strip(" .,:;")
        if tail and _looks_like_math_fragment(tail):
            _append_math_candidate(candidates, tail)

    if ":" in normalized:
        tail = normalized.rsplit(":", 1)[-1].strip(" .")
        if tail and _looks_like_math_fragment(tail):
            _append_math_candidate(candidates, tail)

    return candidates


def math_equivalence_key(value: str, metadata: dict[str, Any]) -> str:
    mode = str(metadata.get("equivalence_mode", "") or "").strip().lower()
    if mode == "sympy":
        expr = tex_to_sympy_expression(value)
        parsed = _parse_sympy_expression(value)
        return str(simplify(parsed))
    if mode == "inequality":
        return _normalize_inequality_key(value)
    if mode == "interval":
        return _normalize_interval_key(value)
    if mode == "ordered_pair":
        return _normalize_ordered_pair_key(value)
    return math_tex_to_plain(value).lower()


def _math_pair_equivalent(left: str, right: str, metadata: dict[str, Any]) -> bool:
    mode = str(metadata.get("equivalence_mode", "") or "").strip().lower()
    if mode == "sympy":
        return _sympy_equivalent(left, right)
    try:
        return math_equivalence_key(left, metadata) == math_equivalence_key(right, metadata)
    except Exception:  # noqa: BLE001
        return math_tex_to_plain(left).lower() == math_tex_to_plain(right).lower()


def math_options_equivalent(left: str, right: str, metadata: dict[str, Any]) -> bool:
    left_candidates = _math_equivalence_candidates(left, metadata) or [normalize_math_tex(left, wrap_if_formula=True)]
    right_candidates = _math_equivalence_candidates(right, metadata) or [normalize_math_tex(right, wrap_if_formula=True)]
    for left_candidate in left_candidates:
        for right_candidate in right_candidates:
            if _math_pair_equivalent(left_candidate, right_candidate, metadata):
                return True
    return False


def _option_family_source(value: str) -> str:
    normalized = normalize_math_tex(value, wrap_if_formula=True)
    if not normalized:
        return ""
    blocks = MATH_DELIMITED_BLOCK_RE.findall(normalized)
    if blocks:
        return blocks[-1]
    plain = math_tex_to_plain(normalized)
    snippet_match = COORDINATE_OR_INTERVAL_SNIPPET_RE.search(plain)
    if snippet_match:
        return snippet_match.group(0)
    tail_match = MATH_ANSWER_TAIL_RE.search(normalized)
    if tail_match:
        tail = tail_match.group("tail").strip(" .,:;")
        if tail and _looks_like_math_fragment(tail):
            return tail
    return normalized


def _option_answer_family(value: str) -> str:
    plain = math_tex_to_plain(_option_family_source(value))
    if any(token in plain for token in ("≤", "≥", "<", ">")):
        return "inequality"
    if plain.startswith("(") or plain.startswith("["):
        if "," in plain:
            if plain.endswith(")") or plain.endswith("]"):
                return "interval_or_coordinate"
    if "P(" in plain or "P (" in plain or "∪" in plain or "∩" in plain:
        return "probability_notation"
    if "\\vec" in value or "pmatrix" in value:
        return "vector"
    return "symbolic"


def _math_payload_symbolic_authenticity_error(
    *,
    stem: str,
    correct_answer: str,
    distractors: list[str],
    metadata: dict[str, Any],
    objective_text: str = "",
    chunk_text: str = "",
) -> str:
    mode = classify_math_objective(objective_text, chunk_text)
    if mode != MATH_GENERATION_MODE_SYMBOLIC:
        return ""

    answer_family = str(metadata.get("answer_family", "") or "")
    combined = " ".join([stem, correct_answer, *distractors])
    has_symbolic_markers = bool(SYMBOLIC_MARKER_PATTERN.search(combined))
    if SYMBOLIC_MATH_OBJECTIVE_PATTERN.search(objective_text) and GEOMETRY_ALGEBRA_OBJECTIVE_PATTERN.search(objective_text):
        if not has_symbolic_markers:
            return "Maths MCQ for algebraic geometry objectives must use expressions, unknowns, or derived equations rather than bare numeric substitution."
    if answer_family in {
        "expression",
        "equation_solution",
        "inequality",
        "function_rule",
        "derivative",
        "antiderivative",
        "trig_identity",
        "vector",
        "probability_notation",
    } and not has_symbolic_markers:
        return "Maths MCQ for a symbolic objective must visibly use symbolic notation or unknowns."

    return ""


def _answer_represents_multiple_values(answer: str, answer_family: str) -> bool:
    plain = math_tex_to_plain(answer).lower()
    if not plain:
        return False
    if answer_family == "coordinate":
        return len(COORDINATE_OR_INTERVAL_SNIPPET_RE.findall(plain)) >= 2
    if answer_family == "equation_solution":
        if plain.count("x =") >= 2:
            return True
        if plain.startswith("{") and plain.endswith("}") and "," in plain:
            return True
        return bool(re.search(r"\b(?:or|and)\b", plain))
    return False


def _math_payload_solution_cardinality_error(
    *,
    stem: str,
    correct_answer: str,
    distractors: list[str],
    metadata: dict[str, Any],
) -> str:
    answer_family = str(metadata.get("answer_family", "") or "")
    if answer_family not in {"equation_solution", "coordinate"}:
        return ""
    if not MULTI_VALUE_MATH_STEM_RE.search(math_tex_to_plain(stem)):
        return ""

    options = [correct_answer, *distractors]
    if not any(_answer_represents_multiple_values(option, answer_family) for option in options):
        return "Maths MCQ stem asks for multiple values, but no option presents a complete solution set."
    if not _answer_represents_multiple_values(correct_answer, answer_family):
        return "Maths MCQ stem asks for multiple values, but the marked correct answer gives only one value."
    return ""


def _curve_intersection_solution_values_from_stem(stem: str) -> list[Any]:
    if not _looks_like_curve_intersection_context(math_tex_to_plain(stem)):
        return []

    normalized = normalize_math_stem_text(stem)
    rhs_expressions = _curve_intersection_rhs_expressions_from_stem(normalized)
    if len(rhs_expressions) < 2:
        return []

    try:
        x_symbol = Symbol("x")
        left = _parse_sympy_expression(rhs_expressions[0])
        right = _parse_sympy_expression(rhs_expressions[1])
        return list(solve(left - right, x_symbol))
    except Exception:  # noqa: BLE001
        return []


def _curve_intersection_rhs_expressions_from_stem(stem: str) -> list[str]:
    normalized = normalize_math_stem_text(stem)
    rhs_expressions: list[str] = []
    for block in MATH_DELIMITED_BLOCK_RE.findall(normalized):
        body = block[2:-2].strip() if block.startswith((r"\(", r"\[")) else block
        if not re.search(r"\by\s*=", body):
            continue
        rhs = body.split("=", 1)[1].strip()
        if rhs:
            rhs_expressions.append(rhs)
        if len(rhs_expressions) >= 2:
            break
    return rhs_expressions


def _curve_intersection_points_from_stem(stem: str) -> list[tuple[Any, Any]]:
    if not _looks_like_curve_intersection_context(math_tex_to_plain(stem)):
        return []

    rhs_expressions = _curve_intersection_rhs_expressions_from_stem(stem)
    if len(rhs_expressions) < 2:
        return []

    try:
        x_symbol = Symbol("x")
        left = _parse_sympy_expression(rhs_expressions[0])
        right = _parse_sympy_expression(rhs_expressions[1])
        x_values = list(solve(left - right, x_symbol))
        return [(x_value, simplify(left.subs(x_symbol, x_value))) for x_value in x_values]
    except Exception:  # noqa: BLE001
        return []


def _answer_solution_values(answer: str) -> list[Any]:
    normalized = normalize_math_tex(answer, wrap_if_formula=True)
    body = normalized.replace(r"\(", "").replace(r"\)", "").replace(r"\[", "").replace(r"\]", "")
    body = re.sub(r"\\text\s*\{\s*(or|and)\s*\}", r" \1 ", body, flags=re.IGNORECASE)
    body = body.replace(r"\text", " ")

    if r"\pm" in body:
        expression = body.split("=", 1)[-1].strip() if "=" in body else body.strip()
        values = []
        for replacement in ("+", "-"):
            try:
                values.append(_parse_sympy_expression(expression.replace(r"\pm", replacement)))
            except Exception:  # noqa: BLE001
                return []
        return values

    body = re.sub(r"\bx\s*=", "", body)
    body = body.strip(" {}")
    body = re.sub(r"\b(?:or|and)\b", ",", body, flags=re.IGNORECASE)

    values = []
    for part in body.split(","):
        candidate = part.strip()
        if not candidate:
            continue
        try:
            values.append(_parse_sympy_expression(candidate))
        except Exception:  # noqa: BLE001
            return []
    return values


def _answer_coordinate_points(answer: str) -> list[tuple[Any, Any]]:
    normalized = normalize_math_tex(answer, wrap_if_formula=True)
    plain = math_tex_to_plain(normalized)
    snippets = [match.group(0) for match in COORDINATE_OR_INTERVAL_SNIPPET_RE.finditer(plain)]
    if not snippets:
        return []

    points: list[tuple[Any, Any]] = []
    for snippet in snippets:
        match = ORDERED_PAIR_RE.match(snippet.strip())
        if not match:
            return []
        left, right = match.groups()
        try:
            points.append((_parse_sympy_expression(left), _parse_sympy_expression(right)))
        except Exception:  # noqa: BLE001
            return []
    return points


def _solution_value_sets_equivalent(expected: list[Any], actual: list[Any]) -> bool:
    if not expected or len(expected) != len(actual):
        return False

    unmatched = list(actual)
    for expected_value in expected:
        matched_index = None
        for index, actual_value in enumerate(unmatched):
            try:
                if simplify(expected_value - actual_value) == 0:
                    matched_index = index
                    break
            except Exception:  # noqa: BLE001
                continue
        if matched_index is None:
            return False
        unmatched.pop(matched_index)
    return True


def _point_sets_equivalent(expected: list[tuple[Any, Any]], actual: list[tuple[Any, Any]]) -> bool:
    if not expected or len(expected) != len(actual):
        return False

    unmatched = list(actual)
    for expected_x, expected_y in expected:
        matched_index = None
        for index, (actual_x, actual_y) in enumerate(unmatched):
            try:
                same_x = simplify(expected_x - actual_x) == 0
                same_y = simplify(expected_y - actual_y) == 0
            except Exception:  # noqa: BLE001
                continue
            if same_x and same_y:
                matched_index = index
                break
        if matched_index is None:
            return False
        unmatched.pop(matched_index)
    return True


def _math_payload_curve_intersection_solution_error(
    *,
    stem: str,
    correct_answer: str,
    distractors: list[str],
    metadata: dict[str, Any],
) -> str:
    answer_family = str(metadata.get("answer_family", "") or "")
    if answer_family not in {"equation_solution", "coordinate"}:
        return ""
    return curve_intersection_question_integrity_error(
        stem=stem,
        correct_answer=correct_answer,
        distractors=distractors,
        answer_family=answer_family,
    )


def curve_intersection_question_integrity_error(
    *,
    stem: str,
    correct_answer: str,
    distractors: list[str],
    answer_family: str = "",
) -> str:
    normalized_stem = normalize_math_stem_text(stem)
    normalized_correct_answer = normalize_math_tex(correct_answer, wrap_if_formula=True)
    normalized_distractors = [normalize_math_tex(option, wrap_if_formula=True) for option in distractors]
    options = [normalized_correct_answer, *normalized_distractors]
    family = str(answer_family or "").strip()

    if family == "coordinate" or any(_answer_coordinate_points(option) for option in options):
        expected_points = _curve_intersection_points_from_stem(normalized_stem)
        if not expected_points:
            return ""
        matching_options = [
            option
            for option in options
            if _point_sets_equivalent(expected_points, _answer_coordinate_points(option))
        ]
        if not matching_options:
            return "Maths MCQ options do not contain the actual curve intersection solution set."
        if not _point_sets_equivalent(expected_points, _answer_coordinate_points(normalized_correct_answer)):
            return "Maths MCQ marked correct answer does not match the curve intersection solution set."
        return ""

    expected_values = _curve_intersection_solution_values_from_stem(normalized_stem)
    if not expected_values:
        return ""

    matching_options = [
        option
        for option in options
        if _solution_value_sets_equivalent(expected_values, _answer_solution_values(option))
    ]
    if not matching_options:
        return "Maths MCQ options do not contain the actual curve intersection solution set."
    if not _solution_value_sets_equivalent(expected_values, _answer_solution_values(normalized_correct_answer)):
        return "Maths MCQ marked correct answer does not match the curve intersection solution set."
    return ""


def validate_math_mcq_payload(
    payload: dict[str, Any],
    *,
    distractor_count: int,
    objective_text: str = "",
    chunk_text: str = "",
    explanation_text: str = "",
) -> dict[str, Any]:
    correct_answers = payload.get("correct_answers") or []
    if len(correct_answers) != 1:
        raise ValueError("Maths MCQ payload must contain exactly one correct answer.")

    distractors = [str(item).strip() for item in (payload.get("distractors") or []) if str(item).strip()]
    if len(distractors) != distractor_count:
        raise ValueError("Maths MCQ payload must contain the configured number of distractors.")

    metadata = payload.get("math_metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Maths MCQ payload must include math_metadata.")

    answer_family = str(metadata.get("answer_family", "") or "").strip()
    if answer_family not in MATH_ANSWER_FAMILIES:
        raise ValueError("Maths MCQ payload uses an unsupported answer family.")
    equivalence_mode = str(metadata.get("equivalence_mode", "") or "").strip().lower()
    if equivalence_mode not in MATH_EQUIVALENCE_MODES:
        raise ValueError("Maths MCQ payload uses an unsupported equivalence mode.")

    stem = normalize_math_stem_text(str(payload.get("stem", "")).strip())
    correct_answer = normalize_math_tex(str(correct_answers[0]).strip(), wrap_if_formula=True)
    normalized_distractors = [normalize_math_tex(option, wrap_if_formula=True) for option in distractors]
    canonical_tex = normalize_math_tex(str(metadata.get("canonical_tex", "")).strip(), wrap_if_formula=True)
    canonical_plain = _normalize_whitespace(str(metadata.get("canonical_plain", "")).strip()) or math_tex_to_plain(correct_answer)
    distractor_tags = [str(item).strip() for item in metadata.get("distractor_tags", []) if str(item).strip()]
    if len(distractor_tags) != distractor_count:
        raise ValueError("Maths MCQ payload must provide one distractor tag per distractor.")

    correct_plain = math_tex_to_plain(correct_answer)
    if answer_family == "antiderivative" and not re.search(r"\+\s*C\b", correct_plain):
        raise ValueError("Maths antiderivative MCQ must include + C in the correct answer.")
    if answer_family == "derivative" and re.search(r"\+\s*C\b", correct_plain):
        raise ValueError("Maths derivative MCQ must not include + C in the correct answer.")

    metadata_normalized = {
        "answer_family": answer_family,
        "canonical_tex": canonical_tex or correct_answer,
        "canonical_plain": canonical_plain,
        "equivalence_mode": equivalence_mode,
        "equivalence_variables": [
            str(item).strip()
            for item in metadata.get("equivalence_variables", [])
            if str(item).strip()
        ][:4],
        "notation_profile": str(metadata.get("notation_profile", "") or MATH_NOTATION_PROFILE).strip() or MATH_NOTATION_PROFILE,
        "distractor_tags": distractor_tags,
        "source_subtopic": _normalize_whitespace(str(metadata.get("source_subtopic", "")).strip()),
    }
    for key in ("generator_id", "generator_seed", "validation_report", "structured_generation"):
        if key in metadata:
            metadata_normalized[key] = metadata.get(key)

    if math_options_equivalent(correct_answer, metadata_normalized["canonical_tex"], metadata_normalized) is False:
        metadata_normalized["canonical_tex"] = correct_answer
        metadata_normalized["canonical_plain"] = math_tex_to_plain(correct_answer)

    option_family_labels = [_option_answer_family(correct_answer), *[_option_answer_family(option) for option in normalized_distractors]]
    if len(set(option_family_labels)) > 1:
        allowed = {"interval_or_coordinate"}
        if set(option_family_labels) != allowed:
            raise ValueError("Maths MCQ mixes incompatible option families.")

    for distractor in normalized_distractors:
        if math_options_equivalent(correct_answer, distractor, metadata_normalized):
            raise ValueError("Maths MCQ contains a distractor equivalent to the correct answer.")
    for index, distractor in enumerate(normalized_distractors):
        for other in normalized_distractors[index + 1 :]:
            if math_options_equivalent(distractor, other, metadata_normalized):
                raise ValueError("Maths MCQ contains duplicate-equivalent distractors.")

    authenticity_error = _math_payload_symbolic_authenticity_error(
        stem=stem,
        correct_answer=correct_answer,
        distractors=normalized_distractors,
        metadata=metadata_normalized,
        objective_text=objective_text,
        chunk_text=chunk_text,
    )
    if authenticity_error:
        raise ValueError(authenticity_error)
    curve_intersection_error = _math_payload_curve_intersection_solution_error(
        stem=stem,
        correct_answer=correct_answer,
        distractors=normalized_distractors,
        metadata=metadata_normalized,
    )
    if curve_intersection_error:
        raise ValueError(curve_intersection_error)
    cardinality_error = _math_payload_solution_cardinality_error(
        stem=stem,
        correct_answer=correct_answer,
        distractors=normalized_distractors,
        metadata=metadata_normalized,
    )
    if cardinality_error:
        raise ValueError(cardinality_error)
    explanation_alignment_issue = _explanation_conclusion_alignment_issue(
        explanation_text,
        correct_answer,
        normalized_distractors,
        metadata_normalized,
    )
    if explanation_alignment_issue:
        raise ValueError(explanation_alignment_issue)
    if explanation_text and MATH_EXPLANATION_OPTION_DISCLAIMER_RE.search(str(explanation_text)):
        raise ValueError("Maths MCQ explanation admits the answer options are broken.")

    return {
        "stem": stem,
        "correct_answer": correct_answer,
        "distractors": normalized_distractors,
        "math_metadata": metadata_normalized,
    }


def math_question_quality_issue(question) -> str:
    metadata = getattr(question, "math_metadata", None)
    if not isinstance(metadata, dict) or not metadata:
        return ""

    answer_family = str(metadata.get("answer_family", "") or "")
    stored_stem = str(getattr(question, "stem", "") or "")
    if normalize_math_stem_text(stored_stem) != stored_stem:
        return "Maths MCQ stem needs TeX normalization."
    correct_answer = str(getattr(question, "correct_answer", "") or "")
    distractors = [str(item or "") for item in getattr(question, "distractors", []) or []]
    if not correct_answer or not distractors:
        return "Maths MCQ is missing answer options."

    try:
        validate_math_mcq_payload(
            {
                "stem": stored_stem,
                "correct_answers": [correct_answer],
                "distractors": distractors,
                "math_metadata": metadata,
            },
            distractor_count=len(distractors),
            objective_text=str(getattr(getattr(question, "learning_objective", None), "text", "") or ""),
            explanation_text=str(getattr(question, "explanation", "") or ""),
        )
    except ValueError as exc:
        return str(exc)

    delimiter_counts = (
        str(getattr(question, "stem", "")).count(r"\(") == str(getattr(question, "stem", "")).count(r"\)")
        and str(getattr(question, "stem", "")).count(r"\[") == str(getattr(question, "stem", "")).count(r"\]")
    )
    if not delimiter_counts:
        return "Maths MCQ stem has malformed TeX delimiters."
    correct_plain = math_tex_to_plain(correct_answer)
    if answer_family == "antiderivative" and not re.search(r"\+\s*C\b", correct_plain):
        return "Maths antiderivative MCQ is missing + C."
    if answer_family == "derivative" and re.search(r"\+\s*C\b", correct_plain):
        return "Maths derivative MCQ incorrectly includes + C."
    return ""
