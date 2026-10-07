"""CP-SAT scheduling with sequential (lexicographic) objectives."""
from itertools import combinations
from time import monotonic
from ortools.sat.python import cp_model
from .models import DAYS, Dataset, DataError, Lock, Result, Session

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
                    if data.children[a].age == data.children[b].age and frozenset((a, b)) not in data.conflicts:
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
            a, b = (l.child for l in locks)
            if data.children[a].age != data.children[b].age or frozenset((a, b)) in data.conflicts:
                raise DataError(f"Khóa {a}–{b}: hai bé khác tuổi hoặc xung khắc.")
    for vid, v in data.volunteers.items():
        if sum(key[0] == vid for key in grouped) > v.max_sessions:
            raise DataError(f"TNV {vid}: số buổi khóa vượt giới hạn {v.max_sessions}.")

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
    for lock in data.locks:
        model.add(sum(x[i] for i, s in enumerate(choices) if s.volunteer == lock.volunteer
                      and s.day == lock.day and s.subject == lock.subject and lock.child in s.children) == 1)
    covered = []
    for cid in data.children:
        y = model.new_bool_var(f"covered_{cid}")
        related = [x[i] for i, s in enumerate(choices) if cid in s.children]
        model.add_max_equality(y, related or [0])
        covered.append(y)
    loads = []
    for vid, v in data.volunteers.items():
        load = model.new_int_var(0, min(5, v.max_sessions), f"load_{vid}")
        model.add(load == sum(x[i] for i, s in enumerate(choices) if s.volunteer == vid))
        square = model.new_int_var(0, 25, f"square_{vid}")
        model.add_multiplication_equality(square, [load, load])
        loads.append(square)
    objectives = [sum(covered), sum(len(s.children) * x[i] for i, s in enumerate(choices)),
                  sum(sum(data.ratings.get((s.volunteer, c)) == "Ưu tiên" for c in s.children) * x[i]
                      for i, s in enumerate(choices)),
                  -sum(x[i] for i, s in enumerate(choices) if len(s.children) == 2), -sum(loads)]
    # The validated locks themselves form a feasible baseline, including before
    # the first search finds an incumbent.
    baseline = {}
    for lock in data.locks:
        key = (lock.volunteer, lock.subject, lock.day)
        baseline.setdefault(key, []).append(lock.child)
    best = [Session(v, sub, day, tuple(sorted(kids))) for (v, sub, day), kids in baseline.items()]
    values = []
    start = monotonic()
    for objective in objectives:
        remaining = time_limit - (monotonic() - start)
        if remaining <= 0:
            return Result(best, False, values)
        model.maximize(objective)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = remaining
        solver.parameters.num_search_workers = 1
        status = solver.solve(model)
        if status == cp_model.INFEASIBLE:
            raise DataError("Các lựa chọn khóa không thể cùng xuất hiện trong một lịch.")
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return Result(best, False, values)
        best = [s for i, s in enumerate(choices) if solver.value(x[i])]
        value = int(solver.value(objective))
        values.append(value)
        if status != cp_model.OPTIMAL:
            return Result(best, False, values)
        model.add(objective == value)
    return Result(sorted(best, key=lambda s: (DAYS.index(s.day), s.volunteer)), True, values)
