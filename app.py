"""Vietnamese local Streamlit interface."""
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from scheduler.models import DataError, Lock
from scheduler.excel_io import read_workbook
from scheduler.engine import solve, validate_locks, eligible
from scheduler.export import export_workbook, schedule_rows, HEADERS
from scheduler.explanations import unmet_demands

st.set_page_config(page_title="Sắp xếp thời khóa biểu", page_icon="📅", layout="wide")
st.title("Sắp xếp thời khóa biểu")
st.caption("Tình nguyện viên và các bé · Thứ Hai–Thứ Sáu · 18:00–20:00")
st.write("Tải dữ liệu, duyệt các cặp phù hợp, rồi xếp lịch. Những lựa chọn đã khóa sẽ được giữ khi xếp lại.")
sample = Path(__file__).parent / "data" / "du_lieu_mau.xlsx"
st.download_button("Tải file mẫu", sample.read_bytes(), "du_lieu_mau.xlsx")
uploaded = st.file_uploader("Tải lên file Excel", type=["xlsx"])
use_sample = st.checkbox("Dùng dữ liệu mẫu", value=uploaded is None)
raw = uploaded.getvalue() if uploaded else sample.read_bytes() if use_sample else None
if raw is None:
    st.info("Tải lên file Excel hoặc chọn dùng dữ liệu mẫu để bắt đầu.")
    st.stop()
fingerprint = hashlib.sha256(raw).hexdigest()
if st.session_state.get("fingerprint") != fingerprint:
    try:
        data = read_workbook(raw)
    except DataError as exc:
        st.error(str(exc))
        st.stop()
    st.session_state.data = data
    st.session_state.fingerprint = fingerprint
    st.session_state.result = None
    st.session_state.stale = False
    st.session_state.revision = 0
data = st.session_state.data
if not data.sites:
    st.caption("Chế độ lớp: " + ("Cho phép ghép hai bé cùng tuổi" if data.allow_group_sessions else "Chỉ dạy 1:1") + ". Bé chưa có tuổi chỉ được xếp 1:1.")
if data.sites:
    st.info("Áp dụng quy tắc riêng từng mái ấm. ACA IC làm lead theo từng ngày; mái ấm yêu cầu lead dạy sẽ kiểm tra cả lớp được phân công. Buổi chỉ làm lead vẫn tính vào giới hạn tuần và được kiểm tra trùng lịch giữa hai mái ấm.")
columns = st.columns(3)
for col, label, value in zip(columns, ["Người dạy" if data.sites else "Tình nguyện viên", "Bé", "Nhu cầu môn học"], [len(data.volunteers), len(data.children), len(data.demands)]):
    col.metric(label, value)
with st.expander("Xem dữ liệu đầu vào"):
    st.dataframe(pd.DataFrame([{"Mã người dạy": v.id, "Loại": v.kind, "Vai trò": v.role, "Môn và lớp": "; ".join(f"{s} lớp {g}" for s, g in sorted(v.skills)), "Ngày rảnh": "; ".join(sorted(v.days)), "Giới hạn buổi": v.max_sessions} for v in data.volunteers.values()]), hide_index=True)
    st.dataframe(pd.DataFrame([{"Mã bé": c.id, "Mái ấm": c.site, "Tuổi": c.age if c.age is not None else "Chưa cung cấp", "Lớp": c.grade, "Ngày rảnh": "; ".join(sorted(c.days)), "Môn cần học": "; ".join(d.subject for d in data.demands if d.child == c.id)} for c in data.children.values()]), hide_index=True)

def changed() -> None:
    st.session_state.stale = st.session_state.result is not None
    st.session_state.revision += 1

review, schedule = st.tabs(["Duyệt cặp và lựa chọn khóa", "Thời khóa biểu"])
with review:
    left, right = st.columns(2)
    vid = left.selectbox("Người dạy" if data.sites else "Tình nguyện viên", sorted(data.volunteers))
    cid = right.selectbox("Bé", sorted(data.children))
    left.subheader("Thông tin phỏng vấn")
    for question, answer in data.interviews.get(vid, []):
        left.markdown(f"**{question}**")
        left.write(answer)
    if not data.interviews.get(vid):
        left.caption("Chưa có câu trả lời.")
    right.subheader("Ghi chú về bé")
    right.write(data.insights.get(cid) or "Chưa có ghi chú.")
    possible = [d.subject for d in data.demands if d.child == cid and eligible(data, vid, cid, d.subject)]
    st.caption("Môn và lớp phù hợp hiện tại: " + (", ".join(possible) or "Không có") + ". Ghi chú chỉ dùng để tham khảo khi duyệt.")
    states = ["Ưu tiên", "Bình thường", "Không ghép"]
    with st.form("rating"):
        state = st.radio("Đánh giá cặp", states, index=states.index(data.ratings.get((vid, cid), "Bình thường")), horizontal=True, key=f"rating_{vid}_{cid}_{st.session_state.revision}")
        if st.form_submit_button("Lưu đánh giá"):
            data.ratings[vid, cid] = state
            changed()
            st.rerun()
    st.subheader("Lựa chọn đã khóa")
    for lock in sorted(data.locks, key=repr):
        cols = st.columns([5, 1])
        cols[0].write(f"{lock.day} · {lock.volunteer} · {lock.child} · {lock.subject}")
        if cols[1].button("Bỏ khóa", key=f"remove_{lock}"):
            data.locks.remove(lock)
            changed()
            st.rerun()
    if not data.locks:
        st.caption("Chưa có lựa chọn khóa. Bạn có thể khóa buổi sau khi xếp lịch.")

try:
    validate_locks(data)
    lock_error = None
except DataError as exc:
    lock_error = str(exc)
    st.error(lock_error)

with schedule:
    if st.button("Xếp lại, giữ lựa chọn khóa" if st.session_state.result else "Xếp thời khóa biểu", type="primary", disabled=bool(lock_error)):
        try:
            with st.spinner("Đang tìm lịch phù hợp…"):
                st.session_state.result = solve(data)
            st.session_state.stale = False
        except DataError as exc:
            st.error(str(exc))
    result = st.session_state.result
    if result:
        if st.session_state.stale:
            st.warning("Đánh giá hoặc khóa đã thay đổi. Hãy xếp lại để cập nhật kết quả trước khi tải lịch xuống.")
        if not result.optimal:
            st.warning("Đã có lịch hợp lệ trong thời gian cho phép. Phương án có thể còn cải thiện; bạn có thể xếp lại.")
        served = {c for s in result.sessions for c in s.children}
        st.success(f"Đã xếp {len(served)}/{len(data.children)} bé, đáp ứng {sum(len(s.children) for s in result.sessions)}/{len(data.demands)} nhu cầu.")
        display_rows = schedule_rows(data, result)
        if data.sites:
            for site in data.sites:
                st.subheader(site)
                site_rows = [r for r in display_rows if r["Mái ấm"] == site]
                st.dataframe(pd.DataFrame(site_rows), hide_index=True, width="stretch")
        else:
            st.dataframe(pd.DataFrame(display_rows, columns=HEADERS), hide_index=True, width="stretch")
        if result.leads:
            st.subheader("Lead team theo ngày")
            st.dataframe(pd.DataFrame([{"Mái ấm":site,"Ngày":day,"ACA IC":vid,"Trực tiếp dạy":"Có" if any(s.volunteer==vid and s.day==day and data.children[s.children[0]].site==site for s in result.sessions) else "Không"} for (site,day),vid in result.leads.items()]),hide_index=True)
        for idx, session in enumerate(result.sessions):
            keys = {Lock(session.volunteer, c, session.subject, session.day) for c in session.children}
            fully_locked = keys <= data.locks
            label = "Bỏ khóa buổi" if fully_locked else "Khóa toàn bộ buổi"
            if st.button(f"{label}: {session.day} · {session.volunteer} · {', '.join(session.children)} · {session.subject}", key=f"lock_{idx}_{st.session_state.revision}", disabled=st.session_state.stale):
                if fully_locked:
                    data.locks.difference_update(keys)
                else:
                    data.locks.update(keys)
                changed()
                st.rerun()
        st.subheader("Bé chưa được xếp")
        st.write(", ".join(sorted(set(data.children) - served)) or "Tất cả các bé đã có ít nhất một buổi.")
        st.subheader("Nhu cầu chưa được đáp ứng")
        unmet = unmet_demands(data, result)
        if unmet:
            st.dataframe(pd.DataFrame(unmet), hide_index=True, width="stretch")
        else:
            st.write("Tất cả nhu cầu đã được đáp ứng.")
        if not st.session_state.stale:
            st.download_button("Tải kết quả Excel", export_workbook(data, result), "thoi_khoa_bieu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.download_button("Lưu dữ liệu, đánh giá và khóa hiện tại", export_workbook(data), "du_lieu_da_duyet.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.caption("Các thay đổi được giữ trong phiên làm việc. Tải file dữ liệu đã duyệt để lưu lâu dài và tải lại ở lần sau.")
