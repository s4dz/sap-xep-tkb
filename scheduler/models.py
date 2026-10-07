"""Typed domain objects, independent from the user interface."""
from dataclasses import dataclass, field

DAYS = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu")
CATALOG = {
    1: {"Toán", "Tiếng Việt", "Tiếng Anh"},
    2: {"Toán", "Ngữ văn", "Tiếng Anh", "Khoa học tự nhiên"},
    3: {"Toán", "Ngữ văn", "Tiếng Anh"},
}

def level(grade: int) -> int:
    return 1 if grade <= 5 else 2 if grade <= 9 else 3

@dataclass(frozen=True)
class Volunteer:
    id: str
    skills: frozenset[tuple[str, int]]
    days: frozenset[str]
    max_sessions: int = 1

@dataclass(frozen=True)
class Child:
    id: str
    age: int
    grade: int
    days: frozenset[str]

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

@dataclass
class Result:
    sessions: list[Session]
    optimal: bool
    objectives: list[int]

class DataError(ValueError):
    """Input or locked decisions violate a hard constraint."""
