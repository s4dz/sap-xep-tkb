from io import BytesIO
from pathlib import Path
import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest
from scheduler.models import DataError
from scheduler.excel_io import read_workbook, subject
from scheduler.engine import solve
from scheduler.export import export_workbook
from scheduler.explanations import unmet_demands
from scripts.sample_data import sample_data

def mutated(mutator):
    wb = load_workbook(BytesIO(export_workbook(sample_data())))
    mutator(wb)
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()

def test_sample_roundtrip_and_export():
    data = read_workbook(Path("data/du_lieu_mau.xlsx"))
    assert len(data.children) == 9 and len(data.volunteers) == 6
    assert len(data.interviews["TNV002"]) == 2
    result = solve(data)
    assert result.optimal
    assert unmet_demands(data, result)
    saved = export_workbook(data, result)
    reloaded = read_workbook(saved)
    assert reloaded == data
    assert "Thoi_khoa_bieu" in load_workbook(BytesIO(saved)).sheetnames

def test_aliases():
    assert subject(" Anh ") == "Tiếng Anh"
    assert subject("Văn") == "Ngữ văn"

@pytest.mark.parametrize("mutator", [lambda w: w.remove(w["Be"]),
    lambda w: setattr(w["Be"]["B2"], "value", 8.5),
    lambda w: setattr(w["Be"]["D2"], "value", "Chủ nhật"),
    lambda w: w["Nhu_cau_be"].append(["BE999", "Toán"]),
    lambda w: w["Nhu_cau_be"].append(["BE001", "Toán"]),
    lambda w: setattr(w["Danh_gia_ghep"]["C2"], "value", "Sai"),
    lambda w: setattr(w["TNV"]["D3"], "value", 4)])
def test_validation_messages(mutator):
    with pytest.raises(DataError):
        read_workbook(mutated(mutator))

def test_notes_exported_as_text_not_formulas():
    data = sample_data()
    data.insights["BE001"] = "=1+1"
    wb = load_workbook(BytesIO(export_workbook(data)))
    assert wb["Insight_be"]["B2"].data_type == "s"

def test_unmet_reasons():
    data = sample_data()
    rows = unmet_demands(data, solve(data))
    assert any(r["Mã bé"] == "BE008" and "đúng môn và lớp" in r["Lý do có thể"] for r in rows)
    assert any(r["Mã bé"] == "BE009" and "ngày rảnh chung" in r["Lý do có thể"] for r in rows)

def test_app_end_to_end():
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=30).run()
    next(s for s in app.selectbox if s.label == "Dữ liệu làm việc").set_value("Dữ liệu mẫu").run()
    assert not app.exception
    next(b for b in app.button if b.label == "Xếp thời khóa biểu").click().run()
    assert not app.exception
    assert app.session_state.result.optimal
    next(b for b in app.button if b.label.startswith("Khóa toàn bộ buổi")).click().run()
    locks = app.session_state.data.locks.copy()
    next(b for b in app.button if b.label == "Xếp lại, giữ lựa chọn khóa").click().run()
    assert not app.exception
    assert app.session_state.data.locks == locks
    next(r for r in app.radio if r.label == "Đánh giá cặp").set_value("Không ghép")
    next(b for b in app.button if b.label == "Lưu đánh giá").click().run()
    assert not app.exception
    assert app.error  # The sample's locked pair is now forbidden.
    assert app.session_state.stale
