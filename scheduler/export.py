"""Export a schedule and reloadable input/decisions in one Excel file."""
from .models import Dataset, Lock, Result
from .excel_io import input_tables, write_tables
from .explanations import unmet_demands

HEADERS = ["Ngày", "Giờ", "TNV", "Môn", "Bé thứ nhất", "Bé thứ hai", "Trạng thái khóa"]

def schedule_rows(data: Dataset, result: Result) -> list[dict]:
    rows = []
    for s in result.sessions:
        count = sum(Lock(s.volunteer, c, s.subject, s.day) in data.locks for c in s.children)
        state = "Đã khóa" if count == len(s.children) else "Khóa một phần" if count else "Chưa khóa"
        rows.append(dict(zip(HEADERS, [s.day, "18:00–20:00", s.volunteer, s.subject, s.children[0], s.children[1] if len(s.children) == 2 else "", state])))
    return rows

def export_workbook(data: Dataset, result: Result | None = None) -> bytes:
    tables = input_tables(data)
    if result is not None:
        unmet = unmet_demands(data, result)
        tables = {"Thoi_khoa_bieu": [HEADERS, *[list(r.values()) for r in schedule_rows(data, result)]],
                  "Chua_dap_ung": [["Mã bé", "Môn", "Bé chưa có buổi", "Lý do có thể"], *[list(r.values()) for r in unmet]],
                  "Tong_quan": [["Chỉ tiêu", "Giá trị"], ["Bé được xếp", len({c for s in result.sessions for c in s.children})],
                                ["Nhu cầu đáp ứng", sum(len(s.children) for s in result.sessions)],
                                ["Đã xác nhận phương án tối ưu", "Có" if result.optimal else "Chưa"]], **tables}
    return write_tables(tables)
