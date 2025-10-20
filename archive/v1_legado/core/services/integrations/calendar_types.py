from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GoogleAttendee:
    email: str
    display_name: Optional[str] = None
    optional: bool = False


@dataclass
class GoogleEvent:
    summary: str
    description: str
    start_iso: str  # ISO-8601 com TZ
    end_iso: str  # ISO-8601 com TZ
    location: Optional[str]
    attendees: List[GoogleAttendee]
    conference: bool = True  # criar Meet quando integrarmos "de verdade"
