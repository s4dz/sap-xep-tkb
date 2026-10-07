"""Behavioral tests for hard constraints and the order of objectives."""
from dataclasses import replace
import pytest
from scheduler.models import Child, Dataset, DataError, Demand, Lock, Volunteer, DAYS
from scheduler.engine import solve

def fixture(children=2, limit=1):
    return Dataset({"V": Volunteer("V", frozenset({("Toán", 3), ("Tiếng Anh", 3)}), frozenset(DAYS), limit)},
                   {str(i): Child(str(i), 8, 3, frozenset(DAYS)) for i in range(children)},
                   [Demand(str(i), "Toán") for i in range(children)])

def test_common_availability_only():
    data = fixture(1)
    data.volunteers["V"] = replace(data.volunteers["V"], days=frozenset({DAYS[0]}))
    data.children["0"] = replace(data.children["0"], days=frozenset({DAYS[1]}))
    assert not solve(data).sessions
    data.children["0"] = replace(data.children["0"], days=frozenset({DAYS[0]}))
    assert solve(data).sessions[0].day == DAYS[0]

@pytest.mark.parametrize("skills", [frozenset({("Tiếng Anh", 3)}), frozenset({("Toán", 4)})])
def test_subject_and_exact_grade(skills):
    data = fixture(1)
    data.volunteers["V"] = replace(data.volunteers["V"], skills=skills)
    assert not solve(data).sessions

def test_volunteer_limit_and_same_day():
    data = fixture(5, 2)
    result = solve(data)
    assert len(result.sessions) == 2
    assert len({s.day for s in result.sessions}) == 2

def test_child_time_conflicts():
    data = fixture(1, 2)
    data.children["0"] = replace(data.children["0"], days=frozenset({DAYS[0]}))
    data.demands.append(Demand("0", "Tiếng Anh"))
    data.volunteers["W"] = replace(data.volunteers["V"], id="W")
    assert sum(len(s.children) for s in solve(data).sessions) == 1

def test_incompatible_children():
    data = fixture()
    data.conflicts.add(frozenset({"0", "1"}))
    assert sum(len(s.children) for s in solve(data).sessions) == 1

def test_two_children_same_age_and_subject():
    data = fixture()
    result = solve(data)
    assert len(result.sessions[0].children) == 2
    data.children["1"] = replace(data.children["1"], age=9)
    assert len(solve(data).sessions[0].children) == 1
    data.children["1"] = replace(data.children["1"], age=8)
    data.demands[1] = Demand("1", "Tiếng Anh")
    assert len(solve(data).sessions[0].children) == 1

def test_forbidden_pair():
    data = fixture()
    data.ratings["V", "0"] = "Không ghép"
    assert all("0" not in s.children for s in solve(data).sessions)

def test_locked_choice_preserved():
    data = fixture()
    data.locks.add(Lock("V", "0", "Toán", DAYS[4]))
    assert any(s.day == DAYS[4] and "0" in s.children for s in solve(data).sessions)

@pytest.mark.parametrize("case", ["limit", "subject", "child", "age", "forbidden", "duplicate_demand", "capacity"])
def test_conflicting_locks(case):
    data = fixture(3)
    data.locks.add(Lock("V", "0", "Toán", DAYS[0]))
    if case == "limit":
        data.locks.add(Lock("V", "1", "Toán", DAYS[1]))
    elif case == "subject":
        data.demands.append(Demand("1", "Tiếng Anh"))
        data.locks.add(Lock("V", "1", "Tiếng Anh", DAYS[0]))
    elif case == "child":
        data.volunteers["W"] = replace(data.volunteers["V"], id="W")
        data.demands.append(Demand("0", "Tiếng Anh"))
        data.locks.add(Lock("W", "0", "Tiếng Anh", DAYS[0]))
    elif case == "age":
        data.children["1"] = replace(data.children["1"], age=9)
        data.locks.add(Lock("V", "1", "Toán", DAYS[0]))
    elif case == "forbidden":
        data.ratings["V", "0"] = "Không ghép"
    elif case == "duplicate_demand":
        data.volunteers["V"] = replace(data.volunteers["V"], max_sessions=2)
        data.locks.add(Lock("V", "0", "Toán", DAYS[1]))
    else:
        data.locks.update({Lock("V", "1", "Toán", DAYS[0]), Lock("V", "2", "Toán", DAYS[0])})
    with pytest.raises(DataError):
        solve(data)

def test_shortage_returns_best_partial_schedule():
    result = solve(fixture(5))
    assert result.optimal
    assert sum(len(s.children) for s in result.sessions) == 2

def test_single_child_classes_preferred_when_coverage_equal():
    data = fixture()
    data.volunteers["W"] = replace(data.volunteers["V"], id="W")
    result = solve(data)
    assert len(result.sessions) == 2
    assert all(len(s.children) == 1 for s in result.sessions)

def test_manual_preference_before_single_class():
    data = fixture()
    data.volunteers["W"] = replace(data.volunteers["V"], id="W")
    data.ratings.update({("V", "0"): "Ưu tiên", ("V", "1"): "Ưu tiên"})
    result = solve(data)
    assert len(result.sessions) == 1
    assert result.sessions[0].volunteer == "V"

def test_children_before_total_demands_and_preference():
    data = fixture(2, 2)
    data.children["1"] = replace(data.children["1"], age=9)
    data.demands.append(Demand("0", "Tiếng Anh"))
    data.ratings["V", "0"] = "Ưu tiên"
    result = solve(data)
    assert {c for s in result.sessions for c in s.children} == {"0", "1"}

def test_balance_when_higher_objectives_equal():
    data = fixture(4, 4)
    for cid, child in data.children.items():
        data.children[cid] = replace(child, age=8 + int(cid))
    data.volunteers["W"] = replace(data.volunteers["V"], id="W")
    result = solve(data)
    assert [sum(s.volunteer == vid for s in result.sessions) for vid in ("V", "W")] == [2, 2]

def test_timeout_keeps_valid_locks():
    data = fixture()
    data.locks.add(Lock("V", "0", "Toán", DAYS[0]))
    result = solve(data, time_limit=0)
    assert not result.optimal
    assert result.sessions[0].children == ("0",)
