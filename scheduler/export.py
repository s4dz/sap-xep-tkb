"""Export a schedule and reloadable input/decisions in one Excel file."""
from .models import Dataset, Lock, Result
from .excel_io import input_tables, write_tables
from .explanations import unmet_demands
from .policies import session_site, pick_leads

HEADERS = ["Ngày", "Giờ", "TNV", "Môn", "Bé thứ nhất", "Bé thứ hai", "Trạng thái khóa"]

def schedule_rows(data: Dataset, result: Result) -> list[dict]:
    rows = []
    for s in result.sessions:
        count = sum(Lock(s.volunteer, c, s.subject, s.day) in data.locks for c in s.children)
        state = "Đã khóa" if count == len(s.children) else "Khóa một phần" if count else "Chưa khóa"
        row = dict(zip(HEADERS, [s.day, "18:00–20:00", s.volunteer, s.subject, s.children[0], s.children[1] if len(s.children) == 2 else "", state]))
        if data.sites:
            site = session_site(data, s)
            row = {("Người dạy" if key == "TNV" else key): value for key, value in row.items()}
            row = {"Mái ấm": site, **row, "Loại": data.volunteers[s.volunteer].kind,
                   "Lead team": "Có" if result.leads.get((site, s.day)) == s.volunteer else ""}
        rows.append(row)
    return rows

def export_workbook(data: Dataset, result: Result | None = None) -> bytes:
    tables = input_tables(data)
    if result is not None:
        unmet = unmet_demands(data, result)
        rows = schedule_rows(data, result)
        headers = list(rows[0]) if rows else (["Mái ấm", *["Người dạy" if h == "TNV" else h for h in HEADERS], "Loại", "Lead team"] if data.sites else HEADERS)
        tables = {"Thoi_khoa_bieu": [headers, *[list(r.values()) for r in rows]],
                  "Chua_dap_ung": [["Mã bé", "Môn", "Bé chưa có buổi", "Lý do có thể"], *[list(r.values()) for r in unmet]],
                  "Tong_quan": [["Chỉ tiêu", "Giá trị"], ["Bé được xếp", len({c for s in result.sessions for c in s.children})],
                                ["Nhu cầu đáp ứng", sum(len(s.children) for s in result.sessions)],
                                ["Đã xác nhận phương án tối ưu", "Có" if result.optimal else "Chưa"]], **tables}
        if data.sites:
            for site in data.sites:
                tables["Lich_" + site] = [headers, *[list(r.values()) for r in rows if r["Mái ấm"] == site]]
            tables["Lead_team"] = [["Mái ấm", "Ngày", "BTC ACA IC"], *[[site, day, vid] for (site, day), vid in result.leads.items()]]
    return write_tables(tables)
