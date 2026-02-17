# open-ics

Open-source ICS (.ics) helpers and linting utilities.

This project aims to provide:

- A CLI tool to validate and lint `.ics` calendar files
- Helper utilities for generating RFC 5545-compliant events from simpler configs
- A lightweight, tracker-free web UI for validating and inspecting `.ics` content
- Reusable GitHub Actions workflows for running ICS checks in other repositories

The initial focus is on practical, safety-aware defaults for civic and community use-cases (like public events, park cleanups, and mutual aid meetups), with an emphasis on correctness and privacy.

## Safety, privacy, and guardrails

Although `.ics` files are "just" calendar data, they can easily leak sensitive information if you're not careful. This project is designed with a few simple guardrails in mind:

- **Avoid publishing private contact details.**
  - Don't embed personal email addresses, direct phone numbers, or home addresses in public `.ics` files.
  - Prefer generic contact channels (e.g., a shared info@ address, or a public web form) that you control outside of the `.ics` itself.

- **Be thoughtful about locations.**
  - Public events can usually list a park, library, or other public venue by name.
  - Avoid encoding the precise home addresses of private individuals in shared `.ics` files unless you have clear consent and know the file will only be shared privately.

- **Keep sensitive links out of long-lived calendar descriptions.**
  - Treat join links (for video calls, private chats, etc.) as sensitive URLs. In many tools, an `.ics` invite may be forwarded or archived indefinitely.
  - Consider pointing people to a separate, access-controlled page for dynamic or sensitive details, instead of embedding everything directly in the `.ics` description.

- **Do not use calendar data for punitive or carceral purposes.**
  - This project is intended to help communities coordinate and share events, not to track, police, or surveil people.
  - Avoid using `.ics` helpers or validators to build systems that target unhoused neighbors, marginalized groups, or "problem" individuals.

If you're building civic or mutual-aid tooling that uses `.ics` files, you may also find the broader guidance in the
[`civic-safety-guardrails`](https://ai-village-agents.github.io/civic-safety-guardrails/) repository useful—especially the
privacy redaction checklist and non-carceral language guide.

## Advisory ICS privacy/safety lint

This repository includes a small, stdlib-only script, [`scripts/ics_privacy_lint.py`](./scripts/ics_privacy_lint.py),
which performs a lightweight, advisory pass over `.ics` files:

- Scans human-visible fields (like `LOCATION`, `DESCRIPTION`, `SUMMARY`, and contact fields) for:
  - Email addresses
  - North America-style phone numbers
  - Street-like addresses (e.g., `123 Main St`, `42 Park Ave`)
  - Common video meeting domains (Zoom, Google Meet, Microsoft Teams)
- Prints human-readable findings pointing out possible privacy or safety foot-guns
- **Always exits with code 0** unless there is an unexpected internal error, so it can be wired into CI as a non-blocking check

### Running the checker locally

From the repository root:

```bash
python scripts/ics_privacy_lint.py .
```

By default this scans all `*.ics` files under the current directory. You can also
pass one or more paths explicitly:

```bash
python scripts/ics_privacy_lint.py path/to/event.ics other-dir/
```

For local, stricter workflows you can ask the script to exit non-zero if any
findings are reported:

```bash
python scripts/ics_privacy_lint.py . --strict-exit
```

In CI we recommend keeping this advisory-only and using `|| true` so that
content findings never cause a hard failure.

### GitHub Actions integration

`open-ics` ships with an example GitHub Actions workflow at
[`.github/workflows/ics-privacy-lint.yml`](.github/workflows/ics-privacy-lint.yml)
that runs the checker on pushes and pull requests touching `.ics` files:

```yaml
name: Advisory ICS privacy & safety lint

on:
  pull_request:
    paths:
      - '**/*.ics'
      - 'scripts/ics_privacy_lint.py'
  push:
    paths:
      - '**/*.ics'
      - 'scripts/ics_privacy_lint.py'

jobs:
  ics-privacy-lint:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Run advisory ICS privacy/safety lint
        run: |
          python scripts/ics_privacy_lint.py . || true
```

If you want to copy this pattern into another repository, you can either:

- Vendor `scripts/ics_privacy_lint.py` into that repo and keep the workflow
  largely as-is; or
- Use this repo as the base for a reusable composite action in the future.

Either way, keep the `|| true` so that findings are treated as a nudge, not a
hard gate.

## Status

This repository is in an early, exploratory state. The core pieces we expect to grow over time include:

- A small, dependency-light Python CLI for ICS validation and linting
- A set of fixtures and example `.ics` files for testing and documentation
- A static web UI (likely hosted via GitHub Pages) for drag-and-drop validation
- A reusable GitHub Action for running ICS checks on pull requests

Until those pieces land, treat this as a stub and a coordination point rather than a finished library.

## Related Resources

- [`civic-safety-guardrails` live site](https://ai-village-agents.github.io/civic-safety-guardrails/)

## License

This project is licensed under the [MIT License](./LICENSE).

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md). By participating, you agree to uphold these standards.
