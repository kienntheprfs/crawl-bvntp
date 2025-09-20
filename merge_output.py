import os
from pathlib import Path
import re
from bs4 import BeautifulSoup

def get_url_to_title_mapping(header_file_path):
    """Đọc file header HTML và tạo mapping từ URL sang tiêu đề tiếng Việt."""
    url_to_title = {}
    category_order = {}
    sub_counter = {}  # Đếm số thứ tự cho mỗi category
    
    with open(header_file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
    
    # Định nghĩa thứ tự La Mã cho các category
    roman_map = {
        "Tin tức": "VII",
        "Góc Y học": "VIII",
        "KHCN": "IX",
        "Góc Bệnh Nhân": "X"
    }
    
    # Các category cần bỏ qua
    skip_categories = ["Giới thiệu", "Thông tin chung", "Góc Tri Ân", "Liên hệ", "Đấu thầu"]
    
    for li in soup.select("ul.nav-menu > li"):
        a_tag = li.find("a")
        if not a_tag:
            continue
        category = a_tag.get_text(strip=True).replace("\n", "").split("<")[0].strip()
        if category in skip_categories:
            continue
            
        # Gán số La Mã cho category nếu có
        if category in roman_map:
            category_order[category] = roman_map[category]
            sub_counter[category] = 1  # Khởi tạo bộ đếm cho sub items
            
        # Lấy các sub items trong submenu
        for sub_a in li.select("ul.submenu a"):
            href = sub_a.get("href")
            title = sub_a.get_text(strip=True)
            if href and title:
                href = href.rstrip("/")
                url_to_title[href] = (title, category, sub_counter.get(category, 1))
                if category in sub_counter:
                    sub_counter[category] += 1
    
    return url_to_title, category_order

def get_special_groups(special_file_path="dac_biet.txt"):
    """Parse file dac_biet.txt để lấy các nhóm đặc biệt và các sub items."""
    groups = {}
    
    with open(special_file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
    
    for div in soup.find_all('div', class_='col-lg-8 col-md-7'):
        h1 = div.find('h1')
        if h1:
            group_title = h1.text.strip()
            subs = []
            for a in div.find_all('a'):
                href = a.get('href')
                h2 = a.find('h2')
                if href and h2:
                    sub_title = h2.text.strip()
                    slug = href.replace("https://bvnguyentriphuong.com.vn/", "").rstrip("/")
                    subs.append({"slug": slug, "title": sub_title})
            if subs:
                groups[group_title] = subs
    
    return groups

def merge_markdown_files(header_file_path="pasted-text.txt", special_file_path="dac_biet.txt"):
    """Gộp các file markdown theo thứ tự URLs từ header file với tiêu đề tiếng Việt, xử lý đặc biệt cho các khối."""
    # Đọc mapping từ URL sang tiêu đề và category order
    url_to_title, category_order = get_url_to_title_mapping(header_file_path)
    
    # Đọc các nhóm đặc biệt
    special_groups = get_special_groups(special_file_path)
    
    # Danh sách slugs đặc biệt
    special_slugs = ["khoi-noi", "khoi-ngoai", "chuyen-khoa-le", "can-lam-sang", "tin-tuc-y-duoc-khac"]
    
    # Danh sách URLs theo thứ tự trong header file
    urls = list(url_to_title.keys())
    
    # Đường dẫn thư mục chứa các file markdown
    input_dir = Path("./final_bvntp")
    output_file = Path("./final_bvntp/merged_output.md")

    # Tạo thư mục đầu ra nếu chưa tồn tại
    output_file.parent.mkdir(exist_ok=True)

    # Bộ đếm số file đã merge
    file_count = 0
    
    # Biến để theo dõi category hiện tại
    current_category = None
    last_category = None

    # Mở file đầu ra để ghi
    with open(output_file, "w", encoding="utf-8") as outfile:
        # Duyệt qua từng URL theo thứ tự
        for url in urls:
            # Chuyển URL thành tên file và slug
            slug = url.replace("https://bvnguyentriphuong.com.vn/", "").rstrip("/")
            file_name = slug + ".md"
            file_path = input_dir / file_name

            # Lấy tiêu đề, category và số thứ tự
            title, category, sub_number = url_to_title.get(url, (slug, None, 1))

            # Xử lý category heading
            if category and category != current_category:
                if category in category_order:
                    outfile.write(f"# {category_order[category]}. {category}\n\n")
                    current_category = category

            if slug in special_slugs:
                # Xử lý đặc biệt: Normalize title để match group in special_groups
                group_title = title.replace("_", " - ")
                outfile.write(f"## {sub_number}. {group_title}\n\n")
                
                # Lấy subs từ special_groups
                subs = special_groups.get(group_title, [])
                for sub in subs:
                    sub_file_name = sub["slug"] + ".md"
                    sub_file_path = input_dir / sub_file_name
                    if sub_file_path.exists():
                        try:
                            with open(sub_file_path, "r", encoding="utf-8") as infile:
                                content = infile.read()
                                # Thay thế PLACEHOLDER_HEADING và PLACEHOLDER_FILE
                                content = content.replace("[[[PLACEHOLDER_HEADING]]]", "#")
                                content = content.replace("[[[PLACEHOLDER_FILE]]]", "####")
                                # Ghi tiêu đề cấp 3 với tên sub
                                outfile.write(f"### {sub['title']}\n\n")
                                # Ghi nội dung sub file
                                outfile.write(content)
                                # Thêm dấu phân cách giữa các sub
                                outfile.write("\n\n---\n\n")
                                file_count += 1
                        except Exception as e:
                            print(f"Lỗi khi đọc sub file {sub_file_name}: {e}")
                    else:
                        print(f"Sub file {sub_file_name} không tồn tại.")
                
                # Thêm phân cách sau toàn bộ group
                outfile.write("\n\n---\n\n")
            else:
                # Xử lý thông thường
                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            content = infile.read()
                            # Thay thế PLACEHOLDER_HEADING và PLACEHOLDER_FILE
                            content = content.replace("[[[PLACEHOLDER_HEADING]]]", "#")
                            content = content.replace("[[[PLACEHOLDER_FILE]]]", "####")
                            # Ghi tiêu đề cấp 1 với số thứ tự và tên tiếng Việt
                            outfile.write(f"## {sub_number}. {title}\n\n")
                            # Ghi nội dung file
                            outfile.write(content)
                            # Thêm dấu phân cách giữa các file
                            outfile.write("\n\n---\n\n")
                            file_count += 1
                    except Exception as e:
                        print(f"Lỗi khi đọc file {file_name}: {e}")
                else:
                    print(f"File {file_name} không tồn tại.")

    print(f"Đã gộp {file_count} file vào {output_file}")

if __name__ == "__main__":
    merge_markdown_files()