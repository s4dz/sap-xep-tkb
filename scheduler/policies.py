"""Shared hard rules for site separation, child pairs and academic leads."""
from .models import DAYS, Dataset, Session

def teaching_skills(data: Dataset, volunteer: str) -> frozenset[tuple[str,int]]:
    """Apply explicitly enabled chemistry-to-science flexibility at the same grade."""
    skills=set(data.volunteers[volunteer].skills)
    if data.flexible_science:
        for subject,grade in list(skills):
            if subject=='Hóa học' and grade>=6:
                skills.update((s,grade) for s in ('Vật lý','Hóa học','Sinh học'))
                if grade<=9:skills.add(('Khoa học tự nhiên',grade))
    return frozenset((subject, grade) for subject, grade in skills
                     if (volunteer, subject, grade) not in data.skill_exclusions)

def can_pair(data: Dataset, a: str, b: str) -> bool:
    """Unknown ages never imply equal ages; same-grade proxy must be explicit."""
    first, second = data.children[a], data.children[b]
    if first.site != second.site or frozenset((a, b)) in data.conflicts:
        return False
    if first.site in data.sites:
        policy = data.sites[first.site]
        if not policy.allow_primary_pairs or first.grade > 5 or second.grade > 5:
            return False
        if policy.pair_by_grade:
            return first.grade == second.grade
    elif not data.allow_group_sessions:
        return False
    return first.age is not None and first.age == second.age

def is_academic_lead(data: Dataset, volunteer: str) -> bool:
    person = data.volunteers[volunteer]
    return person.kind == "BTC" and person.role.casefold().replace("_", " ").strip() == "aca ic"


def can_lead(data: Dataset, volunteer: str) -> bool:
    return is_academic_lead(data, volunteer) and data.volunteers[volunteer].can_lead


def lead_ids(result, site: str, day: str) -> tuple[str, ...]:
    value = result.leads.get((site, day), ())
    return (value,) if isinstance(value, str) else tuple(value)


def lead_rows(result):
    return [(site, day, vid) for site, day in result.leads for vid in lead_ids(result, site, day)]

def session_site(data: Dataset, session: Session) -> str:
    return data.children[session.children[0]].site

def pick_leads(data: Dataset, sessions: list[Session]) -> dict[tuple[str, str], str]:
    """Choose exactly one teaching ACA IC as lead per active required site/day."""
    groups: dict[tuple[str, str], list[str]] = {}
    for session in sessions:
        site = session_site(data, session)
        if site in data.sites and data.sites[site].require_academic_lead and can_lead(data, session.volunteer):
            groups.setdefault((site, session.day), []).append(session.volunteer)
    return {key: sorted(groups[key])[0] for key in sorted(groups, key=lambda key: (key[0], DAYS.index(key[1])))}
