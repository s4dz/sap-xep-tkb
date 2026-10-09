from scheduler.excel_io import read_workbook
from scheduler.export import export_workbook
from scheduler.models import Dataset, Volunteer, Child, Demand, DAYS
from scheduler.policies import teaching_skills
from scheduler.engine import candidates


def test_explicit_exclusion_overrides_chemistry_flexibility_and_roundtrips():
    data = Dataset(
        volunteers={"TNV034": Volunteer("TNV034", frozenset({("Hóa học", 12), ("Toán", 9)}), frozenset(DAYS), 2)},
        children={"BE1": Child("BE1", None, 12, frozenset(DAYS))},
        demands=[Demand("BE1", "Vật lý")], flexible_science=True,
        skill_exclusions={("TNV034", "Vật lý", g) for g in (10, 11, 12)},
    )
    assert ("Hóa học", 12) in teaching_skills(data, "TNV034")
    assert ("Toán", 9) in teaching_skills(data, "TNV034")
    assert ("Vật lý", 12) not in teaching_skills(data, "TNV034")
    assert not candidates(data)
    restored = read_workbook(export_workbook(data))
    assert restored.skill_exclusions == data.skill_exclusions
    assert not candidates(restored)
