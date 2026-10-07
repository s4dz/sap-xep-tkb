# Kết quả kiểm chứng

Ngày kiểm chứng: 07/10/2026.

- Python 3.12.14, OR-Tools 9.15.6755, Streamlit 1.65.0.
- Toàn bộ 34 kiểm thử vượt qua.
- Luồng giao diện kiểm chứng bằng Streamlit AppTest: tải dữ liệu mẫu, xếp lịch, khóa thêm buổi, xếp lại giữ khóa, đánh giá cấm cặp đang khóa và hiển thị lỗi.
- Luồng Excel kiểm chứng: đọc workbook mẫu → xếp lịch → xuất kết quả → đọc lại đầy đủ dữ liệu và quyết định thủ công.
- Dữ liệu mẫu: 6 TNV, 9 bé, 14 nhu cầu. Phương án tối ưu xếp 6 bé, đáp ứng 7 nhu cầu trong 7 buổi một bé; 3 bé chưa có buổi và 7 nhu cầu chưa đáp ứng. Một bé có hai môn. Khóa ban đầu được giữ.
- Các giá trị mục tiêu lần lượt: 6 bé, 7 nhu cầu, 3 lựa chọn ưu tiên, 0 buổi hai bé, tổng bình phương tải TNV bằng 9.
- Đã render và kiểm tra trực quan cả 9 sheet của workbook mẫu: tiêu đề, nội dung, mã, tuổi/lớp và ma trận phỏng vấn đọc được.
- Máy chủ Streamlit local khởi động thành công; điểm kiểm tra hoạt động trả HTTP 200.

Kiểm thử tự động không thay thế thử nghiệm với dữ liệu thực tế. Chưa đo hiệu năng trên tập dữ liệu lớn và chưa chạy luồng tương tác trực tiếp trong trình duyệt.
