Thiết kế strategy phù hợp:
- Bắt đầu với các link trong header 
- Mỗi link trong header chứa list các <link nhỏ hơn>: lấy link thủ công bỏ lên gpt để làm sạch tag html, lập thành array các link
- Nghiên cứu cấu trúc web bệnh viện & Lập được danh sách các link thực sự cần crawl nội dung, chiều sâu và số trang
- Truy cập vào từng <link nhỏ hơn>, phải hiện ra list các bài viết để tiếp tục crawl 
- Craw mỗi bài viết trong <link nhỏ hơn> (giới hạn độ sâu là 1, số trang là 500): deep_crawl
    + trang chính được pagination thành nhiều trang nhỏ thì làm như thế nào? Làm sao biết có tất cả bao nhiêu trang : chỉnh url page += "/2", += "/3",... đến trang không có gì sẽ hiện "Danh mục chưa có bài viết" thì dừng lại
    + Làm sao để crawl được text trong hình ảnh? nghiên cứu OCR thêm
    + Chỉ crawl trong <div class="col-lg-8 col-md-7">...</div> và trong div này, bỏ các phần từ <h2 class="strong itext-red mb-15">BÀI VIẾT KHÁC</h2> trở xuống (nếu có) có khả thi không?

- Chia toàn bộ nội dung crawl được ra như thế thế nào?
    + Mỗi <link nhỏ hơn> là một trang list ra rất nhiều bài viết cùng chủ đề -> gộp hết các bài viết thành 1 file
    + Tên file là tên tiêu đề link? okay
    + Bên trong mỗi file là tiêu đề chương, lấy lại tiêu đề link để dùng, từng bài viết nhỏ sẽ là các mục 1. 2. 3.,...

Câu hỏi thảo luận thêm:
- Có cần xuất ra file markdown THEO FORMAT CỦA THẦY YÊU CẦU? oke k có format cụ thể
- Nên crawl kiểu tóm tắt lại nội dung bằng AI hay giữ nguyên văn bản gốc? giữ nguyên
Chốt sau khi họp 16/9/2025 => Tạo 2 bản: bản nhiều file nhỏ nhỏ cho Hương, bản lớn 1 file duy nhất cho thầy. Craw cần có đề mục nội dung hoặc la mã đàng hoàng

Hết ngày 17/9 còn lại
- chưa crawl được ảnh: văn bản quyết định, bảng dạng hình ảnh, các kiểu thông tin/văn bản khác dưới dạng hình ảnh,...và quan trọng hơn là phân biệt được khi nào là ảnh con người không phải văn bản (nói chung là này khó)
- chưa crawl được file, sau đó nối tiếp vào văn bản bài viết
- chưa sắp xếp được heading cho hợp lý (này xong nhanh)

Đọc docs hiểu được:
- crawl có cấu trúc và theo yêu cầu prompt: sử dụng LLM api keykey
- crawl hết thông tin text trong một trang: raw_markdown

Thư viện đã dùng
- crawl4ai
- datalab-to/marker



NỘI DUNG ĐÃ CRAWL + CẦN CRAWL: 
(để biết được nội dung cần được crawl thêm)

Trang Chủ
    <không có link con>
    <Rất nhiều nội dung gợi ý người dùng trên trang chủ>

Giới thiệu
    Sứ mệnh - Tầm nhìn (ĐÃ CRAWL)
    Năng lực Bệnh viện (ĐÃ CRAWL)
    Hình thành và phát triển (ĐÃ CRAWL)
    Cơ cấu tổ chức
    Ban Giám đốc (ĐÃ CRAWL)
    Khối chuyên môn (ĐÃ CRAWL)
    Phòng Chức Năng (ĐÃ CRAWL)
    Chính sách quyền riêng tư

Thông tin chung
    Quy trình khám bệnh (ĐÃ CRAWL)
    Bảng giá viện phí (ĐÃ CRAWL)
    Hỏi đáp (ĐÃ CRAWL)
    Lịch khám bệnh dịch vụ
    Xét nghiệm tại nhà (ĐÃ CRAWL)
    Tư liệu

Tin tức
    Thông tin bệnh viện
    Hoạt động Đảng và đoàn thể
    Thông tin khóa học
    Phổ biến pháp luật
    Văn bản triển khai nội bộ
    Khen thưởng, nêu gương


Góc Y học
    Khoa Khám bệnh
    Khối Nội_Nhi
        <grid các card: mỗi card là link nhỏ hơn>
    Khối Ngoại_Sản
        <grid các card: mỗi card là link nhỏ hơn>
    Chuyên khoa lẻ
        <grid các card: mỗi card là link nhỏ hơn>
    Cận lâm sàng
        <grid các card: mỗi card là link nhỏ hơn>
    Điều dưỡng
    Khoa Dược
    Da liễu chuyên sâu
    Phẫu thuật thẩm mỹ

KHCN
    Phác đồ điều trị
    Tài liệu chuyên môn
    Quy trình thủ tục hành chính
    Nghiên cứu được đăng tải trên tạp chí quốc tế
    Nghiên cứu nội bộ và đăng tải tạp chí trong nước
    Nghiên cứu khoa học và Thử nghiệm lâm sàng

Đấu thầu
    <Bỏ qua>
Góc Bệnh Nhân
    Câu lạc bộ bệnh nhân
    Bác sĩ tư vấn
    Video clip y tế <Bỏ qua>
    Thông tin & Tiện ích
        Hệ thống thanh toán thẻ
        Phần mềm đặt hẹn
        Tin tức y dược khác
    Liều thuốc tinh thần
    Kiến thức cho người bệnh
    Tâm lý

Góc Tri Ân
    Hoạt động từ thiện
    Thư cám ơn
    Gian hàng yêu thương & hoạt động của mạnh thường quân

Liên hệ
    <Bỏ qua>

