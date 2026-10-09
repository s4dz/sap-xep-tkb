from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from scheduler.models import DAYS, DataError, Lock, Result
from scheduler.staff_editing import staff_member
from scheduler.engine import validate_locks
from scheduler.excel_io import read_workbook
from scheduler.export import export_workbook
from scripts.sample_data import sample_data


def test_academic_cap_and_pause_roundtrip():
    with pytest.raises(DataError, match="1 buổi"):
        staff_member("ACA_NEW", "BTC", "ACA IC", [("Toán", 7)], DAYS, 2)
    data = sample_data()
    person = staff_member("ACA_NEW", "BTC", "ACA IC", [("Toán", 7)], [], 0)
    data.volunteers[person.id] = person
    assert read_workbook(export_workbook(data)).volunteers[person.id] == person


def test_staff_change_keeps_conflicting_lock_visible():
    data = sample_data()
    data.locks.add(Lock("TNV001", "BE001", "Toán", DAYS[0]))
    data.volunteers["TNV001"] = staff_member("TNV001", "TNV", "", [("Toán", 3)], [DAYS[4]], 1)
    with pytest.raises(DataError):
        validate_locks(data)
    assert len(data.locks) == 1


def test_staff_form_update_add_and_stale():
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30).run()
    next(s for s in app.selectbox if s.label == "Dữ liệu làm việc").set_value("Dữ liệu mẫu").run()
    next(s for s in app.selectbox if s.label == "Người cần chỉnh sửa").set_value("TNV001").run()
    app.session_state.result = Result([], True, [])
    next(m for m in app.multiselect if m.label == "Ngày rảnh").set_value([DAYS[4]])
    next(b for b in app.button if b.label == "Lưu thay đổi người dạy").click().run()
    assert not app.exception
    assert app.session_state.data.volunteers["TNV001"].days == frozenset([DAYS[4]])
    assert app.session_state.stale
    assert not any(d.label == "Tải kết quả Excel" for d in app.get("download_button"))
    next(s for s in app.selectbox if s.label == "Người cần chỉnh sửa").set_value("Thêm người mới").run()
    next(t for t in app.text_input if t.label == "Mã người dạy").set_value("TNV_NEW")
    next(m for m in app.multiselect if m.label == "Ngày rảnh").set_value([DAYS[0]])
    next(m for m in app.multiselect if m.label == "Môn và lớp có thể dạy").set_value(["Lớp 3 · Toán"])
    next(b for b in app.button if b.label == "Thêm người dạy").click().run()
    assert not app.exception
    data = app.session_state.data
    assert data.volunteers["TNV_NEW"].skills == frozenset([("Toán", 3)])
    assert read_workbook(export_workbook(data)).volunteers == data.volunteers
