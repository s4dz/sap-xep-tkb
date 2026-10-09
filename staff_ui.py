"""Vietnamese staff management controls for the local web app."""
from pathlib import Path
import pandas as pd
import streamlit as st
from scheduler.models import CATALOG, DAYS, DataError, level
from scheduler.staff_editing import staff_member
from scheduler.export import export_workbook


def render_staff(data, changed):
    st.subheader("Quản lý TNV và BTC")
    st.caption("Chọn người để sửa hoặc thêm người mới. Đặt 0 buổi để tạm ngưng; các buổi đã khóa được giữ và sẽ được kiểm tra khi xếp lại.")
    people = list(data.volunteers.values())
    active = [v for v in people if v.max_sessions > 0 and v.days]
    tnv = [v for v in active if v.kind == "TNV"]
    cols = st.columns(4)
    cols[0].metric("TNV đang tham gia", len(tnv))
    cols[1].metric("TNV có thể đi 2 buổi", sum(min(v.max_sessions, len(v.days)) >= 2 for v in tnv))
    cols[2].metric("Ca TNV tối đa", sum(min(v.max_sessions, len(v.days)) for v in tnv))
    cols[3].metric("BTC đang tham gia", sum(v.kind == "BTC" for v in active))
    st.caption("Số ca tối đa dựa trên ngày rảnh và giới hạn tuần; khả năng đáp ứng còn phụ thuộc môn, lớp và lead team.")
    search = st.text_input("Tìm theo mã hoặc ban", key="staff_search").strip().casefold()
    group = st.radio("Danh sách", ["Tất cả", "TNV", "BTC"], horizontal=True)
    visible = [v for v in people if (group == "Tất cả" or v.kind == group) and (not search or search in (v.id + " " + v.role).casefold())]
    st.dataframe(pd.DataFrame([{"Mã": v.id, "Loại": v.kind, "Ban / vai trò": v.role, "Ngày rảnh": ", ".join(d for d in DAYS if d in v.days), "Buổi/tuần": v.max_sessions, "Môn và lớp": "; ".join(f"{s} lớp {g}" for s, g in sorted(v.skills, key=lambda x: (x[1], x[0])))} for v in visible]), hide_index=True, width="stretch")
    selected = st.selectbox("Người cần chỉnh sửa", ["Thêm người mới"] + [v.id for v in visible], key="staff_selected")
    person = data.volunteers.get(selected)
    revision = st.session_state.revision
    prefix = f"staff_{selected}_{revision}"
    # Grade-specific choices avoid silently broadening teaching qualifications.
    choices = {f"Lớp {g} · {s}": (s, g) for g in range(1, 13) for s in sorted(CATALOG[level(g)])}
    with st.form(prefix):
        identifier = st.text_input("Mã người dạy", value=person.id if person else "", disabled=person is not None)
        kind = st.selectbox("Loại người dạy", ["TNV", "BTC"], index=1 if person and person.kind == "BTC" else 0)
        role = st.text_input("Ban / vai trò BTC (ACA IC, WF IC, PR IC…)", value=person.role if person else "")
        days = st.multiselect("Ngày rảnh", DAYS, default=[d for d in DAYS if person and d in person.days])
        limit = st.number_input("Số buổi tối đa mỗi tuần", min_value=0, max_value=2, value=min(person.max_sessions, 2) if person else 1, step=1)
        st.caption("ACA IC tối đa 1 buổi, gồm cả buổi chỉ làm lead. TNV và BTC ban khác tối đa 2 buổi.")
        skills = st.multiselect("Môn và lớp có thể dạy", list(choices), default=[label for label, skill in choices.items() if person and skill in person.skills])
        if st.form_submit_button("Lưu thay đổi người dạy" if person else "Thêm người dạy", type="primary"):
            try:
                if person is None and identifier.strip() in data.volunteers:
                    raise DataError("Mã này đã tồn tại. Hãy chọn người đó để sửa.")
                updated = staff_member(identifier, kind, role, [choices[s] for s in skills], days, int(limit))
                data.volunteers[updated.id] = updated
                changed()
                st.session_state.staff_notice = f"Đã lưu {updated.id}."
                st.rerun()
            except DataError as exc:
                st.error(str(exc))
    if st.session_state.get("staff_notice"):
        st.success(st.session_state.pop("staff_notice"))
    st.subheader("Lưu để dùng lần sau")
    st.caption("Lưu trên máy này để mở lại với các thay đổi mới nhất. Bạn cũng có thể tải bản Excel ở cuối trang.")
    if st.button("Lưu dữ liệu trên máy này"):
        target = Path(__file__).parent / "data" / "private" / "du_lieu_dang_sua.xlsx"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = export_workbook(data)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        st.success("Đã lưu trên máy. Lần sau chọn Dữ liệu đã lưu trên máy để tiếp tục.")
