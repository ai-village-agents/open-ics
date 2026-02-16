#!/usr/bin/env python3
"""Advisory privacy and safety lint for iCalendar (.ics) files.

This script is intentionally stdlib-only and designed to be *advisory*:

- It scans .ics files for potentially sensitive content in fields that
  commonly end up in public calendar feeds, such as LOCATION and
  DESCRIPTION.
- It prints human-readable findings but exits with code 0 unless there is
  an unexpected internal error (e.g., I/O failure), so it can be wired
  into CI as a non-blocking check.

The goal is not to perfectly classify every case, but to catch obvious
privacy foot-guns and nudge maintainers toward safer defaults.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,2}[\s\-.])?(?:\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})(?!\d)"
)

# Simple heuristic for "street-like" addresses. This will fire on both private
# homes and public venues; the lint message focuses on distribution/context.
STREET_SUFFIXES = [
    "ST",
    "STREET",
    "AVE",
    "AVENUE",
    "BLVD",
    "ROAD",
    "RD",
    "DR",
    "DRIVE",
    "LANE",
    "LN",
    "COURT",
    "CT",
    "WAY",
    "PLACE",
    "PL",
    "TERRACE",
    "TER",
    "PARKWAY",
    "PKWY",
]

ZOOM_RE = re.compile(r"zoom\.us", re.IGNORECASE)
MEET_RE = re.compile(r"meet\.google\.com", re.IGNORECASE)
TEAMS_RE = re.compile(r"teams\.microsoft\.com", re.IGNORECASE)


@dataclass
class Finding:
    file: str
    prop_name: str
    line_no: Optional[int]
    kind: str
    message: str
    snippet: str


def iter_ics_files(paths: List[str]) -> Iterable[str]:
    """Yield .ics file paths under the given paths (or current dir if empty)."""

    if not paths:
        paths = ["."]

    for p in paths:
        if os.path.isfile(p) and p.lower().endswith(".ics"):
            yield p
        elif os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for name in files:
                    if name.lower().endswith(".ics"):
                        yield os.path.join(root, name)


def unfold_ics_lines(lines: Iterable[str]) -> List[Tuple[str, int]]:
    """Return unfolded iCalendar property lines with approximate line numbers.

    iCalendar allows long content lines to be folded: a content line that
    is too long can be wrapped by inserting a CRLF immediately followed by
    a space or tab. Continuation lines start with a single space or tab.

    For linting we care about the full property value. This function
    reconstructs logical properties and tracks the starting line number of
    each property for reference in findings.
    """

    props: List[Tuple[str, int]] = []
    current: Optional[str] = None
    current_lineno: Optional[int] = None

    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        if line.startswith(" ") or line.startswith("\t"):
            # Continuation of previous line
            if current is not None:
                current += line[1:]
            else:
                # Malformed folding; treat as a new property
                current = line.lstrip()
                current_lineno = lineno
        else:
            if current is not None and current_lineno is not None:
                props.append((current, current_lineno))
            current = line
            current_lineno = lineno

    if current is not None and current_lineno is not None:
        props.append((current, current_lineno))

    return props


def analyze_property(
    file_path: str, prop: str, lineno: Optional[int]
) -> List[Finding]:
    findings: List[Finding] = []

    if not prop:
        return findings

    if ":" in prop:
        head, value = prop.split(":", 1)
    else:
        head, value = prop, ""

    # Extract the property name without parameters (e.g., LOCATION;LANG=en-US)
    prop_name = head.split(";", 1)[0].upper()

    # We focus on fields that are likely to be visible in public calendars or
    # that often carry contact info.
    interesting_props = {"LOCATION", "DESCRIPTION", "SUMMARY", "COMMENT", "ORGANIZER", "ATTENDEE", "CONTACT"}

    if prop_name not in interesting_props:
        return findings

    trimmed_value = value.strip()
    if not trimmed_value:
        return findings

    # Basic email detection
    emails = EMAIL_RE.findall(trimmed_value)
    if emails:
        # We do not attempt to distinguish role accounts from personal
        # addresses. The message invites maintainers to double-check.
        findings.append(
            Finding(
                file=file_path,
                prop_name=prop_name,
                line_no=lineno,
                kind="email",
                message=(
                    "Email address found in %s. For public .ics feeds, consider "
                    "using a role-based or generic contact (e.g., events@group.org) "
                    "and avoid publishing personal inboxes." % prop_name
                ),
                snippet=trimmed_value[:200],
            )
        )

    # Phone number detection (North America-like formats)
    phones = PHONE_RE.findall(trimmed_value)
    if phones:
        findings.append(
            Finding(
                file=file_path,
                prop_name=prop_name,
                line_no=lineno,
                kind="phone",
                message=(
                    "Phone-like number found in %s. Consider whether this should "
                    "live in a private invite or sign-up flow instead of a public "
                    "calendar feed." % prop_name
                ),
                snippet=trimmed_value[:200],
            )
        )

    # Simple street-address heuristic
    upper_val = trimmed_value.upper()
    if re.search(r"\b\d{1,5}\b", upper_val):
        for suffix in STREET_SUFFIXES:
            if f" {suffix} " in f" {upper_val} ":
                findings.append(
                    Finding(
                        file=file_path,
                        prop_name=prop_name,
                        line_no=lineno,
                        kind="address",
                        message=(
                            "Specific street-like address detected. If this is a "
                            "private home or sensitive location, prefer an "
                            "approximate description or non-public calendar, and "
                            "only share precise details with trusted attendees."
                        ),
                        snippet=trimmed_value[:200],
                    )
                )
                break

    # Video-conference / meeting links
    if ZOOM_RE.search(trimmed_value) or MEET_RE.search(trimmed_value) or TEAMS_RE.search(trimmed_value):
        findings.append(
            Finding(
                file=file_path,
                prop_name=prop_name,
                line_no=lineno,
                kind="meeting-link",
                message=(
                    "Potential meeting join link detected. Remember that .ics files "
                    "are easy to forward and may be archived in public repos; "
                    "consider linking to an access-controlled page instead of "
                    "embedding full join details in DESCRIPTION or LOCATION."
                ),
                snippet=trimmed_value[:200],
            )
        )

    return findings


def lint_file(path: str) -> List[Finding]:
    findings: List[Finding] = []

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[ics-privacy-lint] ERROR: failed to read {path}: {e}", file=sys.stderr)
        # I/O failures are considered internal errors; the caller may choose how
        # to handle them. We do not raise here to allow processing of other files.
        return findings

    props = unfold_ics_lines(lines)
    for prop, lineno in props:
        findings.extend(analyze_property(path, prop, lineno))

    return findings


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Advisory privacy/safety lint for .ics files. Scans for email "
            "addresses, phone-like numbers, precise street addresses, and "
            "common meeting links in human-visible fields. Always exits 0 "
            "unless a fatal internal error occurs."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to scan. If omitted, scans the current directory.",
    )
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help=(
            "Exit with code 2 if any findings are reported. Intended for local "
            "use; CI configurations are encouraged to keep this advisory-only "
            "(e.g., by appending '|| true')."
        ),
    )

    args = parser.parse_args(argv)

    all_files = sorted(set(iter_ics_files(args.paths)))
    if not all_files:
        print("[ics-privacy-lint] No .ics files found to scan.")
        return 0

    all_findings: List[Finding] = []

    for path in all_files:
        file_findings = lint_file(path)
        if not file_findings:
            continue
        all_findings.extend(file_findings)

    if all_findings:
        print("[ics-privacy-lint] Advisory findings:")
        for f in all_findings:
            loc = f"{f.file}"
            if f.line_no is not None:
                loc += f":{f.line_no}"
            print("-")
            print(f"  File      : {loc}")
            print(f"  Property  : {f.prop_name}")
            print(f"  Kind      : {f.kind}")
            print(f"  Message   : {f.message}")
            print(f"  Snippet   : {f.snippet!r}")
        print()
        print(
            f"[ics-privacy-lint] Checked {len(all_files)} .ics file(s); "
            f"reported {len(all_findings)} advisory finding(s)."
        )
    else:
        print(
            f"[ics-privacy-lint] Checked {len(all_files)} .ics file(s); "
            "no advisory findings."
        )

    if args.strict_exit and all_findings:
        return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("[ics-privacy-lint] Interrupted by user.", file=sys.stderr)
        raise SystemExit(1)
