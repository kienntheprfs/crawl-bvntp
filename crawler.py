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

import re  # Thêm import re

__cur_dir__ = Path(__file__).parent


async def crawl_single_url(crawler, url: str) -> List[CrawlResult]:
    """Crawl một URL với logic phân trang và trả về danh sách kết quả."""
    filter_chain = FilterChain([DomainFilter(allowed_domains=["bvnguyentriphuong.com.vn"])])
    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=1,
        filter_chain=filter_chain
    )

    results: List[CrawlResult] = []
    page_num = 1
    stop_flag = False

    while not stop_flag and page_num == 1:
        page_url = f"{url}/{page_num}"
        print(f"Crawling page: {page_url}")

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

        for result in one_pagination_results:
            if "Danh mục chưa có bài viết" in result.markdown.fit_markdown:
                print(f"Đã dừng tại trang {page_num}: Danh mục chưa có bài viết")
                stop_flag = True
                break

        results += one_pagination_results[1:]  # Bỏ trang danh sách link các bài viết
        page_num += 1

    # Lưu kết quả ngay sau khi crawl xong URL
    # safe_url = re.sub(r'[^\w\-]', '_', url).replace('https___', '')[:100]
    
    # Chỉ lấy phần cuối của URL làm tên file
    safe_url = "_".join(url.split('/')[3:])  # Lấy phần cuối của URL bỏ domain bệnh viện đi (ví dụ: thong-tin-benh-vien)
    fit_file_path = os.path.join("final_bvntp", f"{safe_url}.md")

    processed_contents = []
    for i, result in enumerate(results, start=1):
        markdown_content = result.markdown.fit_markdown
        markdown_content = re.sub(r'^#+?\s*Mục lục\s*\n', '', markdown_content, flags=re.MULTILINE)
        markdown_content = re.sub(r'\bMục lục\b', '', markdown_content)
        processed_contents.append(f'##{markdown_content}')

    total_content = "".join(processed_contents)

    os.makedirs("final_bvntp", exist_ok=True)
    with open(fit_file_path, "w", encoding="utf-8") as f:
        f.write(total_content)
    print(f"Đã lưu {len(results)} bài viết vào file: {fit_file_path}")

    return results


async def my_crawler_parallel():
    """Crawl song song nhiều URL và lưu kết quả ngay sau mỗi URL."""
    print("\n=== 3. Fit Markdown with LLM Content Filter ===")

    urls = [
        # "https://bvnguyentriphuong.com.vn/thong-tin-benh-vien",
        # "https://bvnguyentriphuong.com.vn/hoat-dong-doan-the",
        # "https://bvnguyentriphuong.com.vn/thong-tin-khoa-hoc",
        # "https://bvnguyentriphuong.com.vn/pho-bien-phap-luat",
        # "https://bvnguyentriphuong.com.vn/van-ban-trien-khai-noi-bo",
        # "https://bvnguyentriphuong.com.vn/hoat-dong-khen-thuong-tam-guong-trong-bv",

        # "https://bvnguyentriphuong.com.vn/khoa-kham-benh",
        
        # "https://bvnguyentriphuong.com.vn/noi-tim-mach",
        # "https://bvnguyentriphuong.com.vn/tim-mach-can-thiep",
        # "https://bvnguyentriphuong.com.vn/noi-tieu-hoa",
        # "https://bvnguyentriphuong.com.vn/noi-tiet",
        # "https://bvnguyentriphuong.com.vn/noi-tam-than-kinh",
        # "https://bvnguyentriphuong.com.vn/noi-than-tiet-nieu",
        # "https://bvnguyentriphuong.com.vn/than-loc-mau",
        # "https://bvnguyentriphuong.com.vn/co-xuong-khop",
        # "https://bvnguyentriphuong.com.vn/noi-ho-hap",
        # # "https://bvnguyentriphuong.com.vn/lao-khoa",
        # "https://bvnguyentriphuong.com.vn/noi-tong-hop",
        # "https://bvnguyentriphuong.com.vn/cap-cuu",
        # # "https://bvnguyentriphuong.com.vn/hoi-suc-tich-cuc-chong-doc",
        # # "https://bvnguyentriphuong.com.vn/khoa-nhi",
        # "https://bvnguyentriphuong.com.vn/y-hoc-co-truyen",
        # # "https://bvnguyentriphuong.com.vn/huyet-hoc-truyen-mau"

        "https://bvnguyentriphuong.com.vn/noi-tam-than-kinh"
    ]

    async with AsyncWebCrawler() as crawler:
        # Chạy crawl song song cho tất cả URL
        tasks = [crawl_single_url(crawler, url) for url in urls]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Xử lý lỗi (nếu có)
        for url, results in zip(urls, all_results):
            if isinstance(results, Exception):
                print(f"Lỗi khi crawl {url}: {results}")


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