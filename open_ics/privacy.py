from __future__ import annotations
from dataclasses import dataclass
from typing import List
import re
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,2}[\s\-.])?(?:\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})(?!\d)")
STREET_HINT = re.compile(r"\b\d{1,5}\s+\w+[\w\-']*\s+(?:ST|STREET|AVE|AVENUE|BLVD|ROAD|RD|DR|DRIVE|LANE|LN|COURT|CT|WAY|PLACE|PL|TERRACE|TER|PARKWAY|PKWY)\b", re.IGNORECASE)
MEETING_DOMAINS = re.compile(r"(zoom\.us|meet\.google\.com|teams\.microsoft\.com)", re.IGNORECASE)
@dataclass
class PrivacyFinding:
    kind: str
    message: str
    snippet: str
INTERESTING = {"LOCATION", "DESCRIPTION", "SUMMARY", "COMMENT", "ORGANIZER", "ATTENDEE", "CONTACT"}

def privacy_findings(ics_text: str) -> List[PrivacyFinding]:
    findings: List[PrivacyFinding] = []
    for raw in ics_text.splitlines():
        if ':' not in raw:
            continue
        head, value = raw.split(':', 1)
        prop = head.split(';', 1)[0].upper()
        if prop not in INTERESTING:
            continue
        val = value.strip()
        if not val:
            continue
        if EMAIL_RE.search(val):
            findings.append(PrivacyFinding('email', f'Email address detected in {prop}; consider a role account or web form for public feeds.', val[:200]))
        if PHONE_RE.search(val):
            findings.append(PrivacyFinding('phone', f'Phone-like number detected in {prop}; consider if it belongs in a private flow.', val[:200]))
        if STREET_HINT.search(val):
            findings.append(PrivacyFinding('address', f'Street-like address in {prop}; ensure consent and context are appropriate.', val[:200]))
        if MEETING_DOMAINS.search(val):
            findings.append(PrivacyFinding('meeting', f'Potential meeting URL in {prop}; treat join links as sensitive.', val[:200]))
    return findings
