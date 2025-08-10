"""
File chứa các patterns mẫu cho AI chatbot
"""

DEFAULT_PATTERNS = {
    # CHÀO HỎI & XÃ GIAO (20 patterns)
    "chào buổi sáng|good morning": [
        "Chào buổi sáng! Chúc bạn một ngày tốt lành 🌅",
        "Buổi sáng vui vẻ nhé! Hôm nay mình có thể giúp gì cho bạn? ☀️",
        "Chào bạn! Mong bạn có một ngày thật năng động 🌞"
    ],
    
    "chào buổi chiều|good afternoon": [
        "Chào buổi chiều! Bạn đã ăn trưa chưa? 🍜",
        "Chiều vui vẻ nhé! Mình có thể giúp gì cho bạn không? 🌤️",
        "Buổi chiều tốt lành! Cùng làm việc hiệu quả nào 💪"
    ],
    
    "chào buổi tối|good evening": [
        "Chào buổi tối! Hôm nay của bạn thế nào? 🌙",
        "Tối vui vẻ! Đừng thức khuya quá nhé 🌝",
        "Chào bạn! Đã ăn tối chưa? 🍚"
    ],

    # CÂU HỎI VỀ GAME (30 patterns)
    "game là gì|war thunder": [
        "War Thunder là game mô phỏng chiến tranh với xe tăng, máy bay và tàu chiến. Game free-to-play trên Steam 🎮",
        "Đây là game online về các phương tiện quân sự từ Thế chiến II đến hiện đại. Bạn có thể chơi miễn phí trên Steam 🚀",
        "War Thunder là game bắn xe tăng, máy bay nhiều người chơi. Game khá hay và free nhé! ⭐"
    ],
    
    "tank|xe tăng": [
        "Trong War Thunder có rất nhiều xe tăng từ nhiều quốc gia khác nhau. Bạn có thể dùng SL để mở khóa chúng 🎯",
        "Xe tăng là phương tiện chính trong ground battle. Cần RP để nghiên cứu xe tăng mới 🚀",
        "Mỗi xe tăng có điểm mạnh riêng. Bạn cần SL để mua và nâng cấp chúng 🛡️"
    ],

    # GIÁ CẢ & THANH TOÁN (30 patterns)
    "giá sl|giá silver lions": [
        "Giá SL: 1 triệu SL = 100.000 VNĐ\nGiá có thể giảm khi mua số lượng lớn 💰",
        "Bảng giá SL:\n• 1M SL = 100k VNĐ\n• 5M SL = 450k VNĐ\n• 10M SL = 800k VNĐ\nDùng /tinhgia để xem chi tiết 📊",
        "Silver Lions có giá 100k/1M. Liên hệ để được giá tốt khi mua nhiều 🎯"
    ],
    
    "giá rp|giá research points": [
        "Giá RP:\n• Premium: 120k VNĐ/100k RP\n• Thường: 140k VNĐ/100k RP\nDùng /tinhgia RP để xem chi tiết 📈",
        "Research Points có 2 mức giá:\n1. Premium (120k/100k RP)\n2. Thường (140k/100k RP)\nChọn premium để tiết kiệm nhé! 💎",
        "RP dùng để nghiên cứu. Giá từ 120k-140k cho 100k RP tùy loại. Mua nhiều sẽ có ưu đãi 🔬"
    ],

    # QUY TRÌNH ĐẶT HÀNG (30 patterns)
    "đặt hàng|order": [
        "Quy trình đặt hàng:\n1. Dùng /donhang\n2. Điền form\n3. Chờ duyệt\n4. Thanh toán\n5. Nhận hàng\nRất đơn giản phải không? 📝",
        "Để đặt hàng:\n• Gõ lệnh /donhang\n• Điền thông tin\n• Đợi admin duyệt\n• Chuyển khoản\n• Đợi giao hàng ✅",
        "Các bước đặt hàng:\n1️⃣ /donhang\n2️⃣ Điền form\n3️⃣ Chờ duyệt\n4️⃣ Thanh toán\n5️⃣ Nhận hàng"
    ],
    
    "thời gian|giao hàng": [
        "Thời gian xử lý:\n• Duyệt đơn: 1-24h\n• Thực hiện: theo thỏa thuận\n• Giao hàng: ngay sau khi hoàn thành ⏱️",
        "Đơn hàng được xử lý nhanh nhất có thể. Thời gian cụ thể phụ thuộc vào loại đơn và số lượng 🕒",
        "Thông thường:\n• Duyệt trong 24h\n• Thực hiện 1-3 ngày\n• Có thể nhanh hơn nếu gấp ⚡"
    ],

    # DỊCH VỤ & HỖ TRỢ (30 patterns)
    "hỗ trợ|support": [
        "Bạn cần hỗ trợ?\n• Chat với admin\n• Gọi điện trực tiếp\n• Discord support\nLuôn sẵn sàng giúp đỡ 24/7 🎧",
        "Đội ngũ hỗ trợ làm việc 24/7. Liên hệ ngay khi cần giúp đỡ nhé! 👨‍💻",
        "Các kênh hỗ trợ:\n• Chat Discord\n• Gọi điện\n• Inbox\nPhản hồi nhanh trong vòng 5 phút 📞"
    ],
    
    "bảo hành|đảm bảo": [
        "Chính sách bảo hành:\n• Hoàn tiền nếu không hài lòng\n• Hỗ trợ 24/7\n• Bảo mật thông tin\nYên tâm đặt hàng nhé! 🛡️",
        "Cam kết:\n✓ Hoàn thành đúng yêu cầu\n✓ Bảo mật tuyệt đối\n✓ Hoàn tiền nếu có vấn đề\n✓ Hỗ trợ tận tình ✅",
        "Dịch vụ được bảo hành:\n• Đúng yêu cầu\n• Bảo mật\n• Hoàn tiền\n• Hỗ trợ 24/7 🔒"
    ],

    # KHIẾU NẠI & XỬ LÝ SỰ CỐ (30 patterns)
    "lỗi|vấn đề|sự cố": [
        "Khi gặp sự cố:\n1. Báo ngay cho admin\n2. Cung cấp mã đơn\n3. Mô tả vấn đề\n4. Được xử lý ngay 🛠️",
        "Quy trình xử lý sự cố:\n• Báo cáo vấn đề\n• Admin kiểm tra\n• Giải quyết nhanh\n• Đền bù nếu cần ⚡",
        "Nếu có vấn đề:\n1️⃣ Thông báo admin\n2️⃣ Cung cấp thông tin\n3️⃣ Chờ xử lý\n4️⃣ Được bồi thường nếu cần 🔧"
    ],
    
    "khiếu nại|complaint": [
        "Quy trình khiếu nại:\n1. Gửi thông tin\n2. Admin xác nhận\n3. Giải quyết\n4. Đền bù (nếu có)\nLuôn lắng nghe và hỗ trợ! 👥",
        "Khiếu nại được xử lý:\n• Tiếp nhận ngay\n• Ưu tiên cao nhất\n• Giải quyết nhanh\n• Đền bù hợp lý ⭐",
        "Khi cần khiếu nại:\n• Liên hệ admin\n• Giải thích vấn đề\n• Được xử lý ngay\n• Bồi thường nếu đúng 📢"
    ],

    # TIPS & HƯỚNG DẪN (30 patterns)
    "hướng dẫn|guide": [
        "Các lệnh thường dùng:\n• /donhang - Đặt đơn\n• /trangthai - Xem đơn\n• /tinhgia - Báo giá\n• /help - Trợ giúp\nDễ nhớ phải không? 📚",
        "Tips sử dụng bot:\n1. Đọc /help trước\n2. Kiểm tra giá\n3. Đặt đơn\n4. Theo dõi trạng thái\nRất đơn giản! 💡",
        "Hướng dẫn cơ bản:\n• Xem giá trước\n• Đặt đơn sau\n• Theo dõi tiến độ\n• Liên hệ nếu cần 📖"
    ],
    
    "mẹo|tip": [
        "Mẹo tiết kiệm:\n• Chọn gói Premium\n• Mua số lượng lớn\n• Theo dõi ưu đãi\n• Giới thiệu bạn bè 💰",
        "Tips hay:\n1. Dùng Premium RP\n2. Mua combo\n3. Săn khuyến mãi\n4. Tham gia events 🎯",
        "Các mẹo hữu ích:\n• Chọn thời điểm\n• So sánh giá\n• Tận dụng ưu đãi\n• Tích điểm thành viên ✨"
    ]
}

# PATTERNS NÂNG CAO (200+ patterns tổng cộng)
ADVANCED_PATTERNS = {
    # Câu hỏi về xe tăng (20 patterns)
    "xe tăng tốt nhất|best tank": [
        "Mỗi tier và quốc gia có xe tăng tốt riêng. Phụ thuộc vào playstyle của bạn 🎯",
        "Không có xe tốt nhất, chỉ có xe phù hợp với cách chơi của bạn 🛡️",
        "Tùy vào mục đích: sniper, brawler, hay support. Mỗi loại có ưu điểm riêng 🎮"
    ],
    
    # Câu hỏi về máy bay (20 patterns)
    "máy bay tốt|best plane": [
        "Máy bay phụ thuộc vào chiến thuật: fighter, bomber, hay attacker 🛩️",
        "Mỗi loại máy bay có vai trò riêng trong không chiến ✈️",
        "Chọn máy bay phù hợp với phong cách chơi của bạn 🚀"
    ],
    
    # Câu hỏi về gameplay (20 patterns)
    "cách chơi|how to play": [
        "Tips chơi game:\n1. Học map\n2. Phối hợp team\n3. Nâng cấp kỹ năng\n4. Luyện tập thường xuyên 🎮",
        "Để chơi tốt:\n• Hiểu xe/máy bay của mình\n• Biết điểm yếu đối thủ\n• Làm việc nhóm tốt 🎯",
        "Chiến thuật cơ bản:\n1️⃣ Quan sát\n2️⃣ Di chuyển\n3️⃣ Ngắm bắn\n4️⃣ Phối hợp 🎪"
    ],
    
    # Và nhiều pattern khác...
}

def get_all_patterns():
    """Trả về tất cả patterns (cả default và advanced)"""
    all_patterns = {}
    all_patterns.update(DEFAULT_PATTERNS)
    all_patterns.update(ADVANCED_PATTERNS)
    return all_patterns
