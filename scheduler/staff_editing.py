"""Validate staff edits before changing the working dataset."""
from .models import CATALOG, DAYS, DataError, Volunteer, level

GRADE_BLOCKS = {1: range(1, 6), 2: range(6, 10), 3: range(10, 13)}
BLOCK_LABELS = {1: "Cấp 1 · Lớp 1–5", 2: "Cấp 2 · Lớp 6–9", 3: "Cấp 3 · Lớp 10–12"}


def skills_from_blocks(selected, previous=frozenset(), whole_blocks=False):
    """New subjects cover a block; existing grade restrictions survive routine edits."""
    skills = set()
    for block, subjects in selected.items():
        for subject in subjects:
            existing = {(s, g) for s, g in previous if s == subject and level(g) == block}
            skills.update(existing if existing and not whole_blocks else {(subject, g) for g in GRADE_BLOCKS[block]})
    return frozenset(skills)


def skills_summary(skills):
    blocks = []
    for block, grades in GRADE_BLOCKS.items():
        subjects = sorted({s for s, g in skills if g in grades})
        parts = []
        for subject in subjects:
            taught = {g for s, g in skills if s == subject and g in grades}
            suffix = "" if taught == set(grades) else " (lớp " + ", ".join(map(str, sorted(taught))) + ")"
            parts.append(subject + suffix)
        if parts:
            blocks.append(f"Cấp {block}: " + ", ".join(parts))
    return "; ".join(blocks)


def staff_member(identifier, kind, role, skills, days, max_sessions):
    identifier = identifier.strip()
    role = role.strip() if kind == "BTC" else ""
    if not identifier:
        raise DataError("Hãy nhập mã người dạy.")
    if kind not in ("TNV", "BTC"):
        raise DataError("Loại người dạy không hợp lệ.")
    if not skills or any(not 1 <= g <= 12 or s not in CATALOG[level(g)] for s, g in skills):
        raise DataError("Chọn ít nhất một môn và lớp có thể dạy.")
    if not set(days) <= set(DAYS):
        raise DataError("Ngày rảnh phải từ Thứ Hai đến Thứ Sáu.")
    academic = kind == "BTC" and role.casefold().replace("_", " ") == "aca ic"
    cap = 1 if academic else 2
    if not isinstance(max_sessions, int) or not 0 <= max_sessions <= cap:
        raise DataError(f"Giới hạn của người dạy này là {cap} buổi/tuần.")
    if max_sessions and not days:
        raise DataError("Chọn ngày rảnh hoặc đặt số buổi bằng 0 để tạm ngưng.")
    return Volunteer(identifier, frozenset(skills), frozenset(days), max_sessions, kind, role)


def remove_staff(data, identifier):
    """Remove a staff member and references that cannot survive deletion."""
    if identifier not in data.volunteers:
        raise DataError("Người dạy này không còn trong danh sách.")
    del data.volunteers[identifier]
    data.interviews.pop(identifier, None)
    data.ratings = {pair: rating for pair, rating in data.ratings.items() if pair[0] != identifier}
    data.locks = {lock for lock in data.locks if lock.volunteer != identifier}
    data.skill_exclusions = {rule for rule in data.skill_exclusions if rule[0] != identifier}
    data.international_teachers.discard(identifier)
    data.fixed_teachers = {key: vid for key,vid in data.fixed_teachers.items() if vid != identifier}
    data.specialist_teachers = {key: people-{identifier} for key,people in data.specialist_teachers.items() if people-{identifier}}
