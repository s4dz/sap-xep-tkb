"""Anonymous fixture definitions shared by the sample builder and tests."""
from scheduler.models import Child, Dataset, Demand, Lock, Volunteer, DAYS

def sample_data() -> Dataset:
    volunteers = {
        "TNV001": Volunteer("TNV001", frozenset({("Toán", 3), ("Tiếng Việt", 3)}), frozenset(DAYS[:2])),
        "TNV002": Volunteer("TNV002", frozenset({("Tiếng Anh", 3), ("Tiếng Anh", 4)}), frozenset(DAYS[1:3])),
        "TNV003": Volunteer("TNV003", frozenset({("Toán", 6), ("Ngữ văn", 6)}), frozenset(DAYS[2:4]), 2),
        "TNV004": Volunteer("TNV004", frozenset({("Khoa học tự nhiên", 6)}), frozenset(DAYS[3:])),
        "TNV005": Volunteer("TNV005", frozenset({("Toán", 10), ("Tiếng Anh", 10)}), frozenset({DAYS[0], DAYS[4]})),
        "TNV006": Volunteer("TNV006", frozenset({("Toán", 3), ("Tiếng Việt", 3)}), frozenset({DAYS[0], DAYS[2]})),
    }
    specs = [(8, 3, [0, 1], ["Toán", "Tiếng Việt"]), (8, 3, [0, 1, 2], ["Toán", "Tiếng Anh"]),
             (9, 4, [1, 2], ["Tiếng Anh"]), (11, 6, [2, 3], ["Toán", "Ngữ văn"]),
             (11, 6, [2, 3, 4], ["Toán", "Khoa học tự nhiên"]), (15, 10, [0, 4], ["Toán", "Tiếng Anh"]),
             (8, 3, [0, 2], ["Toán"]), (12, 7, [1, 4], ["Ngữ văn"]), (11, 6, [0], ["Khoa học tự nhiên"])]
    children, demands = {}, []
    for idx, (age, grade, days, subjects) in enumerate(specs, 1):
        cid = f"BE{idx:03}"
        children[cid] = Child(cid, age, grade, frozenset(DAYS[d] for d in days))
        demands.extend(Demand(cid, sub) for sub in subjects)
    return Dataset(volunteers, children, demands,
                   {frozenset({"BE001", "BE002"}), frozenset({"BE004", "BE005"})},
                   {("TNV001", "BE001"): "Ưu tiên", ("TNV003", "BE004"): "Ưu tiên", ("TNV006", "BE002"): "Không ghép"},
                   {Lock("TNV001", "BE001", "Toán", DAYS[0])},
                   {c: "Ghi chú giả lập: cần ôn kiến thức nền và hướng dẫn từng bước." for c in children},
                   {"TNV001": [("Bạn có thể hỗ trợ môn nào?", "Toán và Tiếng Việt lớp 3.")],
                    "TNV002": [("Bạn có thể hỗ trợ môn nào?", "Tiếng Anh lớp 3 và 4."), ("Lịch rảnh?", "Thứ Ba và Thứ Tư.")],
                    "TNV003": [("Kinh nghiệm giảng dạy?", "Thông tin giả lập: từng hỗ trợ nhóm học sinh.")]})
