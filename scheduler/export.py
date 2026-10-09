"""Export a schedule and reloadable input/decisions in one Excel file."""
from .models import DAYS, Dataset, Lock, Result
from .excel_io import input_tables, write_tables
from .explanations import unmet_demands
from .policies import session_site

HEADERS = ["Ngày", "Giờ", "TNV", "Môn", "Bé thứ nhất", "Bé thứ hai", "Trạng thái khóa"]

def timetable_grid(data: Dataset, result: Result, site: str) -> list[list]:
    """One child per row, weekdays in columns, with a daily lead footer."""
    kids = [c for c in data.children.values() if c.site == site]
    sessions = {(cid,s.day):s for s in result.sessions for cid in s.children if data.children[cid].site==site}
    rows = [["STT","18:00–20:00","Lớp",*DAYS]]
    for number,c in enumerate(kids,1):
        cells = []
        for day in DAYS:
            s = sessions.get((c.id,day))
            if s is None:
                cells.append("")
            else:
                flags = []
                if len(s.children)==2:flags.append("ghép")
                if result.leads.get((site,day))==s.volunteer:flags.append("lead")
                cells.append(f"{s.subject}\n{s.volunteer}" + (" · " + ", ".join(flags) if flags else ""))
        rows.append([number,c.source_id or c.id,c.grade,*cells])
    rows.append(["LEAD TEAM","","",*[result.leads.get((site,day),"") for day in DAYS]])
    missing=[c.source_id or c.id for c in kids if not any(d.child==c.id for d in data.demands)]
    note = "Mỗi ô ghi môn và người dạy. Ô có ‘ghép’ cùng người dạy, cùng ngày là một buổi hai bé."
    if missing:note += " Chưa có môn trong TKB nguồn: " + ", ".join(missing) + "."
    rows.append(["GHI CHÚ","","",note,"","","",""])
    return rows

def timetable_tables(data: Dataset, result: Result) -> dict[str,list[list]]:
    """Printable weekly timetable sheets precede detailed audit tables."""
    tables={}
    for site in data.sites:
        fulfilled=sum(len(s.children) for s in result.sessions if session_site(data,s)==site)
        total=sum(data.children[d.child].site==site for d in data.demands)
        title=site.replace('_',' ').upper()
        tables['TKB_'+site]=[[f'THỜI KHÓA BIỂU — {title}',*['']*7],
                            [(('BẢN TẠM · ' if result.issues else '') + f'Thứ Hai–Thứ Sáu · 18:00–20:00 · Đáp ứng {fulfilled}/{total} nhu cầu bé–môn'),*['']*7],
                            *timetable_grid(data,result,site)]
    return tables

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
        tables["Yeu_cau_chua_dat"] = [["Yêu cầu chưa đáp ứng"], *[[issue] for issue in result.issues]]
        if data.sites:
            for site in data.sites:
                tables["Lich_" + site] = [headers, *[list(r.values()) for r in rows if r["Mái ấm"] == site]]
            tables["Lead_team"] = [["Mái ấm", "Ngày", "BTC ACA IC", "Trực tiếp dạy"], *[[site, day, vid, "Có" if any(s.volunteer==vid and s.day==day and session_site(data,s)==site for s in result.sessions) else "Không"] for (site, day), vid in result.leads.items()]]
            tables={**timetable_tables(data,result),**tables}
    return write_tables(tables)
