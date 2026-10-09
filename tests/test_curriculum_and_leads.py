from dataclasses import replace
from scheduler.models import Dataset, Volunteer, Child, Demand, SitePolicy, DAYS
from scheduler.engine import solve, eligible, solve_for_display
from scheduler.export import export_workbook, timetable_grid
from scheduler.excel_io import read_workbook
from scheduler.policies import lead_ids


def example():
    return Dataset(
        {'V':Volunteer('V',frozenset({('Toán',3)}),frozenset(DAYS),2)},
        {'C':Child('C',None,3,frozenset(DAYS),'s')},[Demand('C','Toán')],
        sites={'s':SitePolicy(require_academic_lead=True,lead_must_teach=False,lead_count=2)})


def test_two_distinct_leads_and_separate_weekly_limits():
    d=example()
    for vid in ('A','B'):
        d.volunteers[vid]=Volunteer(vid,frozenset({('Toán',3)}),frozenset(DAYS),1,'BTC','ACA IC',True,2,2)
    r=solve(d)
    session=r.sessions[0]
    assert len(lead_ids(r,'s',session.day))==2
    assert len(set(lead_ids(r,'s',session.day)))==2
    assert all(vid in timetable_grid(d,r,'s')[-2][3+DAYS.index(session.day)] for vid in ('A','B'))
    assert read_workbook(export_workbook(d))==d


def test_disallowed_lead_keeps_aca_classification_and_teaches_fixed_class():
    d=example()
    d.sites['s']=replace(d.sites['s'],lead_count=1)
    d.volunteers['A']=Volunteer('A',frozenset({('Toán',3)}),frozenset(DAYS),1,'BTC','ACA IC',False,0,1)
    d.fixed_teachers['C','Toán']='A'
    r=solve_for_display(d)
    assert r.sessions[0].volunteer=='A'
    assert not r.leads and r.issues


def test_specialist_is_hard_international_is_soft_and_persisted():
    d=example()
    d.sites={}
    d.volunteers['S']=replace(d.volunteers['V'],id='S')
    d.specialist_teachers['C','Toán']=frozenset({'S'})
    assert not eligible(d,'V','C','Toán') and eligible(d,'S','C','Toán')
    d.international_children={'C'}
    d.international_teachers={'V'}
    assert solve(d).sessions[0].volunteer=='S'
    assert read_workbook(export_workbook(d))==d
    d.specialist_teachers={}
    assert solve(d).sessions[0].volunteer=='V'


def test_lead_twice_can_only_teach_once_and_site1_teaching_requires_lead():
    d=example()
    d.children['D']=replace(d.children['C'],id='D')
    d.demands.append(Demand('D','Toán'))
    d.sites['s']=replace(d.sites['s'],required_days=frozenset(DAYS[:2]),aca_teach_only_when_leading=True)
    for vid in ('A','B'):
        d.volunteers[vid]=Volunteer(vid,frozenset({('Toán',3)}),frozenset(DAYS[:2]),1,'BTC','ACA IC',True,2,2)
    r=solve(d)
    assert sum(len(lead_ids(r,'s',day)) for day in DAYS)==4
    for vid in ('A','B'):
        assert sum(s.volunteer==vid for s in r.sessions)<=1
        for s in r.sessions:
            if s.volunteer==vid: assert vid in lead_ids(r,'s',s.day)
