# Kết quả kiểm chứng

Cập nhật ngày 09/10/2026:

- Toàn bộ 61 kiểm thử vượt qua sau bổ sung linh hoạt Hóa → Lý–Hóa–Sinh, nhận KHTN tổng hợp ở cấp 2, giữ đúng lớp đăng ký, ưu tiên BTC ban khác trước ACA IC, ưu tiên lớp ghép hợp lệ và xuất–tải lại ba cờ cấu hình mới.
- Bổ sung bảng thời khóa biểu theo tuần, mỗi bé một hàng và năm ngày thành cột, có hàng lead/ghi chú. Kiểm tra dữ liệu đối chiếu từng ô với danh sách buổi học, bảo toàn mã bé nguồn khi tải lại và kiểm tra trực quan cả hai trang TKB trong workbook kết quả.
- Sau bổ sung ACA IC làm lead ở cả hai mái ấm, toàn bộ 56 kiểm thử vượt qua. Bốn kiểm thử mới xác nhận lead không dạy không cần chuyên môn đứng lớp, buổi chỉ làm lead vẫn tiêu thụ giới hạn tuần, không trực hai mái ấm cùng ngày, dạy và lead tại cùng mái ấm chỉ tính một buổi, và mười vị trí lead dùng mười ACA IC khác nhau khi mỗi người chỉ đi một buổi.
- Đợt xếp với lead đủ hai mái ấm tiếp tục đáp ứng toàn bộ nhu cầu đã khai báo, với đủ mười phân công lead trong tuần. Workbook có bảng đối chiếu nhu cầu theo bé–môn, tách số buổi dạy và số buổi đi dạy/trực lead để kiểm tra giới hạn tuần.
- Sau sửa lỗi đọc nhóm vai trò trong ô gộp, toàn bộ 52 kiểm thử vượt qua. Bốn kiểm thử mới xác nhận vai trò áp dụng đủ mọi dòng trong vùng gộp, đủ năm ngày học với ACA IC trực tiếp dạy mỗi ngày, báo lỗi khi thiếu lead cho ngày bắt buộc và không trả lịch nền thiếu ngày khi hết thời gian.
- Phương án dữ liệu thực tế sau sửa lỗi đáp ứng toàn bộ nhu cầu đã khai báo; mái ấm cần lead có lớp và ACA IC trực tiếp dạy đủ năm ngày. Kiểm tra độc lập xác nhận tất cả vai trò BTC theo nhóm ô gộp, giới hạn một buổi của từng ACA IC, lịch riêng hai mái ấm và khả năng tải lại workbook.
- Toàn bộ 48 kiểm thử vượt qua. Chín kiểm thử mới xác nhận quy tắc riêng từng mái ấm, ghép cấp 1 theo lớp khi được cấu hình, ACA IC trực tiếp dạy và làm lead, giới hạn lead một buổi, thứ tự nguồn lực TNV/BTC, tránh trùng lịch liên mái ấm, kiểm tra khóa thiếu lead và xuất–tải lại cấu hình.
- Dữ liệu thực tế đã được xếp với cả bảy mục tiêu được chứng minh tối ưu. Kết quả được kiểm tra riêng về ngày rảnh, môn/lớp, giới hạn buổi, lịch trùng, lớp ghép, nhu cầu và lead; dữ liệu cùng kết quả chỉ lưu local trong thư mục bị Git bỏ qua.
- Toàn bộ 39 kiểm thử vượt qua, bao gồm 5 kiểm thử bổ sung cho chế độ chỉ 1:1, tuổi chưa cung cấp, xuất–tải lại cấu hình, khóa lớp hai bé bị từ chối và chuyên môn Lý/Hóa riêng biệt.
- Bổ sung ràng buộc tổng số bé được xếp không vượt số nhu cầu được đáp ứng, và dùng lời giải đã có làm gợi ý cho mục tiêu tiếp theo. Không thay đổi thứ tự tối ưu.
- Kiểm thử giao diện cần được chạy trong môi trường cho phép socket nội bộ của Streamlit; môi trường sandbox có thể chặn khởi tạo vòng lặp sự kiện.
- Các workbook dữ liệu thật và kết quả local nằm ngoài nội dung theo dõi của Git. Không ghi dữ liệu cá nhân vào tài liệu kiểm chứng này.

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
# Quản lý người dạy trên web

Quy tắc trường quốc tế, chuyên môn bắt buộc, người dạy cố định và nhiều lead mỗi ngày đã được kiểm tra. Bộ kiểm thử hiện có 75 kiểm tra thành công. Kiểm tra bổ sung trên dữ liệu đã lưu: đủ 78/78 nhu cầu; BTC012–be_g_1 và BTC013–be_g_4 được giữ; BTC013 không lead; tre_7 học Văn với chuyên Văn; TNV012 dạy be_g_5; 6/8 nhu cầu trường quốc tế được giao nhóm phù hợp (hai nhu cầu còn lại không có đăng ký chuyên môn trong nhóm). ACA ở mái ấm 1 không cần dạy; còn 3 vị trí lead thiếu do chỉ có tối đa 12 lượt cho yêu cầu 15 lượt.

Đã kiểm tra cập nhật ngày rảnh qua biểu mẫu, thêm TNV mới, lưu và đọc lại thông tin người dạy qua Excel, tạm ngưng người dạy và giới hạn một buổi của ACA IC. Sửa người dạy đánh dấu lịch cũ cần cập nhật và chặn tải kết quả cũ. Các khóa vẫn được giữ để báo mâu thuẫn nếu ngày rảnh hoặc môn dạy thay đổi. Bộ kiểm thử hiện có 64 kiểm tra thành công.

