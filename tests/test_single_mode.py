"""Regression coverage for single-child-only scheduling without age."""
from dataclasses import replace
import pytest
from scheduler.models import DataError, Lock, DAYS
from scheduler.engine import solve
from scheduler.excel_io import read_workbook, subject
from scheduler.export import export_workbook
from scripts.sample_data import sample_data
from tests.test_engine import fixture

def test_single_mode_forbids_pair_even_if_same_age():
    data = fixture()
    data.allow_group_sessions = False
    result = solve(data)
    assert len(result.sessions)==1
    assert len(result.sessions[0].children)==1

def test_missing_age_never_enables_pair():
    data=fixture()
    for cid,c in data.children.items():data.children[cid]=replace(c,age=None)
    assert all(len(s.children)==1 for s in solve(data).sessions)

def test_single_mode_and_blank_ages_roundtrip():
    data=sample_data()
    data.allow_group_sessions=False
    for cid,c in data.children.items():data.children[cid]=replace(c,age=None)
    loaded=read_workbook(export_workbook(data))
    assert loaded==data
    assert all(len(s.children)==1 for s in solve(loaded).sessions)

def test_single_mode_rejects_locked_pair():
    data=fixture()
    data.allow_group_sessions=False
    data.locks={Lock('V','0','Toán',DAYS[0]),Lock('V','1','Toán',DAYS[0])}
    with pytest.raises(DataError,match='1:1'):solve(data)

def test_new_subjects_have_independent_skills():
    data=fixture(1)
    data.children['0']=replace(data.children['0'],grade=11,age=None)
    data.demands[0]=replace(data.demands[0],subject='Vật lý')
    data.volunteers['V']=replace(data.volunteers['V'],skills=frozenset({('Vật lý',11)}))
    loaded=read_workbook(export_workbook(data))
    assert solve(loaded).sessions[0].subject=='Vật lý'
    loaded.volunteers['V']=replace(loaded.volunteers['V'],skills=frozenset({('Hóa học',11)}))
    assert not solve(loaded).sessions
    assert subject('Hoá Học')=='Hóa học'
    assert subject('Sử')=='Lịch sử'
