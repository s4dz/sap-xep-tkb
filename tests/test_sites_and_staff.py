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

def test_lead_only_does_not_need_teaching_skill_and_counts_weekly_visit():
    d=example()
    d.sites['s1']=SitePolicy(False,True,False,frozenset({DAYS[0]}),False)
    d.volunteers['L']=Volunteer('L',frozenset({('Tiếng Anh',3)}),frozenset(DAYS),1,'BTC','ACA IC')
    result=solve(d)
    assert result.leads=={('s1',DAYS[0]):'L'}
    assert all(s.volunteer!='L' for s in result.sessions)
    assert read_workbook(export_workbook(d,result))==d
    d.sites['s1']=replace(d.sites['s1'],required_days=frozenset(DAYS[:2]))
    with pytest.raises(DataError):solve(d)

def test_one_lead_cannot_cover_two_sites_same_day():
    d=example()
    d.children['B']=replace(d.children['B'],site='s2')
    for site in d.sites:d.sites[site]=SitePolicy(False,True,False,frozenset({DAYS[0]}),False)
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset(DAYS),2,'BTC','ACA IC')
    with pytest.raises(DataError):solve(d)

def test_teaching_and_leading_same_site_counts_once():
    d=example()
    d.volunteers.pop('V')
    d.children.pop('B');d.demands=[Demand('A','Toán')]
    d.sites['s1']=SitePolicy(False,True,False,frozenset({DAYS[0]}),True)
    d.volunteers['L']=Volunteer('L',frozenset({('Toán',3)}),frozenset({DAYS[0]}),1,'BTC','ACA IC')
    result=solve(d)
    assert len(result.sessions)==1 and result.leads=={('s1',DAYS[0]):'L'}

def test_two_sites_five_days_use_ten_distinct_one_visit_leads():
    d=week_example()
    d.children.update({f'A{i}':Child(f'A{i}',None,3,frozenset(DAYS),'s1') for i in range(5)})
    d.demands.extend(Demand(f'A{i}','Toán') for i in range(5))
    d.sites['s1']=SitePolicy(False,True,False,frozenset(DAYS),False)
    for i,day in enumerate(DAYS):
        vid=f'K{i}'
        d.volunteers[vid]=Volunteer(vid,frozenset({('Toán',3)}),frozenset({day}),1,'BTC','ACA IC')
    result=solve(d)
    assert len(result.leads)==10 and len(set(result.leads.values()))==10
    for (site,day),vid in result.leads.items():
        visits={(site,day)}|{(d.children[s.children[0]].site,s.day) for s in result.sessions if s.volunteer==vid}
        assert len(visits)==1
        if site=='s2':assert any(s.volunteer==vid and s.day==day for s in result.sessions)

def test_chemistry_flexibility_requires_flag_and_keeps_grade():
    from scheduler.engine import eligible
    d=example()
    d.children['A']=replace(d.children['A'],grade=11)
    d.volunteers['V']=replace(d.volunteers['V'],skills=frozenset({('Hóa học',11)}))
    assert not eligible(d,'V','A','Vật lý')
    d.flexible_science=True
    assert eligible(d,'V','A','Vật lý') and eligible(d,'V','A','Sinh học')
    assert not eligible(d,'V','A','Toán')
    d.children['A']=replace(d.children['A'],grade=10)
    assert not eligible(d,'V','A','Vật lý')

def test_secondary_chemistry_can_cover_integrated_science_when_enabled():
    from scheduler.engine import eligible
    d=example();d.flexible_science=True
    d.children['A']=replace(d.children['A'],grade=8)
    d.volunteers['V']=replace(d.volunteers['V'],skills=frozenset({('Hóa học',8)}))
    assert eligible(d,'V','A','Khoa học tự nhiên')

def test_other_btc_before_aca_then_tnv_before_both():
    d=example();d.prioritize_other_btc=True
    d.children.pop('B');d.demands=[Demand('A','Toán')]
    v=d.volunteers.pop('V')
    d.volunteers['ACA']=replace(v,id='ACA',kind='BTC',role='ACA IC')
    d.volunteers['OTHER']=replace(v,id='OTHER',kind='BTC',role='WF IC')
    assert solve(d).sessions[0].volunteer=='OTHER'
    d.volunteers['V']=v
    assert solve(d).sessions[0].volunteer=='V'

def test_prefer_pairs_uses_approved_pair_instead_of_two_singles():
    d=example();d.prefer_pairs=True
    result=solve(d)
    assert len(result.sessions)==1 and len(result.sessions[0].children)==2
    d.sites['s1']=SitePolicy(False,False,False)
    assert all(len(s.children)==1 for s in solve(d).sessions)

def test_flexible_resource_and_pair_preferences_roundtrip():
    d=example();d.flexible_science=d.prioritize_other_btc=d.prefer_pairs=True
    assert read_workbook(export_workbook(d,solve(d)))==d
