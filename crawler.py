import asyncio
import os
import json
import base64
from pathlib import Path
from typing import List
from crawl4ai import ProxyConfig

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, CrawlResult
from crawl4ai import RoundRobinProxyStrategy
from crawl4ai import JsonCssExtractionStrategy, LLMExtractionStrategy
from crawl4ai import LLMConfig
from crawl4ai import PruningContentFilter, BM25ContentFilter
from crawl4ai import DefaultMarkdownGenerator
from crawl4ai import BFSDeepCrawlStrategy, DomainFilter, FilterChain
from crawl4ai import BrowserConfig
import re
import aiohttp
from PyPDF2 import PdfReader
from docx import Document
# import textract
import mimetypes
import uuid  # Thêm để làm temp file unique

__cur_dir__ = Path(__file__).parent

async def download_file(url: str) -> bytes:
    """Tải nội dung file từ URL."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:  # Thêm timeout
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
    except Exception as e:
        print(f"Lỗi download {url}: {e}")
    return b""

async def extract_file_content(file_data: bytes, file_url: str) -> str:
    """Trích xuất nội dung từ file dựa trên loại file."""
    mime_type, _ = mimetypes.guess_type(file_url)
    file_extension = os.path.splitext(file_url)[1].lower()

    temp_file_path = None  # Để đảm bảo xóa dù error
    try:
        # Tạo file tạm thời để xử lý
        unique_id = uuid.uuid4().hex[:8]  # Làm unique để tránh conflict concurrent
        temp_file_path = __cur_dir__ / f"temp_file_{unique_id}{file_extension}"
        with open(temp_file_path, "wb") as f:
            f.write(file_data)

        content = ""
        if file_extension == ".pdf" or mime_type == "application/pdf":
            with open(temp_file_path, "rb") as f:
                pdf = PdfReader(f)
                for page in pdf.pages:
                    content += page.extract_text() or ""
        
        elif file_extension == ".docx" or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(temp_file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
        
        elif file_extension in [".txt", ".md"] or mime_type == "text/plain":
            with open(temp_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        
        else:
            # # Sử dụng textract cho các định dạng khác (doc, rtf, v.v.)
            # try:
            #     content = textract.process(temp_file_path).decode("utf-8")
            # except Exception as e:
                # content = f"Không thể trích xuất nội dung từ file {file_url}: {str(e)}"
            content = f"Định dạng file {file_url} không được hỗ trợ (chỉ hỗ trợ PDF, DOCX, TXT, MD)."

        
        # Xóa file tạm
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return content.strip()
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f"Lỗi extract file {file_url}: {e}")
        return f"Lỗi khi xử lý file {file_url}: {str(e)}"

async def is_file_url(url: str) -> bool:  # Không cần async, nhưng giữ nguyên
    """Kiểm tra xem URL có phải là file hay không."""
    file_extensions = [".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"]
    # print(f"URL: {url}\n\n")
    return any(url.lower().endswith(ext) for ext in file_extensions)

async def crawl_single_url(crawler, url: str) -> List[str]:  # Sửa return type
    """Crawl một URL với logic phân trang và xử lý file trong nội dung."""
    filter_chain = FilterChain([DomainFilter(allowed_domains=["bvnguyentriphuong.com.vn"])])
    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=1,
        filter_chain=filter_chain
    )

    # Không dùng results list lớn, lưu trực tiếp vào file để tránh tràn RAM
    safe_url = "_".join(url.split('/')[3:])  # Lấy phần cuối của URL bỏ domain bệnh viện đi (ví dụ: thong-tin-benh-vien)
    fit_file_path = os.path.join("final_bvntp", f"{safe_url}.md")
    os.makedirs("final_bvntp", exist_ok=True)
    with open(fit_file_path, "w", encoding="utf-8") as f:  # Mở file ở mode 'w' đầu tiên, sau append 'a'
        f.write("")  # Clear file nếu tồn tại

    page_num = 1
    stop_flag = False
    max_pages = 2000  # Giới hạn max pages để tránh loop vô tận
    article_count = 0

    while not stop_flag and page_num <= max_pages:
        try:
            page_url = f"{url}/{page_num}"
            print(f"Crawling page: {page_url}\n")

            one_pagination_results: List[CrawlResult] = await crawler.arun(
                url=page_url,
                config=CrawlerRunConfig(
                    markdown_generator=DefaultMarkdownGenerator(
                        content_filter=PruningContentFilter()
                    ),
                    deep_crawl_strategy=deep_crawl_strategy,
                    css_selector="div.col-lg-8.col-md-7",
                    excluded_selector='h2.strong.itext-red.mb-15, h2.strong.itext-red.mb-15 ~ *, .pagination.justify-content-center'
                ),
            )
            
            if len(one_pagination_results) > 1:  # Kiểm tra trước slice để tránh error
                one_pagination_results = one_pagination_results[1:]  # Bỏ trang danh sách link các bài viết
            # print(one_pagination_results)

            for result in one_pagination_results:
                markdown_content = result.markdown.fit_markdown
                if "Danh mục chưa có bài viết" in markdown_content:
                    print(f"Đã dừng tại trang {page_num}: Danh mục chưa có bài viết\n")
                    stop_flag = True
                    break
                
                # Xử lý file links
                if result.links:
                    # print(f"có thêm link phụ: {result.links}\n")
                    for link in result.links.get("external", []) + result.links.get("internal", []):
                        if isinstance(link, dict) and 'href' in link:
                            link_url = link['href']
                        elif isinstance(link, str):
                            link_url = link
                        else:
                            print(f"Link không hợp lệ: {link}\n")
                            continue
                            
                        if await is_file_url(link_url):
                            print(f"Đang xử lý file: {link_url}\n")
                            file_data = await download_file(link_url)
                            if file_data:
                                file_content = await extract_file_content(file_data, link_url)
                                print(f"file content: {file_content}\n")
                                # results[-1] += f"\n\n#### Nội dung từ file {link_url}:\n{file_content}"
                                
                                # Tìm dòng chứa file url và thêm file content vào ngay sau dòng đó
                                markdown_content = markdown_content.replace(f"({link_url})", f"({link_url})\n#### Nội dung từ file {link_url}:\n{file_content}")

                # Process và lưu ngay vào file
                markdown_content = re.sub(r'^#+?\s*Mục lục\s*\n', '', markdown_content, flags=re.MULTILINE)
                markdown_content = re.sub(r'\bMục lục\b', '', markdown_content)
                with open(fit_file_path, "a", encoding="utf-8") as f:  # Append mode
                    f.write(f'##{markdown_content}\n')
                article_count += 1

            page_num += 1
        except Exception as e:
            print(f"Lỗi tại page {page_num} của {url}: {e}. Bỏ qua và tiếp tục.\n")
            page_num += 1  # Tiếp tục page tiếp theo dù error

    print(f"Đã lưu {article_count} bài viết vào file: {fit_file_path}\n")
    return []  # Không cần return results lớn

async def my_crawler_parallel():
    """Crawl song song nhiều URL và lưu kết quả ngay sau mỗi URL."""
    print("\n=== 3. Fit Markdown with LLM Content Filter ===\n")

    urls = [
        # "https://bvnguyentriphuong.com.vn/thong-tin-benh-vien",
        # "https://bvnguyentriphuong.com.vn/hoat-dong-doan-the",
        # "https://bvnguyentriphuong.com.vn/thong-tin-khoa-hoc",
        # "https://bvnguyentriphuong.com.vn/pho-bien-phap-luat",
        # "https://bvnguyentriphuong.com.vn/van-ban-trien-khai-noi-bo",
        # "https://bvnguyentriphuong.com.vn/hoat-dong-khen-thuong-tam-guong-trong-bv",


        "https://bvnguyentriphuong.com.vn/khoa-kham-benh",
        

        "https://bvnguyentriphuong.com.vn/noi-tim-mach",
        "https://bvnguyentriphuong.com.vn/tim-mach-can-thiep",
        "https://bvnguyentriphuong.com.vn/noi-tieu-hoa",
        "https://bvnguyentriphuong.com.vn/noi-tiet",
        "https://bvnguyentriphuong.com.vn/noi-tam-than-kinh",
        "https://bvnguyentriphuong.com.vn/noi-than-tiet-nieu",
        "https://bvnguyentriphuong.com.vn/than-loc-mau",
        "https://bvnguyentriphuong.com.vn/co-xuong-khop",
        "https://bvnguyentriphuong.com.vn/noi-ho-hap",
        # "https://bvnguyentriphuong.com.vn/lao-khoa",
        "https://bvnguyentriphuong.com.vn/noi-tong-hop",
        "https://bvnguyentriphuong.com.vn/cap-cuu",
        # "https://bvnguyentriphuong.com.vn/hoi-suc-tich-cuc-chong-doc",
        # "https://bvnguyentriphuong.com.vn/khoa-nhi",
        "https://bvnguyentriphuong.com.vn/y-hoc-co-truyen",
        # "https://bvnguyentriphuong.com.vn/huyet-hoc-truyen-mau",


        "https://bvnguyentriphuong.com.vn/ngoai-tong-hop",
        "https://bvnguyentriphuong.com.vn/ngoai-tieu-hoa",
        "https://bvnguyentriphuong.com.vn/ngoai-than-kinh",
        "https://bvnguyentriphuong.com.vn/chan-thuong-chinh-hinh",
        "https://bvnguyentriphuong.com.vn/ngoai-than-tiet-nieu",
        "https://bvnguyentriphuong.com.vn/san-phu-khoa",
        "https://bvnguyentriphuong.com.vn/gay-me-hoi-suc",
        "https://bvnguyentriphuong.com.vn/ung-buou",
        "https://bvnguyentriphuong.com.vn/ngoai-long-nguc-mach-mau",


        "https://bvnguyentriphuong.com.vn/khoa-mat",
        "https://bvnguyentriphuong.com.vn/tai-mui-hong",
        "https://bvnguyentriphuong.com.vn/rang-ham-mat",
        "https://bvnguyentriphuong.com.vn/benh-ky-sinh-trung",
        "https://bvnguyentriphuong.com.vn/benh-truyen-nhiem",
        "https://bvnguyentriphuong.com.vn/benh-hoc-da",
        "https://bvnguyentriphuong.com.vn/mien-dich-lam-sang",
        "https://bvnguyentriphuong.com.vn/benh-nghe-nghiep",
        "https://bvnguyentriphuong.com.vn/benh-di-truyen",


        "https://bvnguyentriphuong.com.vn/chan-doan-hinh-anh",
        "https://bvnguyentriphuong.com.vn/xet-nghiem",
        "https://bvnguyentriphuong.com.vn/noi-soi",
        "https://bvnguyentriphuong.com.vn/tham-do-chuc-nang",
        "https://bvnguyentriphuong.com.vn/giai-phau-benh",
        "https://bvnguyentriphuong.com.vn/dinh-duong",
        "https://bvnguyentriphuong.com.vn/kiem-soat-nhiem-khuan",
        "https://bvnguyentriphuong.com.vn/vat-ly-tri-lieu",
        "https://bvnguyentriphuong.com.vn/y-hoc-du-phong",
        "https://bvnguyentriphuong.com.vn/y-hoc-hat-nhan",  # Sửa khoảng trắng thừa


        "https://bvnguyentriphuong.com.vn/dieu-duong",
        "https://bvnguyentriphuong.com.vn/hoat-dong-duoc",
        "https://bvnguyentriphuong.com.vn/kham-da-lieu-chuyen-sau",
        "https://bvnguyentriphuong.com.vn/tham-my",


        "https://bvnguyentriphuong.com.vn/phac-do-dieu-tri",
        "https://bvnguyentriphuong.com.vn/tai-lieu-chuyen-mon",
        "https://bvnguyentriphuong.com.vn/quy-trinh-thu-tuc-hanh-chinh",
        "https://bvnguyentriphuong.com.vn/nghien-cuu-duoc-dang-tai-tren-tap-chi-quoc-te",
        "https://bvnguyentriphuong.com.vn/nghien-cuu-noi-bo-va-dang-tai-tap-chi-trong-nuoc",
        "https://bvnguyentriphuong.com.vn/nghien-cuu-khoa-hoc-va-thu-nghiem-lam-sang",


        "https://bvnguyentriphuong.com.vn/cau-lac-bo-benh-nhan",
        "https://bvnguyentriphuong.com.vn/bac-si-tu-van",

        
        "https://bvnguyentriphuong.com.vn/he-thong-thanh-toan-the",
        "https://bvnguyentriphuong.com.vn/phan-mem-dat-hen",


        "https://bvnguyentriphuong.com.vn/doanh-nghiep-doi-tac",
        "https://bvnguyentriphuong.com.vn/tin-tu-cac-co-so-y-te",
        "https://bvnguyentriphuong.com.vn/tin-tu-doanh-nghiep",


        "https://bvnguyentriphuong.com.vn/lieu-thuoc-tinh-than",
        "https://bvnguyentriphuong.com.vn/kien-thuc-cho-nguoi-benh",
        "https://bvnguyentriphuong.com.vn/tam-ly"
    ]

    # Chia batch URLs dựa trên env từ GitHub Actions
    batch_index = int(os.getenv('BATCH_INDEX', 0))
    num_batches = int(os.getenv('NUM_BATCHES', 1))
    batch_size = len(urls) // num_batches
    start = batch_index * batch_size
    end = start + batch_size if batch_index < num_batches - 1 else len(urls)
    urls = urls[start:end]

    async with AsyncWebCrawler() as crawler:
        # Giới hạn concurrent tasks để tránh rate limit/hết tài nguyên
        semaphore = asyncio.Semaphore(5)  # Giới hạn 5 URLs đồng thời
        
        async def limited_crawl(url):
            async with semaphore:
                try:
                    return await crawl_single_url(crawler, url)
                except Exception as e:
                    print(f"Lỗi toàn bộ URL {url}: {e}. Bỏ qua.\n")
                    return []

        # Chạy crawl song song cho tất cả URL
        tasks = [limited_crawl(url) for url in urls]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Xử lý lỗi (nếu có)
        for url, results in zip(urls, all_results):
            if isinstance(results, Exception):
                print(f"Lỗi khi crawl {url}: {results}\n")


async def main():
    """Run all demo functions sequentially"""
    print("=== Comprehensive Crawl4AI Demo ===")
    print("Note: Some examples require API keys or other configurations")

    
    
    await my_crawler_parallel()
    

    # Clean up any temp files that may have been created
    print("\n=== Demo Complete ===")
    print("Check for any generated files (screenshots, PDFs) in the current directory")


if __name__ == "__main__":
    asyncio.run(main())