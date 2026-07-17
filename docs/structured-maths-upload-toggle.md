# Structured Maths Upload Toggle

## Why this exists

Direct LLM-written maths questions are too fragile for symbolic topics. Algebraic equivalence, multi-root answers, distractors, and worked solutions need code-based validation. The structured maths path keeps AI out of the role of mathematical source of truth and routes supported maths objectives through deterministic generators validated with SymPy-aware checks.

## Rollout scope

This system is currently opt-in per PDF upload through `CourseImport.use_structured_maths_generation`.

- Default: off
- Scope: only the PDF import flow
- Non-maths uploads: unchanged
- Physics numerical generation: unchanged
- Existing imports: unchanged

## What the toggle changes

When a teacher enables the upload-time toggle and the imported content is maths-targeted:

1. Chapter ingest still creates blocks and learning objectives as normal.
2. Maths objectives are mapped to `MathsGeneratorSpec` records.
3. Each spec is validated against the local archetype registry.
4. Only `validated` specs can generate live maths questions.
5. Unsupported objectives are marked `unsupported` and blocked safely.
6. The legacy fragile maths fallback is not used for those opted-in maths blocks.

When the toggle is off, the existing upload and question-generation behaviour stays in place.

## Supported archetypes

- `linear_equation_one_variable`
- `expand_single_bracket`
- `expand_double_bracket`
- `factorise_quadratic_monic`
- `solve_quadratic_factorisable`
- `simultaneous_linear_equations`
- `simplify_indices`
- `differentiate_polynomial`
- `integrate_polynomial`
- `equation_of_straight_line`
- `arithmetic_sequence_nth_term`

## Adding a new archetype

1. Add an objective-to-archetype matcher in [structured_maths.py](/home/freddie/bioboost_v2/standalone/services/structured_maths.py).
2. Add a deterministic generator to `GENERATOR_REGISTRY`.
3. Generate backwards from a clean answer structure where possible.
4. Return a payload that passes `validate_math_mcq_payload`.
5. Add tests covering many seeds and reproducibility.

## Validation model

Structured maths generators validate that:

- exactly one correct option exists
- options are unique
- distractors are not equivalent to the answer
- the answer family matches the question type
- symbolic answers pass local maths validation before persistence

## Failure handling

Failed or unsupported objectives are not silently downgraded to the old maths path for opted-in uploads. Instead the system logs the reason and raises a safe generation error so the issue is visible and reviewable.
