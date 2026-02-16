from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid
import yaml

@dataclass
class EventSpec:
    summary: str
    start: str
    end: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    uid: Optional[str] = None
    prodid: str = '-//AI Village Agents//Open ICS 0.1.1//EN'


def _fold(line: str, limit: int = 75) -> str:
    if len(line) <= limit:
        return line
    out = []
    while len(line) > limit:
        out.append(line[:limit])
        line = ' ' + line[limit:]
    out.append(line)
    return '\r\n'.join(out)


def generate_from_yaml_str(yaml_text: str) -> str:
    data = yaml.safe_load(yaml_text) or {}
    ev = EventSpec(
        summary=str(data.get('summary', '') or '').strip(),
        start=str(data.get('start', '') or '').strip(),
        end=(str(data.get('end')).strip() if data.get('end') is not None else None),
        duration=(str(data.get('duration')).strip() if data.get('duration') is not None else None),
        location=(str(data.get('location')).strip() if data.get('location') is not None else None),
        description=(str(data.get('description')).strip() if data.get('description') is not None else None),
        url=(str(data.get('url')).strip() if data.get('url') is not None else None),
        uid=(str(data.get('uid')).strip() if data.get('uid') is not None else None),
        prodid=str(data.get('prodid') or '-//AI Village Agents//Open ICS 0.1.1//EN'),
    )

    if not ev.summary:
        raise ValueError('summary is required')
    if not ev.start:
        raise ValueError('start is required (e.g., 20260214T170000Z)')
    if not (ev.end or ev.duration):
        raise ValueError('must provide end or duration')

    now = datetime.now(timezone.utc)
    uid = ev.uid or f"{uuid.uuid4()}@open-ics"

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:{ev.prodid}',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}',
        f'DTSTART:{ev.start}',
    ]

    if ev.end:
        lines.append(f'DTEND:{ev.end}')
    if ev.duration and not ev.end:
        lines.append(f'DURATION:{ev.duration}')
    if ev.summary:
        lines.append(_fold(f'SUMMARY:{ev.summary}'))
    if ev.description:
        lines.append(_fold(f'DESCRIPTION:{ev.description}'))
    if ev.location:
        lines.append(_fold(f'LOCATION:{ev.location}'))
    if ev.url:
        lines.append(_fold(f'URL:{ev.url}'))

    lines += ['END:VEVENT', 'END:VCALENDAR']

    return '\r\n'.join(lines) + '\r\n'
