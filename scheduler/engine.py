"""CP-SAT scheduling with sequential (lexicographic) objectives."""
from itertools import combinations
from time import monotonic
from ortools.sat.python import cp_model
from .models import DAYS, Dataset, DataError, Lock, Result, Session
from .policies import can_pair, is_academic_lead, pick_leads, session_site, teaching_skills

def eligible(data: Dataset, volunteer: str, child: str, subject: str) -> bool:
    """Check teaching registration and manual exclusion, without reading notes."""
    v, c = data.volunteers[volunteer], data.children[child]
    return (subject, c.grade) in teaching_skills(data,volunteer) and data.ratings.get((volunteer, child)) != "Không ghép"

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
            if policy and policy.require_academic_lead and policy.lead_must_teach and not any(session_site(data, s) == site and s.day == lock.day
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
    lead_vars = {}
    attendance = {}
    for site, policy in data.sites.items():
        for day in policy.required_days:
            model.add(sum(x[i] for i, s in enumerate(choices) if session_site(data, s) == site and s.day == day) >= 1)
        if not policy.require_academic_lead:
            continue
        site_active = []
        for day in DAYS:
            relevant = [i for i, s in enumerate(choices) if session_site(data, s) == site and s.day == day]
            active = model.new_bool_var(f"active_{site}_{day}")
            site_active.append(active)
            for i in relevant:
                model.add(x[i] <= active)
            model.add(active <= sum(x[i] for i in relevant))
            daily_leads = []
            for vid,v in data.volunteers.items():
                if not is_academic_lead(data,vid) or day not in v.days:
                    continue
                lead = model.new_bool_var(f"lead_{site}_{day}_{vid}")
                lead_vars[site,day,vid] = lead
                daily_leads.append(lead)
                teaching = [x[i] for i in relevant if choices[i].volunteer == vid]
                if policy.lead_must_teach:
                    model.add(lead <= sum(teaching))
                present = model.new_bool_var(f"present_{site}_{day}_{vid}")
                model.add_max_equality(present,[lead,*teaching])
                attendance[site,day,vid] = present
            model.add(sum(daily_leads) == active)
        # One simultaneous class per child implies at most one fulfilled
        # demand per active day, regardless of how many people are available.
        site_children = {d.child for d in data.demands if data.children[d.child].site == site}
        model.add(sum(len(s.children) * x[i] for i, s in enumerate(choices) if session_site(data, s) == site)
                  <= len(site_children) * sum(site_active))
    # Lead-only attendance consumes the same weekly/day resource as teaching.
    # A teaching lead at the same site counts once, never twice.
    person_attendance = {}
    for vid,v in data.volunteers.items():
        if not is_academic_lead(data,vid):
            continue
        present = []
        for day in DAYS:
            daily = []
            for site in {c.site for c in data.children.values()}:
                if (site,day,vid) in attendance:
                    daily.append(attendance[site,day,vid])
                else:
                    daily.extend(x[i] for i,s in enumerate(choices) if s.volunteer==vid and s.day==day and session_site(data,s)==site)
            model.add(sum(daily)<=1)
            present.extend(daily)
        model.add(sum(present)<=v.max_sessions)
        person_attendance[vid]=sum(present)
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
        model.add(load == person_attendance.get(vid,sum(x[i] for i, s in enumerate(choices) if s.volunteer == vid)))
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
                  (1 if data.prefer_pairs else -1)*sum(x[i] for i, s in enumerate(choices) if len(s.children) == 2), -sum(loads)]
    if data.prioritize_volunteers:
        btc_sessions = sum(x[i] for i, s in enumerate(choices) if data.volunteers[s.volunteer].kind == "BTC")
        if data.prioritize_other_btc:
            aca_sessions=sum(x[i] for i,s in enumerate(choices) if is_academic_lead(data,s.volunteer))
            objectives[2:2] = [-aca_sessions, -(btc_sessions-aca_sessions), -sum(second_sessions)]
        else:
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
    baseline_valid = not any(data.sites.get(session_site(data, s)) and data.sites[session_site(data, s)].require_academic_lead
           and (session_site(data, s), s.day) not in baseline_leads for s in best)
    baseline_valid = baseline_valid and all(any(session_site(data, s) == site and s.day == day for s in best)
                          for site, policy in data.sites.items() for day in policy.required_days)
    # Standalone leads need a model assignment; teaching locks alone cannot
    # establish a feasible incumbent for a site allowing lead-only attendance.
    if any(p.require_academic_lead and not p.lead_must_teach and (p.required_days or any(session_site(data,s)==site for s in best)) for site,p in data.sites.items()):
        baseline_valid = False
    if not baseline_valid:
        best = []
    values = []
    best_leads = baseline_leads if baseline_valid else {}
    start = monotonic()
    for objective in objectives:
        if isinstance(objective, int):
            values.append(objective)
            continue
        remaining = time_limit - (monotonic() - start)
        if remaining <= 0:
            if not baseline_valid and not best:
                raise DataError("Chưa tìm được lịch hợp lệ đáp ứng ngày học bắt buộc, khóa và lead; hãy tăng thời gian xếp hoặc kiểm tra dữ liệu.")
            return Result(best, False, values, best_leads)
        model.maximize(objective)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = remaining
        solver.parameters.num_search_workers = 8 if len(choices) > 1000 else 1
        status = solver.solve(model)
        if status == cp_model.INFEASIBLE:
            raise DataError("Không có lịch đáp ứng đồng thời các lựa chọn khóa, ngày học bắt buộc và yêu cầu lead.")
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if not baseline_valid and not best:
                raise DataError("Chưa tìm được lịch hợp lệ đáp ứng ngày học bắt buộc, khóa và lead.")
            return Result(best, False, values, best_leads)
        best = [s for i, s in enumerate(choices) if solver.value(x[i])]
        best_leads = {(site,day):vid for (site,day,vid),variable in sorted(lead_vars.items(),key=lambda item:(item[0][0],DAYS.index(item[0][1]),item[0][2])) if solver.value(variable)}
        value = int(solver.value(objective))
        values.append(value)
        if status != cp_model.OPTIMAL:
            return Result(best, False, values, best_leads)
        model.add(objective == value)
        # Seed the next priority with the complete feasible assignment already
        # found. This avoids rediscovering a schedule among symmetric choices.
        model.clear_hints()
        for index in range(len(model.proto.variables)):
            variable = model.get_int_var_from_proto_index(index)
            model.add_hint(variable, solver.value(variable))
    return Result(sorted(best, key=lambda s: (session_site(data, s), DAYS.index(s.day), s.volunteer)), True, values, best_leads)
