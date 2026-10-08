"""Transparent possible causes, without claiming a unique causal explanation."""
from .models import Dataset, Result
from .engine import eligible

def unmet_demands(data: Dataset, result: Result) -> list[dict[str, str]]:
    satisfied = {(c, s.subject) for s in result.sessions for c in s.children}
    assigned = {c for c, _ in satisfied}
    rows = []
    for d in data.demands:
        if (d.child, d.subject) in satisfied:
            continue
        c = data.children[d.child]
        skilled = [v for v in data.volunteers.values() if (d.subject, c.grade) in v.skills]
        permitted = [v for v in skilled if eligible(data, v.id, c.id, d.subject)]
        common = [v for v in permitted if v.days & c.days and v.max_sessions > 0]
        if not skilled:
            reason = "Không có TNV đăng ký đúng môn và lớp."
        elif not permitted:
            reason = "Các TNV phù hợp đều được đánh dấu Không ghép."
        elif not any(v.days & c.days for v in permitted):
            reason = "Không có ngày rảnh chung với TNV phù hợp."
        elif not common:
            reason = "TNV phù hợp có giới hạn số buổi bằng 0."
        elif all(sum(s.volunteer == v.id for s in result.sessions) >= v.max_sessions for v in common):
            reason = "Trong phương án hiện tại, các TNV phù hợp đều đã đạt giới hạn số buổi/tuần."
        else:
            reason = "Có ứng viên; có thể thiếu buổi, trùng lịch hoặc vướng lựa chọn khóa."
            if data.allow_group_sessions:
                reason += " Điều kiện lớp ghép cũng có thể giới hạn lựa chọn."
        policy = data.sites.get(c.site)
        if data.sites:
            reason = reason.replace("TNV", "người dạy")
        if policy and policy.require_academic_lead:
            reason += " Mái ấm này chỉ mở lớp vào ngày có BTC ACA IC trực tiếp dạy và làm lead."
        if common:
            if not result.optimal:
                reason += " Thời gian xếp đã hết; phương án có thể còn cải thiện."
        rows.append({"Mã bé": c.id, "Môn": d.subject, "Bé chưa có buổi": "Có" if c.id not in assigned else "Không", "Lý do có thể": reason})
    return rows
