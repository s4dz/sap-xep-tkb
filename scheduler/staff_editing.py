"""Validate staff edits before changing the working dataset."""
from .models import CATALOG, DAYS, DataError, Volunteer, level


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
