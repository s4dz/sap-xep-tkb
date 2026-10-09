# Sắp xếp thời khóa biểu

Ứng dụng Python chạy local, giao diện tiếng Việt, hỗ trợ tình nguyện viên (TNV) và các bé học từ Thứ Hai đến Thứ Sáu, 18:00–20:00. Dữ liệu mẫu hoàn toàn giả lập, chỉ dùng mã định danh. Không dùng LLM, API AI hoặc phân tích tính cách.

## Cài đặt và chạy trên Windows

1. Cài Python 3.11 trở lên (khuyến nghị 3.12), có Python Launcher `py`.
2. Mở thư mục `C:\Users\admin\Documents\Python\sap-xep-tkb`.
3. Nhấp đúp `run_app.bat`. Lần đầu cần mạng để tải thư viện. Những lần sau chạy hoàn toàn local.
4. Mở `http://127.0.0.1:8501` nếu trình duyệt chưa tự mở.
5. Đóng cửa sổ lệnh hoặc nhấn Ctrl+C để dừng ứng dụng.

Cài thủ công trong PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Môi trường `.venv` trên máy triển khai đã được cài thư viện. Các phiên bản thực tế được ghi trong `requirements-lock.txt`; có thể thay `requirements.txt` bằng tệp này để tái lập môi trường.

## Luồng sử dụng

1. Chọn **Dữ liệu làm việc** (dữ liệu hai mái ấm hiện tại, dữ liệu đã lưu trên máy hoặc dữ liệu mẫu) hoặc tải một file `.xlsx`. Lỗi cấu trúc và giá trị được báo kèm sheet/hàng.
2. Xem số TNV, bé, nhu cầu và bảng dữ liệu đầu vào.
3. Trong **Duyệt cặp và lựa chọn khóa**, chọn mã TNV và bé; xem câu hỏi/câu trả lời phỏng vấn và ghi chú; lưu **Ưu tiên / Bình thường / Không ghép**. Ghi chú không tác động tự động đến lịch.
4. Trong **Thời khóa biểu**, nhấn **Xếp thời khóa biểu**. Ứng dụng luôn hiển thị các ca xếp được, cả khi còn thiếu ngày học hoặc ACA lead. Lịch chưa đủ yêu cầu được ghi **BẢN TẠM** và vẫn tải được Excel với sheet **Yeu_cau_chua_dat**. Chuyên môn, ngày rảnh, giới hạn số buổi và điều kiện ghép vẫn được giữ. Nếu các khóa mâu thuẫn, bản tạm không áp dụng các khóa đó và báo rõ; quyết định khóa gốc được giữ để bạn sửa.
5. Khóa toàn bộ buổi đã duyệt hoặc bỏ khóa. Một khóa trong Excel là một TNV–bé–môn–ngày; buổi hai bé có thể có một phần khóa. Khóa từng lựa chọn có thể được bỏ trong khu vực duyệt.
6. Nhấn **Xếp lại, giữ lựa chọn khóa** sau khi thay đổi. Khi dữ liệu duyệt thay đổi, lịch cũ được đánh dấu cần cập nhật và không được tải xuống như lịch hiện hành.
7. **Tải kết quả Excel** chứa lịch, nhu cầu chưa đáp ứng, tổng quan và toàn bộ dữ liệu đầu vào. **Lưu dữ liệu, đánh giá và khóa hiện tại** dùng để lưu tiến độ kể cả khi các khóa đang mâu thuẫn. Tải lại một trong hai file này ở lần sử dụng sau.

Trong tab **TNV và BTC**, tìm người theo mã/ban, sửa ngày rảnh, môn theo từng lớp và số buổi tối đa; hoặc thêm người mới. Đặt **0 buổi** để tạm ngưng. ACA IC được tối đa một buổi (kể cả chỉ làm lead); TNV và BTC ban khác được tối đa hai buổi. Thay đổi làm lịch cũ cần cập nhật, nên hãy xếp lại trước khi tải kết quả.

Sheet tùy chọn **Ngoai_le_chuyen_mon** gồm `Ma_TNV`, `Mon`, `Lop`: ghi các môn/lớp người đó không thể dạy. Ngoại lệ được ưu tiên hơn quy tắc linh hoạt Hóa → KHTN, được giữ khi lưu/tải dữ liệu và hiện trong phần chỉnh sửa người dạy.

Nhấn **Lưu dữ liệu trên máy này** để lưu tiến độ tại `data/private/du_lieu_dang_sua.xlsx`. Lần mở sau ứng dụng ưu tiên bản đã lưu; dữ liệu gốc được giữ. File này được loại khỏi Git. Có thể tải bản Excel ở cuối trang để sao lưu hoặc chuyển sang máy khác. Thay nguồn dữ liệu sẽ bắt đầu phiên mới; hãy lưu trước khi chuyển nguồn hoặc đóng trang.

## Cấu trúc workbook

Hàng 1 chứa đúng tên cột. Một hàng là một bản ghi, trừ `Interview_TNV`. Mã là chuỗi không trống và phải tham chiếu mã đã khai báo; tên thật không cần thiết. Dấu `;` phân tách ngày rảnh của bé. Ngày chấp nhận `Thứ Hai`…`Thứ Sáu` hoặc `2`…`6`. Không chấp nhận cuối tuần.

| Sheet | Cột và ý nghĩa |
|---|---|
| `TNV` | `Ma_TNV`, `Mon`, `Lop`, `Gioi_han_buoi`. Mỗi hàng đăng ký một môn–lớp cụ thể. Lặp mã TNV để đăng ký nhiều môn/lớp. Giới hạn mặc định 1 khi trống, từ 0–5 và phải thống nhất giữa các hàng của cùng TNV. Muốn dạy cả cấp cần đăng ký từng lớp. |
| `Lich_ranh_TNV` | `Ma_TNV`, `Ngay`. Một hàng cho mỗi ngày rảnh. TNV không có dòng ngày rảnh sẽ không được xếp. |
| `Be` | **Sheet bổ sung**: `Ma_be`, `Tuoi`, `Lop`, `Ngay_ranh`. Một hàng/bé, tuổi nguyên 1–25, lớp 1–12. Ví dụ `Thứ Hai;Thứ Tư`. Tuổi dùng để kiểm tra điều kiện lớp ghép; lớp dùng để kiểm tra chuyên môn. |
| `Nhu_cau_be` | `Ma_be`, `Mon`. Một hàng/môn cần học, không trùng bé–môn. Mỗi nhu cầu tối đa một buổi/tuần. |
| `Insight_be` | `Ma_be`, `Ghi_chu`. Có thể có nhiều dòng, được nối khi hiển thị. |
| `Interview_TNV` | Cột đầu `Cau_hoi`; các cột tiếp theo là mã TNV. Mỗi hàng một câu hỏi. Câu trả lời trống được bỏ qua; câu trả lời có nội dung phải có câu hỏi. Có thể chỉ có cột của một số TNV. |
| `Cap_be_xung_khac` | `Ma_be_1`, `Ma_be_2`. Thứ tự mã không quan trọng; hai mã phải khác nhau. |
| `Danh_gia_ghep` | `Ma_TNV`, `Ma_be`, `Trang_thai`: `Ưu tiên`, `Bình thường`, `Không ghép`. Không khai báo tương đương Bình thường. Trạng thái áp dụng cho mọi môn của cặp. |
| `Lua_chon_da_khoa` | `Ma_TNV`, `Ma_be`, `Mon`, `Ngay`. Một hàng/lựa chọn. Hai khóa cùng TNV/ngày chỉ được gộp nếu cùng môn, cùng tuổi và không xung khắc. |

Sheet trống vẫn cần hàng tiêu đề. Sheet kết quả bổ sung được bỏ qua khi tải lại. Ô công thức trong các trường dữ liệu không được tính; dùng giá trị trực tiếp. Mã bé trong sheet `Be` không được trùng.

Danh mục: lớp 1–5 có Toán, Tiếng Việt, Tiếng Anh, Lịch sử và Khoa học; lớp 6–9 có Toán, Ngữ văn, Tiếng Anh, Khoa học tự nhiên, Vật lý, Hóa học, Sinh học; lớp 10–12 có Toán, Ngữ văn, Tiếng Anh, Vật lý, Hóa học, Sinh học. Các môn bổ sung theo dữ liệu hiện tại; không tự coi đăng ký Tiếng Việt là đăng ký Lịch sử, hoặc Lý/Hóa riêng là đủ chuyên môn toàn môn Khoa học tự nhiên. Chuẩn hóa khoảng trắng, chữ hoa/thường, Unicode và các bí danh `Anh`, `Văn`, `KHTN`, `Lý`, `Hoá`, `Sinh`, `Sử`. `Văn` là Ngữ văn, không thay thế Tiếng Việt cấp 1.

Sheet tùy chọn `Cau_hinh` có hai cột `Tham_so`, `Gia_tri`. Đặt `Che_do_lop` = `Chỉ 1:1` để cấm lớp hai bé; hoặc `Cho phép ghép hai bé` để dùng quy tắc ghép ban đầu. Khi không có sheet này, dùng quy tắc ban đầu. `Be.Tuoi` được phép trống; bé chưa có tuổi chỉ được xếp 1:1, không tự suy tuổi từ lớp. Chế độ lớp được giữ khi xuất–tải lại.

Với lịch nhiều mái ấm, bổ sung `Be.Mai_am`; sheet `Quy_tac_mai_am` gồm `Mai_am`, `Ghep_cap_1`, `Can_lead_aca_ic`, `Dung_lop_thay_tuoi`, với ba cờ Có/Không. Quy tắc mái ấm được dùng thay quy tắc ghép toàn cục. Ghép chỉ áp dụng cấp 1 cùng mái ấm; mặc định cần cùng tuổi đã biết. Chỉ bật `Dung_lop_thay_tuoi` khi đã đồng ý dùng cùng lớp làm điều kiện ghép tạm. Cặp không ghép vẫn được tôn trọng.

Sheet `TNV` được dùng chung cho người dạy, có thêm cột `Loai` (`TNV`/`BTC`) và `Vai_tro` (ví dụ `ACA IC`). Cột tùy chọn `Quy_tac_mai_am.Lead_bat_buoc_day` (Có/Không, mặc định Có) phân biệt lead phải trực tiếp dạy với lead chỉ cần có mặt. Mái ấm 1 cần ACA IC làm lead cả năm ngày nhưng không bắt buộc dạy; mái ấm 2 cần ACA IC trực tiếp dạy đúng môn/lớp và làm lead cả năm ngày. Một người không thể dạy hoặc trực lead ở hai mái ấm cùng ngày. Giới hạn tuần tính tổng số buổi đi trên cả hai mái ấm, kể cả buổi chỉ làm lead; dạy và lead cùng ngày cùng mái ấm tính một buổi. Với giới hạn một buổi/ACA IC, cần mười ACA IC khác nhau cho mười vị trí lead trong tuần.

Đặt `Cau_hinh.Uu_tien_nguon_luc` = `Có` để dùng thứ tự: tối đa bé → tối đa nhu cầu → ít buổi BTC → ít buổi bổ sung sau buổi đầu của TNV → đánh giá ưu tiên → ít lớp ghép → cân bằng tải. Điều này dùng TNV trước, buổi thứ hai của TNV trước BTC, cho cùng mức đáp ứng. ACA IC bắt buộc là ngoại lệ theo ràng buộc lead. Giới hạn hai buổi không được suy từ ngày rảnh trừ khi người dùng đã xác nhận; với đợt này người dùng đã đồng ý làm vậy. BTC thông thường tối đa hai buổi, ACA IC tối đa một buổi. Trạng thái tối ưu trong kết quả thể hiện đã chứng minh toàn bộ mục tiêu hay mới có phương án tốt nhất trong giới hạn thời gian.

Ba cờ tùy chọn mới trong `Cau_hinh` (Có/Không, mặc định Không): `Linh_hoat_Hoa_KHTN` cho người đăng ký Hóa dạy thêm Lý và Sinh ở đúng lớp đã đăng ký, đồng thời nhận KHTN tổng hợp nếu thuộc cấp 2; `BTC_ban_khac_truoc_ACA` tách ưu tiên người dạy thành TNV → BTC ban khác → BTC ACA IC; `Uu_tien_lop_ghep` tăng số ca ghép hợp lệ sau các mục tiêu đáp ứng và nguồn lực. Đăng ký gốc được giữ nguyên; linh hoạt không mở rộng sang lớp/cấp chưa đăng ký hoặc các môn khác như Toán/Văn. Khi bật thứ tự BTC mới, tối ưu ít buổi ACA đứng lớp trước rồi ít buổi BTC ban khác, tiếp đến ít buổi bổ sung của TNV. Buổi ACA bắt buộc dạy tại mái ấm 2 vẫn là ràng buộc cứng. Lead ở mái ấm 1 có thể chỉ trực mà không đứng lớp.

Giao diện hiển thị bảng riêng cho từng mái ấm. File kết quả có thêm `Lich_<mã mái ấm>` và `Lead_team`, đồng thời giữ đầy đủ cấu hình để tải lại. Bộ xếp giải chung nguồn lực để tránh hai lịch riêng phân công trùng người.

Bảng thời khóa biểu chính có mỗi bé một hàng, năm ngày trong tuần là năm cột, giống bố cục workbook nguồn. Mỗi ô ghi môn, mã người dạy và ký hiệu ghép/lead khi có. Hàng `LEAD TEAM` và `GHI CHÚ` nằm dưới bảng. File Excel đặt hai trang `TKB_<mã mái ấm>` ở đầu, có màu tiêu đề, đường viền và mã bé nguồn; các bảng chi tiết vẫn dùng để kiểm tra và khóa buổi. Cột tùy chọn `Be.Ma_nguon` giữ mã bé trong workbook nguồn khi xuất–tải lại; nếu trống, bảng dùng `Ma_be`.

Cột tùy chọn `Quy_tac_mai_am.Ngay_hoc_bat_buoc` ghi các ngày phải có lớp, phân tách bằng `;`. Cả hai mái ấm dùng Thứ Hai–Thứ Sáu theo xác nhận. Mỗi ngày phải có lớp và một ACA IC làm lead theo điều kiện `Lead_bat_buoc_day`; nếu dữ liệu không thể đáp ứng, ứng dụng báo lỗi thay vì trả lịch thiếu ngày hoặc lead. Để trống cột ngày nếu không bắt buộc mở lớp vào ngày cụ thể.

Khi chuẩn hóa workbook nguồn có ô gộp, lấy giá trị ô đầu vùng gộp cho mọi dòng thuộc đúng vùng đó. Đặc biệt, vai trò ACA IC trong vùng A10:A19 áp dụng cho cả nhóm người, không chỉ dòng đầu tiên. Giới hạn một buổi/tuần được áp dụng cho từng ACA IC trong nhóm. Các ô trống ngoài vùng gộp giữ nguyên là trống.

Dữ liệu thật và kết quả local được loại khỏi Git bằng `.gitignore`; repository chỉ chứa workbook mẫu giả lập. Với đợt xếp theo yêu cầu ngày 09/10/2026: lấy danh sách bé, lớp và môn từ TKB hiện tại, mặc định bé rảnh cả năm ngày. Mái ấm 1 cho phép ghép cấp 1 cùng lớp, cùng môn theo xác nhận; mái ấm 2 chỉ xếp 1:1 và cần lead ACA IC trực tiếp dạy. Mỗi môn trong ô gộp qua nhiều bé được tính riêng cho từng bé; môn trong ngoặc cũng được giữ. Ngày của TKB nguồn chỉ dùng đối chiếu, không khóa ngày cũ khi phân công lại.

Mẫu `data/du_lieu_mau.xlsx`: 6 TNV, 9 bé, 14 nhu cầu, 2 cặp xung khắc, đánh giá ưu tiên/cấm và 1 lựa chọn khóa. `BE008` thiếu TNV đúng lớp; `BE009` không có ngày chung. Đây là các trường hợp cố ý chưa thể đáp ứng.

## Quy tắc và tối ưu

Mỗi buổi gồm một TNV, một môn và một hoặc hai bé. Lớp hai bé phải cùng tuổi, cùng môn và mỗi bé đều phù hợp lớp TNV đã đăng ký; không yêu cầu hai bé cùng lớp nếu TNV đăng ký cả hai lớp. Mỗi người tối đa một buổi/ngày. TNV không vượt giới hạn tuần. Không ghép và khóa là ràng buộc cứng; khóa không được lấn át lịch rảnh hoặc chuyên môn.

OR-Tools CP-SAT tối ưu lần lượt: số bé khác nhau có ít nhất một buổi → số nhu cầu được đáp ứng → số lựa chọn ưu tiên được đáp ứng → giảm số buổi hai bé → giảm tổng bình phương số buổi của từng TNV (cân bằng số buổi tuyệt đối). Chỉ cố định mục tiêu khi chứng minh tối ưu rồi mới chuyển sang mục tiêu tiếp theo; không dùng tổng trọng số có thể đảo thứ tự ưu tiên.

Giới hạn tổng thời gian tìm kiếm mặc định 30 giây. Nếu hết thời gian, trả phương án hợp lệ tốt nhất đã tìm được và báo có thể còn cải thiện. Các khóa chỉ được dùng làm lịch nền khi thỏa cả yêu cầu lead; nếu chưa tìm được lịch có lead giữ toàn bộ khóa, ứng dụng báo rõ cần kiểm tra khóa hoặc tăng thời gian xếp. Nhu cầu chưa đáp ứng được giải thích bằng kiểm tra chuyên môn/ngày/cấm và các nguyên nhân có thể; không tuyên bố xác định chính xác một nguyên nhân duy nhất cho xung đột toàn cục.

## Kiến trúc và kiểm thử

```text
app.py                    giao diện Streamlit
scheduler/models.py       mô hình dữ liệu
scheduler/excel_io.py     đọc, chuẩn hóa, kiểm tra và ghi workbook
scheduler/engine.py       kiểm tra khóa và xếp lịch
scheduler/policies.py     quy tắc mái ấm, lớp ghép và lead
scheduler/explanations.py giải thích nhu cầu còn thiếu
scheduler/export.py       bảng kết quả và xuất Excel
scripts/sample_data.py    dữ liệu giả lập
tests/                    kiểm thử nghiệp vụ, Excel và giao diện
```

Đánh giá hiện tại nằm ở `Dataset.ratings`; `eligible` đọc đánh giá này, không đọc phỏng vấn/insight. Có thể bổ sung module chấm độ phù hợp độc lập về sau, nhưng phải thiết kế lại rõ mục tiêu ưu tiên trước khi đưa điểm vào bộ xếp lịch.

Chạy kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Kiểm thử bao gồm các ràng buộc nghiệp vụ, thứ tự tối ưu, khóa mâu thuẫn, lịch thiếu nguồn lực, thời gian tìm kiếm bằng 0, chuẩn hóa/kiểm tra Excel, xuất–tải lại và luồng giao diện xếp–khóa–xếp lại–đánh giá cấm. File kiểm chứng được tạo trong `outputs/` và không đưa vào Git.

## Giới hạn MVP

- Một khung giờ cố định; không quản lý phòng học, lịch nghỉ, ngày tháng cụ thể hoặc nhiều tuần.
- Một nhu cầu bé–môn tương ứng một buổi/tuần; không có số buổi riêng cho từng môn.
- Không đăng nhập, không cơ sở dữ liệu và không hợp nhất chỉnh sửa nhiều người. Phiên làm việc cần tải file xuống để lưu.
- Số ứng viên tăng nhanh khi nhiều bé có cùng tuổi/môn; dữ liệu lớn có thể hết thời gian trước khi chứng minh tối ưu. Các phương án đồng hạng không có tiêu chí phá hòa riêng.
- Không tự phân tích ghi chú hoặc thông tin phỏng vấn.
- Khi chuyển sang máy khác, phải tạo lại `.venv`; không sao chép môi trường này qua Git.

## GitHub

Repository được yêu cầu là riêng tư, tên `sap-xep-tkb`. Nếu máy chưa có đăng nhập GitHub khả dụng, project local và commit vẫn được hoàn thành; có thể đăng nhập GitHub CLI rồi chạy:

```powershell
gh auth login
gh repo create sap-xep-tkb --private --source . --remote origin --push
```
