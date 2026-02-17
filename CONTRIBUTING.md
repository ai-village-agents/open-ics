# Contributing to open-ics

Welcome to the calendar standardization library. We're excited to collaborate on privacy-minded, community-safe ICS tooling.

## Core Principles
- **Evidence**: Base changes on reproducible behaviors and transparent reasoning, especially when adjusting validation rules.
- **Privacy**: Default to minimizing sensitive data exposure in `.ics` files and supporting redaction-first workflows.
- **Non-Carceral**: Do not use this project to build punitive, surveillance, or enforcement tooling.
- **Safety**: Prioritize user safety in features, documentation, and examples; flag risky patterns early.

## How to Contribute
- **Focus**: Python development is the primary path for code contributions.
- **Setup**: Install in editable mode with `pip install -e .` (a `[dev]` extra is not required in this repo).
- **Testing**: Run the test suite with `pytest` from the repository root before sending changes.
- **Workflow**: Create a feature branch, open a pull request, and include context on motivation and testing.

## Style Guide
- Follow PEP 8.
- Use type hints where practical to make intent explicit.

## Code of Conduct
By participating, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). If you observe or experience a violation, please report it to the maintainers.
