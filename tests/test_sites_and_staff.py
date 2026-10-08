from dataclasses import replace
import pytest
from scheduler.models import Child, Dataset, Demand, Volunteer, SitePolicy, DAYS, Lock, DataError
from scheduler.engine import solve, candidates
from scheduler.export import export_workbook
from scheduler.excel_io import read_workbook

def example():
    return Dataset({'V':Volunteer('V',frozenset({('Toán',3)}),frozenset(DAYS),2)},
        {'A':Child('A',8,3,frozenset(DAYS),'s1'), 'B':Child('B',8,3,frozenset(DAYS),'s1')},
        [Demand('A','Toán'),Demand('B','Toán')],sites={'s1':SitePolicy(True,False,False),'s2':SitePolicy(False,True,False)},prioritize_volunteers=True)

def test_only_primary_same_site_pairs():
    d=example()
    assert any(len(s.children)==2 for s in candidates(d))
    d.children['B']=replace(d.children['B'],site='s2')
    assert not any(len(s.children)==2 for s in candidates(d))
    d.children['B']=replace(d.children['B'],site='s1',grade=6)
    d.children['A']=replace(d.children['A'],grade=6)
    d.volunteers['V']=replace(d.volunteers['V'],skills=frozenset({('Toán',6)}))
    assert not any(len(s.children)==2 for s in candidates(d))

def test_explicit_grade_proxy_with_unknown_ages():
    d=example()
    d.children={cid:replace(c,age=None) for cid,c in d.children.items()}
    assert not any(len(s.children)==2 for s in candidates(d))
    d.sites['s1']=SitePolicy(True,False,True)
    assert any(len(s.children)==2 for s in candidates(d))

def test_mandatory_aca_teaches_and_is_lead():
    d=example()
    d.children={cid:replace(c,site='s2') for cid,c in d.children.items()}
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset({DAYS[2]}),1,'BTC','ACA IC')
    result=solve(d)
    assert result.leads=={('s2',DAYS[2]):'L'}
    assert all(s.day==DAYS[2] for s in result.sessions)
    assert len(result.sessions)==2
    assert any(s.volunteer=='L' for s in result.sessions)

def test_no_aca_prevents_site_classes_even_with_other_btc():
    d=example()
    d.children={cid:replace(c,site='s2') for cid,c in d.children.items()}
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset(DAYS),2,'BTC','WF IC')
    assert not solve(d).sessions

def test_lead_one_session_means_one_active_day():
    d=example()
    d.children={str(i):Child(str(i),None,3,frozenset(DAYS),'s2') for i in range(4)}
    d.demands=[Demand(str(i),'Toán') for i in range(4)]
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset(DAYS[2:]),1,'BTC','ACA_IC')
    result=solve(d)
    assert len({s.day for s in result.sessions})==1
    assert sum(s.volunteer=='L' for s in result.sessions)==1
    assert len(result.leads)==1

def test_second_tnv_before_optional_btc_and_first_before_second():
    d=example()
    d.sites['s1']=SitePolicy(False,False,False)
    d.volunteers['C']=Volunteer('C',frozenset({('Toán',3)}),frozenset(DAYS),2,'BTC','')
    result=solve(d)
    assert len(result.sessions)==2 and all(s.volunteer=='V' for s in result.sessions)
    d.volunteers['W']=replace(d.volunteers['V'],id='W',max_sessions=1)
    result=solve(d)
    assert {s.volunteer for s in result.sessions}=={'V','W'}

def test_cross_site_staff_does_not_double_book_or_exceed_weekly_cap():
    d=example()
    d.children['B']=replace(d.children['B'],site='s2')
    d.sites['s2']=SitePolicy(False,False,False)
    d.volunteers['V']=replace(d.volunteers['V'],days=frozenset({DAYS[0]}))
    assert len(solve(d).sessions)==1
    d.volunteers['V']=replace(d.volunteers['V'],days=frozenset(DAYS),max_sessions=1)
    assert len(solve(d).sessions)==1

def test_lock_on_lead_unavailable_day_is_infeasible():
    d=example()
    d.children['A']=replace(d.children['A'],site='s2')
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset({DAYS[2]}),1,'BTC','ACA IC')
    d.locks.add(Lock('V','A','Toán',DAYS[0]))
    with pytest.raises(DataError):solve(d)

def test_site_and_staff_config_roundtrip():
    d=example()
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset({DAYS[2]}),1,'BTC','ACA IC')
    result=solve(d)
    assert read_workbook(export_workbook(d,result))==d

def week_example():
    d=example()
    d.children={str(i):Child(str(i),None,3,frozenset(DAYS),'s2') for i in range(10)}
    d.demands=[Demand(cid,'Toán') for cid in d.children]
    d.sites['s2']=SitePolicy(False,True,False,frozenset(DAYS))
    d.volunteers['V']=replace(d.volunteers['V'],max_sessions=5)
    for i,day in enumerate(DAYS):
        vid=f'L{i}'
        d.volunteers[vid]=Volunteer(vid,frozenset({('Toán',3)}),frozenset({day}),1,'BTC','ACA IC')
    return d

def test_required_week_has_teaching_lead_every_day():
    d=week_example()
    result=solve(d)
    assert result.optimal and len(result.sessions)==10
    assert {s.day for s in result.sessions}==set(DAYS)
    assert set(result.leads)=={('s2',day) for day in DAYS}
    assert all(sum(s.volunteer==v for s in result.sessions)==1 for v in result.leads.values())
    assert read_workbook(export_workbook(d,result))==d

def test_required_day_without_available_lead_reports_error():
    d=week_example()
    del d.volunteers['L0']
    with pytest.raises(DataError,match='ngày học bắt buộc'):solve(d)

def test_required_week_timeout_does_not_return_invalid_empty_schedule():
    with pytest.raises(DataError,match='ngày học bắt buộc'):solve(week_example(),0)

def test_merged_role_applies_to_every_person_in_range_only():
    from openpyxl import Workbook
    from scheduler.excel_io import merged_cell_value
    ws=Workbook().active
    ws['A2']='WF IC';ws.merge_cells('A2:A3')
    ws['A4']='ACA IC';ws.merge_cells('A4:A6')
    ws['A7']='PR IC';ws.merge_cells('A7:A8')
    assert [merged_cell_value(ws,i,1) for i in range(2,10)]==['WF IC','WF IC','ACA IC','ACA IC','ACA IC','PR IC','PR IC',None]
