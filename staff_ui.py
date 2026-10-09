"""Vietnamese staff management controls for the local web app."""
from pathlib import Path
import pandas as pd
import streamlit as st
from scheduler.models import CATALOG, DAYS, DataError, level
from scheduler.staff_editing import staff_member, remove_staff, skills_from_blocks, skills_summary, GRADE_BLOCKS, BLOCK_LABELS
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
    st.dataframe(pd.DataFrame([{"Mã": v.id, "Loại": v.kind, "Ban / vai trò": v.role, "Ngày rảnh": ", ".join(d for d in DAYS if d in v.days), "Buổi/tuần": v.max_sessions, "Môn theo khối": skills_summary(v.skills)} for v in visible]), hide_index=True, width="stretch")
    selected = st.selectbox("Người cần chỉnh sửa", ["Thêm người mới"] + [v.id for v in visible], key="staff_selected")
    person = data.volunteers.get(selected)
    if person:
        excluded = {(subject, grade) for vid, subject, grade in data.skill_exclusions if vid == person.id}
        if excluded:
            st.info("Ngoại lệ chuyên môn — không phân công: " + skills_summary(excluded))
    revision = st.session_state.revision
    prefix = f"staff_{selected}_{revision}"
    with st.form(prefix):
        identifier = st.text_input("Mã người dạy", value=person.id if person else "", disabled=person is not None)
        kind = st.selectbox("Loại người dạy", ["TNV", "BTC"], index=1 if person and person.kind == "BTC" else 0)
        role = st.text_input("Ban / vai trò BTC (ACA IC, WF IC, PR IC…)", value=person.role if person else "")
        days = st.multiselect("Ngày rảnh", DAYS, default=[d for d in DAYS if person and d in person.days])
        limit = st.number_input("Số buổi tối đa mỗi tuần", min_value=0, max_value=2, value=min(person.max_sessions, 2) if person else 1, step=1)
        st.caption("ACA IC tối đa 1 buổi, gồm cả buổi chỉ làm lead. TNV và BTC ban khác tối đa 2 buổi.")
        st.markdown("**Môn có thể dạy theo khối**")
        selected_subjects = {}
        for column, block in zip(st.columns(3), GRADE_BLOCKS):
            with column:
                defaults = sorted({s for s, g in person.skills if level(g) == block}) if person else []
                selected_subjects[block] = st.multiselect(BLOCK_LABELS[block], sorted(CATALOG[block]), default=defaults)
        whole_blocks = False
        if person:
            whole_blocks = st.checkbox("Cho phép dạy toàn bộ lớp trong các khối đã chọn", value=False)
            st.caption("Môn đã có giữ giới hạn lớp hiện tại. Môn mới chọn áp dụng cho toàn khối; tích ô trên để mở rộng cả môn đã có.")
        else:
            st.caption("Môn được chọn áp dụng cho toàn bộ lớp trong khối đó.")
        if st.form_submit_button("Lưu thay đổi người dạy" if person else "Thêm người dạy", type="primary"):
            try:
                if person is None and identifier.strip() in data.volunteers:
                    raise DataError("Mã này đã tồn tại. Hãy chọn người đó để sửa.")
                skills = skills_from_blocks(selected_subjects, person.skills if person else frozenset(), whole_blocks)
                updated = staff_member(identifier, kind, role, skills, days, int(limit))
                data.volunteers[updated.id] = updated
                changed()
                st.session_state.staff_notice = f"Đã lưu {updated.id}."
                st.rerun()
            except DataError as exc:
                st.error(str(exc))
    if person:
        st.caption("Xóa người này sẽ gỡ cả đánh giá, thông tin phỏng vấn và buổi khóa liên quan. Bạn cần xếp lại thời khóa biểu.")

        def delete_selected():
            remove_staff(data, person.id)
            changed()
            # The old timetable contains references to the deleted staff member.
            st.session_state.result = None
            st.session_state.stale = False
            st.session_state.staff_selected = "Thêm người mới"
            st.session_state.staff_notice = f"Đã xóa {person.id}. Hãy xếp lại thời khóa biểu."

        st.button("Xóa người được chọn", key=f"delete_{person.id}", on_click=delete_selected)
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
        st.success("Đã lưu dữ liệu trên máy. Lần sau chọn Dữ liệu đã lưu trên máy để tiếp tục.")
        st.caption(f"File đã lưu: {target}")
