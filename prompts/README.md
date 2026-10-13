# Prompt Management & Governance

This directory contains version-controlled, production-grade Jinja2 prompt templates for the Remote 150K+ DS/AI/ML Job Search Platform.

## Directory Layout
- `system/`: System prompts enforcing role identity, classification taxonomy, and strict JSON output formats.
- `user/`: User turn templates standardizing document payload formatting and context bounding.
- `registry.yaml`: Metadata manifest tracking active prompt versions, input parameters, temperature settings, and schema contracts.

## Template Standards
1. **Jinja2 Templating**: All prompts use standard Jinja2 syntax (`{{ variable }}`).
2. **Defensive Formatting**: Use triple-quotes (`"""`) to wrap unstructured job description inputs to prevent prompt injection.
3. **Deterministic Output**: LLM tasks requiring data transformation should specify temperature $\le 0.2$ and explicit JSON schemas.
4. **Versioning**: Never modify existing released templates in place (e.g., `_v1`). Create new versions (`_v2`) and update `registry.yaml`.
5. **Regression Testing**: All prompt changes must pass the regression suite under `evals/prompt_regression.py`.
