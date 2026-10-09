"""Typed domain objects, independent from the user interface."""
from dataclasses import dataclass, field

DAYS = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu")
CATALOG = {
    1: {"Toán", "Tiếng Việt", "Tiếng Anh", "Lịch sử", "Khoa học"},
    2: {"Toán", "Ngữ văn", "Tiếng Anh", "Khoa học tự nhiên", "Vật lý", "Hóa học", "Sinh học"},
    3: {"Toán", "Ngữ văn", "Tiếng Anh", "Vật lý", "Hóa học", "Sinh học"},
}

def level(grade: int) -> int:
    return 1 if grade <= 5 else 2 if grade <= 9 else 3

@dataclass(frozen=True)
class Volunteer:
    id: str
    skills: frozenset[tuple[str, int]]
    days: frozenset[str]
    max_sessions: int = 1
    kind: str = "TNV"
    role: str = ""

@dataclass(frozen=True)
class Child:
    id: str
    age: int | None
    grade: int
    days: frozenset[str]
    site: str = ""
    source_id: str = ""

@dataclass(frozen=True)
class SitePolicy:
    """Site-specific grouping and academic lead requirements."""
    allow_primary_pairs: bool = False
    require_academic_lead: bool = False
    pair_by_grade: bool = False
    required_days: frozenset[str] = frozenset()
    lead_must_teach: bool = True

@dataclass(frozen=True)
class Demand:
    child: str
    subject: str

@dataclass(frozen=True)
class Lock:
    volunteer: str
    child: str
    subject: str
    day: str

@dataclass(frozen=True)
class Session:
    volunteer: str
    subject: str
    day: str
    children: tuple[str, ...]

@dataclass
class Dataset:
    volunteers: dict[str, Volunteer]
    children: dict[str, Child]
    demands: list[Demand]
    conflicts: set[frozenset[str]] = field(default_factory=set)
    ratings: dict[tuple[str, str], str] = field(default_factory=dict)
    locks: set[Lock] = field(default_factory=set)
    insights: dict[str, str] = field(default_factory=dict)
    interviews: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    allow_group_sessions: bool = True
    sites: dict[str, SitePolicy] = field(default_factory=dict)
    prioritize_volunteers: bool = False
    flexible_science: bool = False
    prioritize_other_btc: bool = False
    prefer_pairs: bool = False

@dataclass
class Result:
    sessions: list[Session]
    optimal: bool
    objectives: list[int]
    leads: dict[tuple[str, str], str] = field(default_factory=dict)

class DataError(ValueError):
    """Input or locked decisions violate a hard constraint."""
