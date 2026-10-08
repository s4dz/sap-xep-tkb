"""CP-SAT scheduling with sequential (lexicographic) objectives."""
from itertools import combinations
from time import monotonic
from ortools.sat.python import cp_model
from .models import DAYS, Dataset, DataError, Lock, Result, Session
from .policies import can_pair, is_academic_lead, pick_leads, session_site

def eligible(data: Dataset, volunteer: str, child: str, subject: str) -> bool:
    """Check teaching registration and manual exclusion, without reading notes."""
    v, c = data.volunteers[volunteer], data.children[child]
    return (subject, c.grade) in v.skills and data.ratings.get((volunteer, child)) != "Không ghép"

def candidates(data: Dataset) -> list[Session]:
    """Enumerate legal single-child and two-child sessions."""
    sessions = []
    for vid, v in sorted(data.volunteers.items()):
        for day in DAYS:
            if day not in v.days:
                continue
            for subject in sorted({d.subject for d in data.demands}):
                kids = sorted(d.child for d in data.demands if d.subject == subject
                              and day in data.children[d.child].days
                              and eligible(data, vid, d.child, subject))
                sessions.extend(Session(vid, subject, day, (c,)) for c in kids)
                for a, b in combinations(kids, 2):
                    if can_pair(data, a, b):
                        sessions.append(Session(vid, subject, day, (a, b)))
    return sessions

def validate_locks(data: Dataset) -> None:
    """Explain incompatible locked choices before invoking the optimizer."""
    grouped: dict[tuple[str, str], list[Lock]] = {}
    child_days = {}
    child_subjects = {}
    demands = {(d.child, d.subject) for d in data.demands}
    for lock in sorted(data.locks, key=repr):
        v, c = data.volunteers.get(lock.volunteer), data.children.get(lock.child)
        if not v or not c or (lock.child, lock.subject) not in demands:
            raise DataError(f"Lựa chọn khóa {lock}: mã hoặc nhu cầu không tồn tại.")
        if lock.day not in v.days & c.days or not eligible(data, v.id, c.id, lock.subject):
            raise DataError(f"Khóa {v.id}–{c.id}: không phù hợp môn/lớp, ngày rảnh hoặc đang Không ghép.")
        group = (v.id, lock.day)
        if (c.id, lock.day) in child_days and child_days[c.id, lock.day] != group:
            raise DataError(f"Bé {c.id} có hai lựa chọn khóa trùng ngày {lock.day}.")
        if (c.id, lock.subject) in child_subjects:
            raise DataError(f"Nhu cầu {c.id}–{lock.subject} được khóa nhiều lần.")
        child_days[c.id, lock.day] = group
        child_subjects[c.id, lock.subject] = True
        grouped.setdefault(group, []).append(lock)
    for (vid, day), locks in grouped.items():
        if len(locks) > 2 or len({l.subject for l in locks}) > 1:
            raise DataError(f"TNV {vid} có lựa chọn khóa trùng giờ vào {day}.")
        if len(locks) == 2:
            if not data.allow_group_sessions and not data.sites:
                raise DataError(f"TNV {vid}: hai bé được khóa cùng ngày {day}, nhưng đang chọn dạy 1:1.")
            a, b = (l.child for l in locks)
            if not can_pair(data, a, b):
                raise DataError(f"Khóa {a}–{b}: hai bé khác tuổi hoặc xung khắc.")
    for vid, v in data.volunteers.items():
        if sum(key[0] == vid for key in grouped) > v.max_sessions:
            raise DataError(f"TNV {vid}: số buổi khóa vượt giới hạn {v.max_sessions}.")
    if data.sites and data.locks:
        legal = candidates(data)
        for lock in data.locks:
            site = data.children[lock.child].site
            policy = data.sites.get(site)
            if policy and policy.require_academic_lead and not any(session_site(data, s) == site and s.day == lock.day
                    and is_academic_lead(data, s.volunteer) and data.volunteers[s.volunteer].max_sessions > 0 for s in legal):
                raise DataError(f"Khóa tại {site}, {lock.day}: không có BTC ACA IC rảnh và đủ chuyên môn trực tiếp dạy để làm lead.")

def solve(data: Dataset, time_limit: float = 30.0) -> Result:
    """Maximize children, demands, preferences, singles, then balance loads.

    Freeze an objective only after optimality is proven. On timeout return the
    best feasible incumbent, never sacrifice a higher-priority objective.
    """
    validate_locks(data)
    choices = candidates(data)
    model = cp_model.CpModel()
    x = [model.new_bool_var(f"session_{i}") for i in range(len(choices))]
    for vid, v in data.volunteers.items():
        model.add(sum(x[i] for i, s in enumerate(choices) if s.volunteer == vid) <= v.max_sessions)
        for day in DAYS:
            model.add(sum(x[i] for i, s in enumerate(choices) if s.volunteer == vid and s.day == day) <= 1)
    for cid in data.children:
        for day in DAYS:
            model.add(sum(x[i] for i, s in enumerate(choices) if cid in s.children and s.day == day) <= 1)
    for d in data.demands:
        model.add(sum(x[i] for i, s in enumerate(choices) if d.child in s.children and s.subject == d.subject) <= 1)
    for site, policy in data.sites.items():
        if not policy.require_academic_lead:
            continue
        site_active = []
        for day in DAYS:
            relevant = [i for i, s in enumerate(choices) if session_site(data, s) == site and s.day == day]
            lead_choices = [x[i] for i in relevant if is_academic_lead(data, choices[i].volunteer)]
            active = model.new_bool_var(f"active_{site}_{day}")
            site_active.append(active)
            for i in relevant:
                model.add(x[i] <= active)
            model.add(active <= sum(x[i] for i in relevant))
            model.add(sum(lead_choices) >= active)
        # One simultaneous class per child implies at most one fulfilled
        # demand per active day, regardless of how many people are available.
        site_children = {d.child for d in data.demands if data.children[d.child].site == site}
        model.add(sum(len(s.children) * x[i] for i, s in enumerate(choices) if session_site(data, s) == site)
                  <= len(site_children) * sum(site_active))
    for lock in data.locks:
        model.add(sum(x[i] for i, s in enumerate(choices) if s.volunteer == lock.volunteer
                      and s.day == lock.day and s.subject == lock.subject and lock.child in s.children) == 1)
    covered = []
    for cid in data.children:
        y = model.new_bool_var(f"covered_{cid}")
        related = [x[i] for i, s in enumerate(choices) if cid in s.children]
        model.add_max_equality(y, related or [0])
        covered.append(y)
    # A child covered at least once consumes at least one fulfilled demand.
    # State this aggregate bound explicitly so scarce-capacity cases can prove
    # optimal coverage without enumerating symmetric schedules.
    model.add(sum(covered) <= sum(len(s.children) * x[i] for i, s in enumerate(choices)))
    loads = []
    second_sessions = []
    for vid, v in data.volunteers.items():
        load = model.new_int_var(0, min(5, v.max_sessions), f"load_{vid}")
        model.add(load == sum(x[i] for i, s in enumerate(choices) if s.volunteer == vid))
        square = model.new_int_var(0, 25, f"square_{vid}")
        model.add_multiplication_equality(square, [load, load])
        loads.append(square)
        if v.kind == "TNV" and v.max_sessions > 1:
            extra = model.new_int_var(0, max(0, v.max_sessions - 1), f"extra_{vid}")
            model.add_max_equality(extra, [load - 1, 0])
            second_sessions.append(extra)
    objectives = [sum(covered), sum(len(s.children) * x[i] for i, s in enumerate(choices)),
                  sum(sum(data.ratings.get((s.volunteer, c)) == "Ưu tiên" for c in s.children) * x[i]
                      for i, s in enumerate(choices)),
                  -sum(x[i] for i, s in enumerate(choices) if len(s.children) == 2), -sum(loads)]
    if data.prioritize_volunteers:
        btc_sessions = sum(x[i] for i, s in enumerate(choices) if data.volunteers[s.volunteer].kind == "BTC")
        objectives[2:2] = [-btc_sessions, -sum(second_sessions)]
    # The validated locks themselves form a feasible baseline, including before
    # the first search finds an incumbent.
    baseline = {}
    for lock in data.locks:
        key = (lock.volunteer, lock.subject, lock.day)
        baseline.setdefault(key, []).append(lock.child)
    best = [Session(v, sub, day, tuple(sorted(kids))) for (v, sub, day), kids in baseline.items()]
    # Locked sessions alone may lack the mandatory teaching lead. Use them as
    # an incumbent only when all site/day lead requirements are satisfied.
    baseline_leads = pick_leads(data, best)
    if any(data.sites.get(session_site(data, s)) and data.sites[session_site(data, s)].require_academic_lead
           and (session_site(data, s), s.day) not in baseline_leads for s in best):
        best = []
    values = []
    start = monotonic()
    for objective in objectives:
        if isinstance(objective, int):
            values.append(objective)
            continue
        remaining = time_limit - (monotonic() - start)
        if remaining <= 0:
            if data.locks and not best:
                raise DataError("Chưa tìm được lịch hợp lệ giữ khóa và có lead ACA IC; hãy tăng thời gian xếp hoặc kiểm tra khóa.")
            return Result(best, False, values, pick_leads(data, best))
        model.maximize(objective)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = remaining
        solver.parameters.num_search_workers = 8 if len(choices) > 1000 else 1
        status = solver.solve(model)
        if status == cp_model.INFEASIBLE:
            raise DataError("Các lựa chọn khóa không thể cùng xuất hiện trong một lịch.")
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if data.locks and not best:
                raise DataError("Chưa tìm được lịch hợp lệ giữ khóa và có lead ACA IC.")
            return Result(best, False, values, pick_leads(data, best))
        best = [s for i, s in enumerate(choices) if solver.value(x[i])]
        value = int(solver.value(objective))
        values.append(value)
        if status != cp_model.OPTIMAL:
            return Result(best, False, values, pick_leads(data, best))
        model.add(objective == value)
        # Seed the next priority with the complete feasible assignment already
        # found. This avoids rediscovering a schedule among symmetric choices.
        model.clear_hints()
        for index in range(len(model.proto.variables)):
            variable = model.get_int_var_from_proto_index(index)
            model.add_hint(variable, solver.value(variable))
    return Result(sorted(best, key=lambda s: (session_site(data, s), DAYS.index(s.day), s.volunteer)), True, values, pick_leads(data, best))
