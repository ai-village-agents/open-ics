from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import re
from datetime import datetime, timezone

@dataclass
class Diagnostic:
    level: str
    message: str
    context: Optional[str] = None

@dataclass
class FileReport:
    file: str
    errors: List[Diagnostic]
    warnings: List[Diagnostic]

BEGIN = re.compile(r'^BEGIN:(?P<name>[A-Z0-9-]+)$')
END = re.compile(r'^END:(?P<name>[A-Z0-9-]+)$')
PROP = re.compile(r'^(?P<head>[A-Z0-9-]+(?:;[^:]+)?):(?P<value>.*)$')

def _unfold(lines: List[str]) -> List[Tuple[str, int]]:
    props: List[Tuple[str, int]] = []
    cur: Optional[str] = None
    cur_lineno: Optional[int] = None
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip('\r\n')
        if line.startswith(' ') or line.startswith('\t'):
            if cur is None:
                cur = line.lstrip()
                cur_lineno = i
            else:
                cur += line[1:]
        else:
            if cur is not None and cur_lineno is not None:
                props.append((cur, cur_lineno))
            cur = line
            cur_lineno = i
    if cur is not None and cur_lineno is not None:
        props.append((cur, cur_lineno))
    return props

def _parse_dt(s: str) -> Optional[datetime]:
    try:
        if s.endswith('Z') and len(s) == 16:
            return datetime.strptime(s, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        if len(s) == 8:
            return datetime.strptime(s, '%Y%m%d')
        if 'T' in s and len(s) in (15, 17):
            return datetime.strptime(s.rstrip('Z'), '%Y%m%dT%H%M%S')
    except Exception:
        return None
    return None

def validate_ics_text(text: str, file_label: str = '<memory>') -> FileReport:
    errors: List[Diagnostic] = []
    warnings: List[Diagnostic] = []
    unfolded = _unfold(text.splitlines())
    in_vcal = False
    vcal_depth = 0
    vevents: List[Dict[str, List[Tuple[str, str]]]] = []
    cur_event: Optional[Dict[str, List[Tuple[str, str]]]] = None
    have_version = False
    have_prodid = False
    for line, _lineno in unfolded:
        m_begin = BEGIN.match(line)
        m_end = END.match(line)
        if m_begin:
            name = m_begin.group('name').upper()
            if name == 'VCALENDAR':
                in_vcal = True
                vcal_depth += 1
            elif name == 'VEVENT':
                if not in_vcal:
                    errors.append(Diagnostic('error', 'VEVENT outside VCALENDAR'))
                cur_event = {}
            continue
        if m_end:
            name = m_end.group('name').upper()
            if name == 'VCALENDAR':
                vcal_depth = max(0, vcal_depth - 1)
                if vcal_depth == 0:
                    in_vcal = False
            elif name == 'VEVENT':
                if cur_event is not None:
                    vevents.append(cur_event)
                cur_event = None
            continue
        pm = PROP.match(line)
        if pm:
            head = pm.group('head')
            value = pm.group('value')
            prop_name = head.split(';', 1)[0].upper()
            if prop_name == 'VERSION':
                have_version = True
            elif prop_name == 'PRODID':
                have_prodid = True
            if cur_event is not None:
                cur_event.setdefault(prop_name, []).append((head, value))
    if not have_version:
        warnings.append(Diagnostic('warning', 'Missing VERSION on VCALENDAR'))
    if not have_prodid:
        warnings.append(Diagnostic('warning', 'Missing PRODID on VCALENDAR'))
    if not vevents:
        errors.append(Diagnostic('error', 'No VEVENT found'))
        return FileReport(file=file_label, errors=errors, warnings=warnings)
    uids: List[str] = []
    for idx, ev in enumerate(vevents, start=1):
        label = f'VEVENT[{idx}]'
        def first(name: str) -> Optional[Tuple[str, str]]:
            arr = ev.get(name.upper())
            return arr[0] if arr else None
        for rq in ['UID', 'DTSTAMP', 'DTSTART']:
            if rq not in ev:
                errors.append(Diagnostic('error', f'{label}: Missing required property {rq}'))
        if 'SUMMARY' not in ev or not (ev.get('SUMMARY')[0][1].strip()):
            errors.append(Diagnostic('error', f'{label}: SUMMARY is required and must be non-empty'))
        if 'DTEND' not in ev and 'DURATION' not in ev:
            errors.append(Diagnostic('error', f'{label}: Must include DTEND or DURATION'))
        uid = (first('UID')[1] if first('UID') else None)
        if uid:
            if uid in uids:
                errors.append(Diagnostic('error', f'{label}: Duplicate UID {uid!r}'))
            uids.append(uid)
        dtstart = first('DTSTART')
        dtend = first('DTEND')
        if dtstart and dtend:
            val_start = dtstart[1]
            val_end = dtend[1]
            ds = _parse_dt(val_start)
            de = _parse_dt(val_end)
            if ds and de and (de.tzinfo is None) == (ds.tzinfo is None):
                if de <= ds:
                    errors.append(Diagnostic('error', f'{label}: DTEND must be after DTSTART'))
            head_start = dtstart[0]
            head_end = dtend[0]
            if ('TZID=' not in head_start and not val_start.endswith('Z')) or ('TZID=' not in head_end and not val_end.endswith('Z')):
                warnings.append(Diagnostic('warning', f'{label}: DTSTART/DTEND appear to be floating times (no TZID, no Z)'))
    return FileReport(file=file_label, errors=errors, warnings=warnings)
