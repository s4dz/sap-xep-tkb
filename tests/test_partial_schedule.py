from io import BytesIO
from pathlib import Path
import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest
from scheduler.models import DAYS, Dataset, Volunteer, Child, Demand, SitePolicy, Lock, DataError
from scheduler.engine import solve, solve_for_display
from scheduler.export import export_workbook


def no_lead_data():
    return Dataset(
        volunteers={"TNV1": Volunteer("TNV1", frozenset({("Toán", 7)}), frozenset({DAYS[0]}), 1)},
        children={"BE1": Child("BE1", None, 7, frozenset(DAYS), "mai_am_2")},
        demands=[Demand("BE1", "Toán"), Demand("BE1", "Tiếng Anh")],
        sites={"mai_am_2": SitePolicy(require_academic_lead=True, required_days=frozenset(DAYS), lead_must_teach=True)},
    )


def test_partial_classes_without_lead_keep_teaching_rules_and_export_gaps():
    data = no_lead_data()
    with pytest.raises(DataError):
        solve(data)
    result = solve_for_display(data)
    assert len(result.sessions) == 1
    assert result.sessions[0].subject == "Toán" and result.sessions[0].day == DAYS[0]
    assert not result.leads
    assert any("thiếu ACA IC" in issue for issue in result.issues)
    assert any("1/2" in issue for issue in result.issues)
    wb = load_workbook(BytesIO(export_workbook(data, result)))
    assert wb["TKB_mai_am_2"]["A2"].value.startswith("BẢN TẠM")
    assert wb["Yeu_cau_chua_dat"].max_row == len(result.issues) + 1


def test_partial_preview_ignores_invalid_locks_with_explicit_issue():
    data = no_lead_data()
    data.locks.add(Lock("TNV1", "BE1", "Tiếng Anh", DAYS[0]))
    result = solve_for_display(data)
    assert len(result.sessions) == 1 and result.sessions[0].subject == "Toán"
    assert any("không áp dụng các buổi khóa" in issue for issue in result.issues)
    assert data.locks  # Original decisions remain available for correction.


def test_partial_preview_ui_shows_and_exports_instead_of_error():
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30).run()
    app.session_state.data = no_lead_data()
    app.session_state.result = None
    app.run()
    next(b for b in app.button if b.label == "Xếp thời khóa biểu").click().run()
    assert not app.exception
    assert len(app.session_state.result.sessions) == 1
    assert any("THỜI KHÓA BIỂU TẠM" in w.value for w in app.warning)
    assert any(d.label == "Tải kết quả Excel" for d in app.get("download_button"))
