from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List
from .validator import validate_ics_text
from .privacy import privacy_findings
from . import __version__

def cmd_validate(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog='open-ics validate', description='Validate iCalendar (.ics) files')
    p.add_argument('paths', nargs='*', help='Files or directories to scan (defaults to current directory)')
    p.add_argument('--json', action='store_true', help='Output JSON diagnostics')
    args = p.parse_args(argv)
    files: List[Path] = []
    if not args.paths:
        args.paths = ['.']
    for pth in args.paths:
        pth = Path(pth)
        if pth.is_file() and pth.suffix.lower() == '.ics':
            files.append(pth)
        elif pth.is_dir():
            files.extend(p for p in pth.rglob('*.ics'))
    all_reports = []
    total_errors = 0
    total_warnings = 0
    for fp in sorted({f.resolve() for f in files}):
        text = fp.read_text(encoding='utf-8', errors='replace')
        rep = validate_ics_text(text, file_label=str(fp))
        total_errors += len(rep.errors)
        total_warnings += len(rep.warnings)
        priv = privacy_findings(text)
        report_obj = {
            'file': rep.file,
            'errors': [d.__dict__ for d in rep.errors],
            'warnings': [d.__dict__ for d in rep.warnings],
            'privacy_findings': [f.__dict__ for f in priv],
        }
        all_reports.append(report_obj)
    if args.json:
        print(json.dumps(all_reports, indent=2))
    else:
        if not all_reports:
            print('No .ics files found', file=sys.stderr)
        for r in all_reports:
            print(f"== {r['file']}")
            for e in r['errors']:
                print(f"  [ERROR] {e['message']}")
            for w in r['warnings']:
                print(f"  [WARN]  {w['message']}")
            for f in r['privacy_findings']:
                print(f"  [PRIV]  {f['kind']}: {f['message']}")
    if total_errors > 0:
        return 2
    if total_warnings > 0:
        return 1
    return 0

def cmd_generate(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog='open-ics generate', description='Generate .ics from YAML spec')
    p.add_argument('--yaml', required=True, help='Path to YAML file')
    p.add_argument('--out', help='Output .ics path (defaults to stdout)')
    args = p.parse_args(argv)
    from .generator import generate_from_yaml_str
    ypath = Path(args.yaml)
    ytext = ypath.read_text(encoding='utf-8')
    ics = generate_from_yaml_str(ytext)
    if args.out:
        Path(args.out).write_text(ics, encoding='utf-8')
    else:
        sys.stdout.write(ics)
    return 0

def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help'):
        print('Open ICS', __version__)
        print('Usage: open-ics <command> [options]')
        print('Commands:')
        print('  validate   Validate .ics files (exit codes: 0 ok, 1 warnings, 2 errors)')
        print('  generate   Generate .ics from YAML spec')
        return 0
    cmd = argv.pop(0)
    if cmd == 'validate':
        return cmd_validate(argv)
    if cmd == 'generate':
        return cmd_generate(argv)
    print(f'Unknown command: {cmd}', file=sys.stderr)
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
