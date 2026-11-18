"""Rule-based Facebook group category classifier."""

import unicodedata


def classify_group(slug, name):
    norm_name = unicodedata.normalize('NFKD', name)
    s = f"{slug} {name} {norm_name}".lower()
    
    # 1. Test / Personal
    if name.strip().lower() in ['test', 'test2'] or slug in ['1084600079916206', '4068605576730229']:
        return ("Thử nghiệm & Quản trị cá nhân", "Nhóm quản trị cá nhân / Thử nghiệm")
        
    # 2. Gambling / Sunwin
    if 'sunwin' in s or 'về bờ' in s:
        return ("Cờ bạc & Game đổi thưởng", "Game bài / Đổi thưởng Sunwin")
        
    # 3. MMO / Honeygain
    if 'honeygain' in s:
        return ("Kiếm tiền Online & MMO", "Chia sẻ băng thông / Honeygain")

    # 4. Dating / Relationship
    if any(k in s for k in ['độc thân', 'kiếm ny', 'tình duyên', 'hẹn hò']):
        return ("Hẹn hò & Đời sống cá nhân", "Giao lưu kết bạn / Tìm người yêu")

    # 5. Memes / Entertainment / Community Humor
    if any(k in s for k in ['mêm', 'meme', 'ytp', 'dảk', 'bizarre', 'trại gà ngố', 'khong ai hoan hao', 'hoan hao ca']):
        return ("Giải trí & Meme", "Cộng đồng chế ảnh / Meme & Tâm sự")

    # 6. Bus / Confessions
    if 'xe bus' in s or 'xebus' in s:
        return ("Giao thông & Đời sống đô thị", "Xe buýt Hà Nội & Confessions")

    # 7. Telecom / Data / VPN
    if any(k in s for k in ['4g/5g', 'data sim', 'free vpn', 'data4g']):
        return ("Viễn thông & Dịch vụ mạng", "Hack Data 4G/5G & VPN")

    # 8. E-Commerce Agency / Facebook Ads
    if any(k in s for k in ['quảng cáo facebook', 'agency', 'chủ shop', 'bán hàng online', 'aff marketing', 'tiếp thị liên kết']):
        return ("Kinh doanh Online & Marketing", "Thương mại điện tử & Facebook Ads")

    # 9. Health & Dental & Aesthetics
    if any(k in s for k in ['niềng răng', 'chỉnh hàm', 'hô móm', 'gọt hàm', 'hạ gò má', 'nha khoa', 'răng']):
        return ("Nha khoa & Phẫu thuật thẩm mỹ", "Chỉnh nha, Niềng răng & Phẫu thuật hàm")

    # 10. Housing & Rentals (Phòng trọ / CCMN / Nhà trọ / Căn hộ)
    if any(k in s for k in [
        'phòng trọ', 'nhà trọ', 'ccmn', 'chung cư', 'nhà nguyên căn', 'thuê phòng', 
        'ở ghép', 'tìm phòng', 'thuenha', 'phongtro', 'nhatro', 'apartment', 
        'cho thuê nhà', 'homestay', 'studio,1n1k', 'cho thuê trọ', 'bình thạnh', 
        'nhà cho thuê', 'cho thuê chưng cư', 'căn hộ chung cư', 'cho thuê căn hộ', 'bất động sản'
    ]) or slug in ['1058967454595890', '455233729045684', '1437237960311125', 'cho.thue.can.ho.chung.cu.tai.hanoi', 'cchothuecanhochungcuhanoi', 'httpswww.facebook.comchothachthanh.thanhhoa.th']:
        if any(k in s for k in ['ở ghép', 'timnguoioghep']):
            detail = "Tìm người ở ghép phòng trọ"
        elif any(k in s for k in ['nguyên căn', 'nhanguyencan']):
            detail = "Cho thuê nhà nguyên căn"
        elif any(k in s for k in ['ccmn', 'chung cư', 'apartment', 'studio', 'căn hộ']):
            detail = "Cho thuê chung cư mini & Căn hộ dịch vụ"
        elif any(k in s for k in ['cầu giấy', 'mỹ đình', 'hồ tùng mậu', 'cầu diễn', 'phú diễn', 'nhổn']):
            detail = "Phòng trọ khu vực Cầu Giấy, Nam/Bắc Từ Liêm"
        elif 'bất động sản' in s:
            detail = "Bất động sản địa phương"
        else:
            detail = "Cho thuê phòng trọ & Nhà trọ Hà Nội"
        return ("Bất động sản & Cho thuê phòng trọ", detail)

    # 11. Tutoring / Language / Translation
    if any(k in s for k in ['gia sư', 'dịch thuật', 'biên dịch', 'phiên dịch', 'tiếng anh', 'ielts', 'toeic', 'sư phạm - hà nội']):
        if 'dịch thuật' in s or 'biên dịch' in s or 'phiên dịch' in s:
            detail = "Cộng tác viên Biên phiên dịch"
        elif 'gia sư' in s:
            detail = "Gia sư & Dạy kèm học sinh"
        else:
            detail = "Tuyển dụng Giáo viên & Trợ giảng Tiếng Anh"
        return ("Gia sư, Dịch thuật & Ngoại ngữ", detail)

    # 12. Camera & Video Gear (Máy ảnh / Handycam)
    if any(k in s for k in ['máy ảnh', 'máy quay', 'handycam', 'nikon', 'canon', 'fujifilm', 'sony camera', 'xóm nikon', 'chomayanh', 'nhiepanh', 'chomayquayphim']):
        if 'handycam' in s or 'máy quay phim' in s:
            detail = "Máy quay phim & Handycam cầm tay"
        elif 'nikon' in s:
            detail = "Máy ảnh & Ống kính Nikon"
        elif 'canon' in s:
            detail = "Máy ảnh & Ống kính Canon"
        else:
            detail = "Mua bán máy ảnh cũ & Thiết bị nhiếp ảnh"
        return ("Máy ảnh & Thiết bị quay chụp", detail)

    # 13. Mechanical Keyboards & Accessories
    if any(k in s for k in ['bàn phím cơ', 'keychron', 'phimco', 'keyboard', 'vietnam keyboard group', 'chobanphimco', 'nghienph1mco']) or slug == 'chobanphimco':
        if 'keychron' in s:
            detail = "Bàn phím cơ Keychron & Mua bán trao đổi"
        else:
            detail = "Chợ Bàn phím cơ & Phụ kiện Custom"
        return ("Bàn phím cơ & Phụ kiện Custom", detail)

    # 14. Audio / Headphones / IEM / DAC/Amp
    if any(k in s for k in ['tai nghe', 'true wireless', 'iem', 'dac/amp', 'máy nghe nhạc', 'chotainghe', 'audiomarketplace', 'chợ audio', 'cuongtruewireless']):
        if 'true wireless' in s:
            detail = "Tai nghe không dây True Wireless"
        elif any(k in s for k in ['iem', 'dac/amp', 'cáp tai nghe']):
            detail = "Tai nghe IEM, DAC/Amp & Dây cáp âm thanh"
        else:
            detail = "Chợ Tai nghe & Thiết bị âm thanh cao cấp"
        return ("Tai nghe & Thiết bị âm thanh", detail)

    # 15. Mobile Phones, iOS, Android, IMEI, iCloud, Parts & Repair
    if any(k in s for k in [
        'up rom', 'root máy', 'unlock', 'unbrick', 'xác điện thoại', 'điện thoại', 
        'iphone', 'ipad', 'xiaomi', 'redmi', 'samsung', 'vsmart', 'nokia', 
        'icloud', 'ghép sim', 'icfix', 'ic team', 'thợ sửa chữa điện thoại', 
        'apple', 'ip 12', 'muabandienthoai', 'dienthoai', 'anh em mobile'
    ]):
        if any(k in s for k in ['xác điện thoại', 'linh kiện điện thoại', 'linh phụ kiện điện thoại', 'icfix', 'ic team', 'linhkienzinip', 'anh em mobile', 'sửa chữa điện thoại']):
            return ("Linh kiện & Sửa chữa điện thoại", "Linh phụ kiện & Xác điện thoại thợ sửa")
        if any(k in s for k in ['up rom', 'root', 'unbrick', 'cài rom', 'icloud', 'bypass']):
            return ("Phần mềm & Unlock điện thoại (ROM/Root/iCloud)", "Up ROM, Root Android & Mở khóa iCloud")
        if any(k in s for k in ['iphone', 'apple', 'ip 12']):
            detail = "Mua bán iPhone & Hệ sinh thái Apple"
        elif any(k in s for k in ['xiaomi', 'redmi']):
            detail = "Cộng đồng & Mua bán điện thoại Xiaomi/Redmi"
        elif 'samsung' in s:
            detail = "Cộng đồng Samsung Galaxy"
        elif 'vsmart' in s:
            detail = "Cộng đồng Vsmart"
        elif 'nokia' in s:
            detail = "Cộng đồng Nokia"
        else:
            detail = "Mua bán điện thoại cũ & mới"
        return ("Điện thoại thông minh & Phụ kiện Mobile", detail)

    # 16. Hardware Salvage / Electronics Repair
    if any(k in s for k in [
        'rã xác', 'xác laptop', 'xác main', 'xác thiết bị', 'kỹ thuật sửa chữa', 
        'hội sửa chữa', 'sửa chữa đồ điện', 'sửa chữa vga', 'raxac', 'xaclaptop', 
        'bios help', 'bios bin', 'chế đồ', 'sửa chữa điện tử'
    ]):
        if 'bios' in s:
            detail = "Nạp ROM BIOS & Tệp tin nhị phân Mainboard"
        elif 'vga' in s:
            detail = "Sửa chữa Card màn hình VGA & Linh kiện PC"
        elif 'laptop' in s:
            detail = "Rã xác laptop & Thu mua xác máy tính"
        else:
            detail = "Sửa chữa điện tử, bo mạch & Tận dụng linh kiện cũ"
        return ("Sửa chữa phần cứng & Rã xác linh kiện", detail)

    # 17. Gaming & Esports & Handheld
    if any(k in s for k in [
        'valorant', 'đấu trường chân lý', 'grouptft', 'liên minh huyền thoại', 
        '2xko', 'among us', 'handheld', 'steam deck', 'legion go', 'rog ally', 
        'cloud gaming', 'gefoce now', 'esports', 'vệ thần arena', 'gamedev', 
        'indie game', 'việc làm ngành game', 'game không hay', 'cyber gaming', 
        'quán net', 'geoguessr', 'oeg'
    ]) or slug in ['132728896890594']:
        if any(k in s for k in ['việc làm ngành game', 'animation, game, vfx']):
            return ("Tuyển dụng & Việc làm Game/VFX", "Tuyển dụng 2D/3D Game & Animation")
        if any(k in s for k in ['handheld', 'steam deck', 'legion go', 'rog ally', 'gpd']):
            return ("Máy chơi game Handheld & Console", "Handheld PC: Steam Deck, ROG Ally, Legion Go")
        if 'quán net' in s or 'cyber gaming' in s:
            return ("Game & Dịch vụ Phòng net / Cyber Games", "Quán Net, Cyber Gaming & Dịch vụ Internet")
        if 'indie game' in s:
            return ("Game & Phát triển trò chơi (Game Dev)", "Cộng đồng Nhà phát triển Game Indie")
        if 'valorant' in s:
            detail = "Cộng đồng game VALORANT"
        elif 'đấu trường chân lý' in s or 'grouptft' in s:
            detail = "Cộng đồng game Đấu Trường Chân Lý (TFT)"
        elif 'liên minh huyền thoại' in s:
            detail = "Cộng đồng Liên Minh Huyền Thoại (LoL)"
        else:
            detail = "Cộng đồng Game & Thể thao điện tử"
        return ("Game & Thể thao điện tử (Esports)", detail)

    # 18. IT & Programming & Cybersecurity
    if any(k in s for k in [
        'python', 'cissp', 'pentester', 'an toàn thông tin', 'ctf', 'linux', 
        'arduino', 'j2team', 'anonyviet', 'subliminal', 'chatbot', 'gentechit', 
        'genzlamit', 'cntt nơi chia sẻ', 'grouptinhte'
    ]):
        if any(k in s for k in ['cissp', 'pentester', 'an toàn thông tin', 'ctf']):
            return ("An toàn thông tin & An ninh mạng", "Bảo mật thông tin, An ninh mạng & Pentest")
        if 'python' in s or 'lập trình' in s or 'genzlamit' in s:
            return ("Lập trình & Phát triển phần mềm", "Lập trình Python & Tự học phần mềm")
        if 'linux' in s or 'arduino' in s:
            return ("Hệ điều hành, Linux & Phần cứng nhúng", "Mã nguồn mở Linux & Phần cứng vi điều khiển")
        return ("Cộng đồng Công nghệ thông tin & Lập trình", "Diễn đàn IT, Kỹ sư phần mềm & Chia sẻ công nghệ")

    # 19. IT Recruitment & Jobs
    if any(k in s for k in [
        'việc làm & thực tập it', 'tuyển dụng it', 'thực tập sinh it', 'it jobs', 
        'it helpdesk', 'it outsource', 'it remote', 'ba, po', 'developer/tester', 
        'thợ sửa máy tính laptop', 'kỹ thuật viên máy tính', 'kỹ thuật máy in', 'it support', 'viectotthiphaihot'
    ]):
        if any(k in s for k in ['kỹ thuật viên máy tính', 'thợ sửa máy tính', 'kỹ thuật máy in', 'kỹ thuật (máy tính']):
            detail = "Tuyển dụng Kỹ thuật viên sửa chữa Máy tính / Máy in"
        elif 'intern' in s or 'thực tập' in s:
            detail = "Tuyển dụng Thực tập sinh IT (Intern / Fresher)"
        elif 'remote' in s or 'freelancer' in s:
            detail = "Việc làm IT Freelance & Remote"
        elif 'helpdesk' in s or 'it support' in s or 'it outsource' in s:
            detail = "Tuyển dụng IT Helpdesk & IT Support"
        else:
            detail = "Tuyển dụng Lập trình viên & Kỹ sư phần mềm"
        return ("Tuyển dụng & Việc làm IT/Kỹ thuật", detail)

    # 20. General Recruitment & Part-time Jobs
    if any(k in s for k in [
        'tuyển dụng', 'việc làm', 'part time', 'full time', 'parttime', 'fulltime', 
        'tìm việc', 'vieclam', '90land - tuyển dụng'
    ]) or slug in ['830503045072888']:
        if 'cầu giấy' in s or 'mỹ đình' in s:
            detail = "Tuyển dụng Part-time & Lao động Cầu Giấy - Mỹ Đình"
        elif 'sinh viên' in s:
            detail = "Tuyển dụng Việc làm thêm cho sinh viên Hà Nội"
        else:
            detail = "Tuyển dụng Việc làm Full-time & Part-time Hà Nội"
        return ("Tuyển dụng & Việc làm phổ thông/Part-time", detail)

    # 21. Education / Academic / Students (UET / VNU / THPT / Luyện thi)
    if any(k in s for k in [
        'uet', 'vnu', 'đại học', 'k69', 'k70', '2k6', 'sinh viên 2k6', 
        'tài liệu học tập', 'ôn thi', 'toán cao cấp', 'toán học', 'học tập', 
        'bch liên chi', 'tuổi trẻ khoa', 'scholarship', 'tuyển sinh', 'hành trang sinh viên', 
        'tsa/hsa', 'cuộc thi', 'computer architecture', 'int2212', 'groupsinhvienit'
    ]):
        if any(k in s for k in ['uet', 'vnu']):
            detail = "Sinh viên Đại học Công Nghệ - ĐHQGHN (UET - VNU)"
        elif any(k in s for k in ['2k6', 'ôn thi', 'thpt', 'đgnl', 'tsa/hsa']):
            detail = "Luyện thi đại học 2K6, ĐGNL & ĐGTD"
        elif 'scholarship' in s:
            detail = "Săn học bổng du học & Học bổng sinh viên"
        elif 'toán' in s:
            detail = "Học phần Toán học & Toán cao cấp đại học"
        else:
            detail = "Tài liệu học tập & Kỹ năng sinh viên"
        return ("Giáo dục, Học tập & Sinh viên (UET / VNU / THPT)", detail)

    # 22. Laptops / Macbooks / Workstations
    if any(k in s for k in ['laptop', 'macbook', 'thinkpad', 'dell', 'hp', 'workstation', 'legion', 'predator', 'asus rog tuf']):
        if 'thinkpad' in s:
            detail = "Hội laptop Lenovo ThinkPad & Workstation"
        elif 'macbook' in s:
            detail = "Hội người dùng Apple MacBook"
        elif any(k in s for k in ['gaming', 'legion', 'predator', 'asus rog']):
            detail = "Mua bán Laptop Gaming hiệu năng cao"
        elif 'giá thợ' in s:
            detail = "Chợ Laptop cũ giá sỉ cho thợ"
        else:
            detail = "Chợ Mua bán Laptop cũ & mới sinh viên"
        return ("Laptop, Macbook & Máy trạm", detail)

    # 23. Gaming Gear
    if any(k in s for k in ['gaming gear', 'gearvn', 'gear logitech', 'chuột', 'logitech g', 'spartacus', 'edra', 'asus rog']) or slug in ['edravn', 'asusvn', 'rogempire', '915379223008388', '890660058837295']:
        if 'logitech' in s:
            detail = "Gaming Gear Logitech & Chuột/Tai nghe 2nd"
        elif 'edra' in s:
            detail = "Cộng đồng thiết bị ngoại vi EDRA"
        elif 'asus' in s or 'rog' in s:
            detail = "Cộng đồng Gaming Gear & Phần cứng ASUS ROG"
        else:
            detail = "Chợ Gaming Gear 2nd: Chuột, Phím, Tai nghe gaming"
        return ("Gaming Gear & Phụ kiện game thủ", detail)

    # 24. PC Hardware, Build PC, Monitors, Cases, PSU, Storage
    if any(k in s for k in [
        'build pc', 'pc gaming', 'máy tính', 'vga', 'linh kiện pc', 'linh kiện máy tính', 
        'màn hình', 'mini pc', 'tiny pc', 'sff pc', 'aio pc', 'case máy tính', 
        'vỏ case', 'nguồn máy tính', 'psu', 'ổ cứng', 'hdd', 'ssd', 'ram', 'cpu', 
        'amdfc', 'amd', 'geforce', 'chợ pc', 'chợ pc', 'chợ máy tính', 've chai vi tính', 
        'card không cổng', 'viewsonic', 'lgitgroup', 'egpu', 'vnitx', 'mandidong'
    ]) or slug in ['1333166007988996', '363780322844603', 'viewsonicvn', 'vnitx', 'lgitgroup', 'cdegpuvn']:
        if any(k in s for k in ['màn hình', 'viewsonic', 'mandidong']):
            detail = "Màn hình vi tính & Màn hình phụ di động"
        elif any(k in s for k in ['vga', 'card', 'geforce', 'egpu']):
            detail = "Card đồ họa VGA & Linh kiện đồ họa rời"
        elif any(k in s for k in ['mini pc', 'itx', 'sff pc', 'aio pc']):
            detail = "Máy tính nhỏ gọn Mini PC & Vietnam ITX"
        elif any(k in s for k in ['ổ cứng', 'ssd', 'ram', 'hdd', 'cpu', 'lưu trữ']):
            detail = "Linh kiện lưu trữ: SSD, HDD, RAM & CPU"
        elif 'vỏ case' in s:
            detail = "Chợ Vỏ case máy tính & Thùng máy"
        elif 'nguồn máy tính' in s or 'psu' in s:
            detail = "Nguồn máy tính (PSU) & Dây cáp"
        elif 'amd' in s:
            detail = "Cộng đồng & Phần cứng AMD Fanclub"
        elif 've chai' in s:
            detail = "Chợ Ve chai vi tính & Linh kiện máy tính rã xác"
        else:
            detail = "Chợ Mua bán Máy tính PC & Tư vấn Build PC"
        return ("Linh kiện PC, Build máy tính & Màn hình", detail)

    # 25. Furniture & Home Appliances
    if any(k in s for k in [
        'bàn ghế', 'tủ lạnh', 'điều hòa', 'máy giặt', 'bếp từ', 'nồi chảo', 
        'decor', 'đồ dùng gia đình', 'kệ - tủ', 'thanhlybanghevanphong'
    ]):
        if any(k in s for k in ['bàn ghế', 'công thái học']):
            detail = "Thanh lý Bàn ghế văn phòng & Ghế công thái học"
        elif any(k in s for k in ['bếp từ', 'nồi chảo']):
            detail = "Đồ dùng nhà bếp & Bếp từ gia đình"
        else:
            detail = "Thanh lý đồ nội thất, gia dụng & Đồ điện tử gia đình"
        return ("Thanh lý đồ gia dụng & Nội thất văn phòng", detail)

    # 26. Deals, E-Commerce, Taobao, Xianyu, Cross-border Shopping
    if any(k in s for k in [
        'order', 'xianyu', 'taobao', 'shopee', 'săn sale', 'săn deal', 'đấu giá', 
        'bid', 'kèo thơm', 'auth tuồn', 'vận chuyển hàng trung quốc', 'giải cứu hàng tồn kho'
    ]) or slug in ['3314652905513027', '845118032582994']:
        if any(k in s for k in ['xianyu', 'taobao', 'trung quốc']):
            detail = "Order hàng Trung Quốc: Taobao, Xianyu, 1688"
        elif any(k in s for k in ['shopee', 'lazada', 'săn sale', 'săn deal']):
            detail = "Săn mã giảm giá & Khuyến mãi Shopee/Lazada"
        elif any(k in s for k in ['đấu giá', 'bid']):
            detail = "Sàn Đấu giá sản phẩm công nghệ"
        else:
            detail = "Hàng xuất khẩu, Hàng tuồn & Xả kho cận date"
        return ("Săn Deal, E-Commerce & Order hàng quốc tế", detail)

    # 27. Second-hand Items & Student Resale
    if any(k in s for k in [
        'pass đồ', 'thanh lý đồ cũ', 'đồ thanh lý', 'cho tặng đồ', 'cho tặng', 'cho tặng', 
        'chotangmienphi', 'vựa đồ cũ', 'vựa 2nd', 'đồng nát', 'thanh lý đồ đã qua sử dụng', 
        'chợ sinh viên'
    ]) or slug in ['thanhlydocukhunhoncaudien', '832746071289614', 'vuadocuhin', '1752472024906832', '2754564161427998', '936368570886388', 'chotangmienphi']:
        if 'cho tặng' in s or 'miễn phí' in s:
            detail = "Cho tặng đồ miễn phí vì cộng đồng"
        elif 'sinh viên' in s or 'pass đồ' in s:
            detail = "Pass đồ sinh viên giá rẻ & Đồ dùng sinh viên cũ"
        else:
            detail = "Thanh lý đồ cũ tổng hợp & Vựa đồ cũ 2nd"
        return ("Thanh lý & Pass đồ cũ sinh viên", detail)

    # 28. Local Communities & Regional Classifieds
    if any(k in s for k in [
        'thạch thành', 'ngọc lặc', 'thanh hóa', 'hà đông', 'quốc oai', 
        'nha trang', 'người việt tại nga', 'hòn xện', 'văn la', 'dịch vọng', 
        'nguyễn đổng chi', 'đồ ăn vặt'
    ]) or slug in ['569942463857814', '1055319828937612', '807652999974064']:
        if 'nga' in s:
            detail = "Cộng đồng người Việt Nam sinh sống tại Nga"
        elif any(k in s for k in ['thạch thành', 'ngọc lặc', 'thanh hóa']):
            detail = "Rao vặt & Đời sống địa phương Thanh Hóa"
        elif 'quốc oai' in s:
            detail = "Ẩm thực & Giao đồ ăn vặt Quốc Oai"
        else:
            detail = "Chợ dân sinh & Rao vặt khu vực Hà Nội"
        return ("Cộng đồng địa phương & Rao vặt vùng miền", detail)

    # 29. General Electronics / Tech Trading
    if any(k in s for k in ['điện tử toàn quốc']):
        return ("Linh kiện & Thiết bị điện tử", "Mua bán trao đổi thiết bị điện tử toàn quốc")

    return ("Khác / Chưa phân loại", "Cộng đồng tổng hợp")


CONSOLIDATED_CATEGORIES = (
    "Laptops & MacBooks",
    "PC Parts & Peripherals",
    "Phones & Mobile",
    "Cameras & Audio",
    "General Market",
    "Other",
)

# Map the fine-grained classifier (and older manual category names) onto the
# commerce-focused buckets.
CATEGORY_CONSOLIDATION = {
    "Laptop, Macbook & Máy trạm": "Laptops & MacBooks",
    "Linh kiện PC, Build máy tính & Màn hình": "PC Parts & Peripherals",
    "Bàn phím cơ & Phụ kiện Custom": "PC Parts & Peripherals",
    "Gaming Gear & Phụ kiện game thủ": "PC Parts & Peripherals",
    "Gaming Gear": "PC Parts & Peripherals",
    "Sửa chữa phần cứng & Rã xác linh kiện": "PC Parts & Peripherals",
    "Linh kiện & Thiết bị điện tử": "PC Parts & Peripherals",
    "Máy chơi game Handheld & Console": "PC Parts & Peripherals",
    "Điện thoại thông minh & Phụ kiện Mobile": "Phones & Mobile",
    "Linh kiện & Sửa chữa điện thoại": "Phones & Mobile",
    "Phần mềm & Unlock điện thoại (ROM/Root/iCloud)": "Phones & Mobile",
    "Máy ảnh & Thiết bị quay chụp": "Cameras & Audio",
    "Tai nghe & Thiết bị âm thanh": "Cameras & Audio",
    "Thanh lý & Pass đồ cũ sinh viên": "General Market",
    "Thanh lý đồ gia dụng & Nội thất văn phòng": "General Market",
    "Cộng đồng địa phương & Rao vặt vùng miền": "General Market",
}


def consolidate_category(category):
    """Return the commerce bucket for a fine-grained category."""
    category = (category or "").strip()
    if category in CONSOLIDATED_CATEGORIES:
        return category
    return CATEGORY_CONSOLIDATION.get(category, "Other")


def classify_consolidated(slug, name):
    """Classify a group into one of the commerce buckets."""
    category, _subcategory = classify_group(slug, name)
    return consolidate_category(category), ""
