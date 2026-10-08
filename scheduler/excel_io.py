"""Read, normalize and validate the documented workbook schema."""
from io import BytesIO
from pathlib import Path
import unicodedata
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from .models import CATALOG, DAYS, Child, Dataset, DataError, Demand, Lock, Volunteer, SitePolicy, level

SCHEMA = {
    "TNV": ["Ma_TNV", "Mon", "Lop", "Gioi_han_buoi"],
    "Lich_ranh_TNV": ["Ma_TNV", "Ngay"],
    "Be": ["Ma_be", "Tuoi", "Lop", "Ngay_ranh"],
    "Nhu_cau_be": ["Ma_be", "Mon"],
    "Insight_be": ["Ma_be", "Ghi_chu"],
    "Interview_TNV": ["Cau_hoi"],
    "Cap_be_xung_khac": ["Ma_be_1", "Ma_be_2"],
    "Danh_gia_ghep": ["Ma_TNV", "Ma_be", "Trang_thai"],
    "Lua_chon_da_khoa": ["Ma_TNV", "Ma_be", "Mon", "Ngay"],
}

def text(value: object) -> str:
    return "" if value is None else str(value).strip()

def normalized(value: object) -> str:
    return unicodedata.normalize("NFC", text(value)).casefold()

def merged_cell_value(sheet, row: int, column: int) -> object:
    """Read a source cell using its merged anchor; never fill unrelated blanks."""
    cell = sheet.cell(row, column)
    for area in sheet.merged_cells.ranges:
        if cell.coordinate in area:
            return sheet.cell(area.min_row, area.min_col).value
    return cell.value

def subject(value: object) -> str:
    aliases = {normalized(s): s for subjects in CATALOG.values() for s in subjects}
    aliases.update({"anh": "Tiếng Anh", "văn": "Ngữ văn", "khtn": "Khoa học tự nhiên",
                    "lý": "Vật lý", "vật lí": "Vật lý", "hóa": "Hóa học", "hoá": "Hóa học", "hoá học": "Hóa học", "sinh": "Sinh học", "sử": "Lịch sử"})
    key = normalized(value)
    if key not in aliases:
        raise DataError(f"Môn học không hợp lệ: {value!r}.")
    return aliases[key]

def day(value: object) -> str:
    aliases = {normalized(d): d for d in DAYS}
    aliases.update({str(i + 2): d for i, d in enumerate(DAYS)})
    if normalized(value) not in aliases:
        raise DataError(f"Ngày không hợp lệ: {value!r}. Dùng Thứ Hai đến Thứ Sáu hoặc 2–6.")
    return aliases[normalized(value)]

def integer(value: object, low: int, high: int) -> int:
    try:
        number = float(value)
        if not number.is_integer() or not low <= number <= high:
            raise ValueError
        return int(number)
    except (ValueError, TypeError, OverflowError):
        raise DataError(f"Giá trị {value!r} phải là số nguyên từ {low} đến {high}.") from None

def read_workbook(source: bytes | Path | str) -> Dataset:
    """Parse workbook; errors name the sheet and row where possible."""
    try:
        wb = load_workbook(BytesIO(source) if isinstance(source, bytes) else source, data_only=False)
    except Exception as exc:
        raise DataError("Không đọc được file .xlsx. Hãy kiểm tra file và thử lại.") from exc
    tables = {}
    for name, required in SCHEMA.items():
        if name not in wb.sheetnames:
            raise DataError(f"Thiếu sheet {name}.")
        rows = list(wb[name].values)
        headers = [text(v) for v in rows[0]] if rows else []
        if not set(required) <= set(headers) or len(headers) != len(set(headers)):
            raise DataError(f"Sheet {name}: cần cột {', '.join(required)} và không được trùng tên cột.")
        tables[name] = [(idx, dict(zip(headers, row))) for idx, row in enumerate(rows[1:], 2)
                        if any(text(v) for v in row)]
    context = ""
    def rows(name: str):
        nonlocal context
        for idx, row in tables[name]:
            context = f"Sheet {name}, hàng {idx}: "
            yield row
    def reference(value: object, mapping: dict, kind: str) -> str:
        key = text(value)
        if key not in mapping:
            raise DataError(f"Mã {kind} {key!r} không tồn tại.")
        return key
    try:
        allow_group_sessions = True
        settings = {}
        if "Cau_hinh" in wb.sheetnames:
            config_rows = list(wb["Cau_hinh"].values)
            if not config_rows or list(config_rows[0][:2]) != ["Tham_so", "Gia_tri"]:
                raise DataError("Sheet Cau_hinh: cần cột Tham_so, Gia_tri.")
            for row in config_rows[1:]:
                if not row[0]: continue
                if text(row[0]) in settings:
                    raise DataError("Sheet Cau_hinh: tham số bị trùng.")
                settings[text(row[0])] = text(row[1])
            mode = settings.get("Che_do_lop", "Cho phép ghép hai bé")
            if mode not in ("Chỉ 1:1", "Cho phép ghép hai bé"):
                raise DataError("Sheet Cau_hinh: Che_do_lop phải là Chỉ 1:1 hoặc Cho phép ghép hai bé.")
            allow_group_sessions = mode != "Chỉ 1:1"
        children = {}
        for r in rows("Be"):
            cid = text(r["Ma_be"])
            if not cid or cid in children:
                raise DataError("Mã bé trống hoặc trùng.")
            days = frozenset(day(d) for d in text(r["Ngay_ranh"]).split(";"))
            age = integer(r["Tuoi"], 1, 25) if text(r["Tuoi"]) else None
            children[cid] = Child(cid, age, integer(r["Lop"], 1, 12), days, text(r.get("Mai_am")))
        skills, limits, kinds, roles = {}, {}, {}, {}
        for r in rows("TNV"):
            vid = text(r["Ma_TNV"])
            if not vid:
                raise DataError("Mã TNV không được trống.")
            sub, grade = subject(r["Mon"]), integer(r["Lop"], 1, 12)
            if sub not in CATALOG[level(grade)]:
                raise DataError(f"Môn {sub} không thuộc danh mục lớp {grade}.")
            limit = 1 if not text(r["Gioi_han_buoi"]) else integer(r["Gioi_han_buoi"], 0, 5)
            if vid in limits and limits[vid] != limit:
                raise DataError(f"TNV {vid} có giới hạn buổi không thống nhất.")
            if (sub, grade) in skills.get(vid, set()):
                raise DataError("Đăng ký TNV–môn–lớp bị trùng.")
            skills.setdefault(vid, set()).add((sub, grade))
            limits[vid] = limit
            kind = text(r.get("Loai")) or "TNV"
            role = text(r.get("Vai_tro"))
            if kind not in ("TNV", "BTC") or (vid in kinds and (kinds[vid], roles[vid]) != (kind, role)):
                raise DataError("Loại người dạy phải là TNV/BTC và vai trò phải thống nhất giữa các hàng.")
            kinds[vid], roles[vid] = kind, role
        availability = {vid: set() for vid in skills}
        for r in rows("Lich_ranh_TNV"):
            vid = reference(r["Ma_TNV"], skills, "TNV")
            availability[vid].add(day(r["Ngay"]))
        volunteers = {vid: Volunteer(vid, frozenset(s), frozenset(availability[vid]), limits[vid], kinds[vid], roles[vid]) for vid, s in skills.items()}
        demands = []
        for r in rows("Nhu_cau_be"):
            cid = reference(r["Ma_be"], children, "bé")
            sub = subject(r["Mon"])
            if sub not in CATALOG[level(children[cid].grade)]:
                raise DataError(f"Môn {sub} không thuộc danh mục lớp của {cid}.")
            d = Demand(cid, sub)
            if d in demands:
                raise DataError(f"Nhu cầu {cid}–{sub} bị trùng.")
            demands.append(d)
        data = Dataset(volunteers, children, demands, allow_group_sessions=allow_group_sessions)
        tier_setting = settings.get("Uu_tien_nguon_luc", "Không")
        if tier_setting not in ("Có", "Không"):
            raise DataError("Cau_hinh.Uu_tien_nguon_luc phải là Có/Không.")
        data.prioritize_volunteers = tier_setting == "Có"
        if "Quy_tac_mai_am" in wb.sheetnames:
            site_rows = list(wb["Quy_tac_mai_am"].values)
            headers = [text(c) for c in site_rows[0]] if site_rows else []
            required = {"Mai_am", "Ghep_cap_1", "Can_lead_aca_ic", "Dung_lop_thay_tuoi"}
            if not required <= set(headers):
                raise DataError("Sheet Quy_tac_mai_am thiếu cột cấu hình.")
            for raw in site_rows[1:]:
                row = dict(zip(headers, raw))
                if not text(row.get("Mai_am")): continue
                flags = [text(row[k]) for k in ("Ghep_cap_1", "Can_lead_aca_ic", "Dung_lop_thay_tuoi")]
                if any(f not in ("Có", "Không") for f in flags) or row["Mai_am"] in data.sites:
                    raise DataError("Quy_tac_mai_am: mã bị trùng hoặc giá trị không phải Có/Không.")
                required_days = frozenset(day(d) for d in text(row.get("Ngay_hoc_bat_buoc")).split(";") if d.strip())
                must_teach = text(row.get("Lead_bat_buoc_day")) or "Có"
                if must_teach not in ("Có","Không"):
                    raise DataError("Lead_bat_buoc_day phải là Có/Không.")
                data.sites[text(row["Mai_am"])] = SitePolicy(*(f == "Có" for f in flags), required_days=required_days, lead_must_teach=must_teach=="Có")
            if any(c.site not in data.sites for c in children.values()):
                raise DataError("Mỗi bé phải có Mai_am và mái ấm đó phải có trong Quy_tac_mai_am.")
        for r in rows("Cap_be_xung_khac"):
            a, b = (reference(r[col], children, "bé") for col in ("Ma_be_1", "Ma_be_2"))
            if a == b:
                raise DataError("Cặp xung khắc phải gồm hai bé khác nhau.")
            data.conflicts.add(frozenset((a, b)))
        for r in rows("Danh_gia_ghep"):
            key = (reference(r["Ma_TNV"], volunteers, "TNV"), reference(r["Ma_be"], children, "bé"))
            state = text(r["Trang_thai"])
            if state not in ("Ưu tiên", "Bình thường", "Không ghép") or key in data.ratings:
                raise DataError("Đánh giá trùng cặp hoặc trạng thái không hợp lệ.")
            data.ratings[key] = state
        for r in rows("Lua_chon_da_khoa"):
            lock = Lock(reference(r["Ma_TNV"], volunteers, "TNV"), reference(r["Ma_be"], children, "bé"), subject(r["Mon"]), day(r["Ngay"]))
            if lock in data.locks:
                raise DataError("Lựa chọn khóa bị trùng.")
            data.locks.add(lock)
        for r in rows("Insight_be"):
            cid = reference(r["Ma_be"], children, "bé")
            data.insights[cid] = "\n".join(filter(None, (data.insights.get(cid), text(r["Ghi_chu"]))))
        interview_headers = [text(c.value) for c in wb["Interview_TNV"][1]]
        for vid in interview_headers:
            if vid != "Cau_hoi":
                reference(vid, volunteers, "TNV")
        for r in rows("Interview_TNV"):
            for vid, answer in r.items():
                if vid != "Cau_hoi" and text(answer):
                    if not text(r["Cau_hoi"]):
                        raise DataError("Câu trả lời phải có câu hỏi tương ứng.")
                    data.interviews.setdefault(vid, []).append((text(r["Cau_hoi"]), text(answer)))
        if not children or not volunteers or not demands:
            raise DataError("Cần ít nhất một TNV, một bé và một nhu cầu.")
        return data
    except DataError as exc:
        raise DataError(context + str(exc)) from exc

def input_tables(data: Dataset) -> dict[str, list[list]]:
    """Serialize the current human decisions for a reloadable workbook."""
    tables = {name: [headers.copy()] for name, headers in SCHEMA.items()}
    tables["Cau_hinh"] = [["Tham_so", "Gia_tri"], ["Che_do_lop", "Cho phép ghép hai bé" if data.allow_group_sessions else "Chỉ 1:1"]]
    tables["Cau_hinh"].append(["Uu_tien_nguon_luc", "Có" if data.prioritize_volunteers else "Không"])
    tables["TNV"][0] += ["Loai", "Vai_tro"]
    tables["Be"][0].append("Mai_am")
    if data.sites:
        tables["Quy_tac_mai_am"] = [["Mai_am", "Ghep_cap_1", "Can_lead_aca_ic", "Dung_lop_thay_tuoi", "Ngay_hoc_bat_buoc", "Lead_bat_buoc_day"],
            *[[site, "Có" if p.allow_primary_pairs else "Không", "Có" if p.require_academic_lead else "Không", "Có" if p.pair_by_grade else "Không", ";".join(d for d in DAYS if d in p.required_days), "Có" if p.lead_must_teach else "Không"] for site, p in data.sites.items()]]
    for v in data.volunteers.values():
        tables["TNV"].extend([v.id, s, g, v.max_sessions, v.kind, v.role] for s, g in sorted(v.skills))
        tables["Lich_ranh_TNV"].extend([v.id, d] for d in DAYS if d in v.days)
    tables["Be"].extend([c.id, c.age, c.grade, ";".join(d for d in DAYS if d in c.days), c.site] for c in data.children.values())
    tables["Nhu_cau_be"].extend([d.child, d.subject] for d in data.demands)
    tables["Insight_be"].extend([cid, note] for cid, note in data.insights.items())
    tables["Cap_be_xung_khac"].extend(sorted(pair) for pair in sorted(data.conflicts, key=lambda p: sorted(p)))
    tables["Danh_gia_ghep"].extend([v, c, state] for (v, c), state in sorted(data.ratings.items()))
    tables["Lua_chon_da_khoa"].extend([l.volunteer, l.child, l.subject, l.day] for l in sorted(data.locks, key=repr))
    vids = sorted(data.volunteers)
    questions = list(dict.fromkeys(q for answers in data.interviews.values() for q, _ in answers))
    tables["Interview_TNV"] = [["Cau_hoi", *vids]]
    for q in questions:
        tables["Interview_TNV"].append([q, *["\n".join(a for question, a in data.interviews.get(v, []) if question == q) for v in vids]])
    return tables

def write_tables(tables: dict[str, list[list]]) -> bytes:
    """Application runtime export; preserve user text as text, never formulas."""
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in tables.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
        for row in ws:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="234E70")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column in ws.columns:
            ws.column_dimensions[column[0].column_letter].width = min(55, max(18, max(len(text(c.value)) for c in column) + 2))
    output = BytesIO()
    wb.save(output)
    return output.getvalue()
