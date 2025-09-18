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


async def my_deep_crawler():
    """Deep crawling with BFS strategy"""
    print("\n=== 6. Deep Crawling ===")

    filter_chain = FilterChain([DomainFilter(allowed_domains=["bvnguyentriphuong.com.vn"])])

    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=1, max_pages=20, filter_chain=filter_chain
    )

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url="https://bvnguyentriphuong.com.vn/thong-tin-benh-vien",
            config=CrawlerRunConfig(deep_crawl_strategy=deep_crawl_strategy),
        )

        print(f"Deep crawl returned {len(results)} pages:")
        for i, result in enumerate(results):
            depth = result.metadata.get("depth", "unknown")
            print(f"  {i + 1}. {result.url} (Depth: {depth})")
            # Save extracted content to a markdown file, create the md file if it doesn't exist
            with open(f"{__cur_dir__}/deep_crawl/deep_crawl_{i}.md", "w", encoding="utf-8") as f:
                f.write(result.markdown.raw_markdown)
    
async def my_crawler():
    """Generate focused markdown with LLM content filter"""
    print("\n=== 3. Fit Markdown with LLM Content Filter ===")

    urls = [
        "https://bvnguyentriphuong.com.vn/thong-tin-benh-vien"
        # "https://bvnguyentriphuong.com.vn/hoat-dong-doan-the",
        # "https://bvnguyentriphuong.com.vn/thong-tin-khoa-hoc",
        # "https://bvnguyentriphuong.com.vn/pho-bien-phap-luat",
        # "https://bvnguyentriphuong.com.vn/van-ban-trien-khai-noi-bo",
        # "https://bvnguyentriphuong.com.vn/hoat-dong-khen-thuong-tam-guong-trong-bv",
    ]

    filter_chain = FilterChain([DomainFilter(allowed_domains=["bvnguyentriphuong.com.vn"])])

    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=1
        # , max_pages=20
        , filter_chain=filter_chain
    )

    async with AsyncWebCrawler() as crawler:
        #  Từ một url link (danh sách link các bài viết), dùng Deep crawl để lấy nội dung từng bài viết cụ thể
        for url in urls:
            results: List[CrawlResult] = []

            # Crawl trang chính và các trang phân trang
            page_num = 1
            stop_flag = False
            while stop_flag is not True:
                # Tạo URL cho trang phân trang
                page_url = f"{url}/{page_num}"
                print(f"Crawling page: {page_url}")

                one_pagination_results: List[CrawlResult] = await crawler.arun(
                    url=page_url,
                    config=CrawlerRunConfig(
                        markdown_generator=DefaultMarkdownGenerator(
                            content_filter=PruningContentFilter()
                        ),
                        deep_crawl_strategy=deep_crawl_strategy,
                        css_selector="div.col-lg-8.col-md-7",  # Giới hạn crawl chỉ trong div này
                        excluded_selector='h2.strong.itext-red.mb-15, h2.strong.itext-red.mb-15 ~ *, .pagination.justify-content-center' # Loại trừ h2 và tất cả phần tử sau nó (sibling selectors), loại trừ phần pagination luôn
                    ),
                )

                for result in one_pagination_results:
                    if "Danh mục chưa có bài viết" in result.markdown.fit_markdown:
                        print(f"Đã dừng tại trang {page_num}: Danh mục chưa có bài viết")
                        stop_flag = True
                        break
                        
                # Bỏ trang danh sách link các bài viết
                results += one_pagination_results[1:]

                page_num += 1

            # Bỏ trang danh sách link các bài viết
            # results = results[1:]

            
            all_articles_one_file()
            # each_article_one_file()

        # Lưu results vào một file, tiêu đề là url
        def all_articles_one_file():
            # Làm sạch URL gốc để tạo tên file hợp lệ
            safe_url = re.sub(r'[^\w\-]', '_', url)  # Thay ký tự không hợp lệ bằng '_'
            safe_url = safe_url.replace('https___', '')  # Loại bỏ phần https://
            safe_url = safe_url[:100]  # Giới hạn độ dài tên file để tránh lỗi

            # Lưu toàn bộ results vào một file duy nhất cho URL này
            fit_file_path = os.path.join("final_bvntp", f"{safe_url}.md")
            
            # Thu thập và xử lý nội dung từ tất cả results
            processed_contents = []
            for i, result in enumerate(results, start=1):
                # Lấy nội dung markdown từ result
                markdown_content = result.markdown.fit_markdown

                # Xóa chữ "Mục lục" (bao gồm cả trường hợp là tiêu đề markdown như ## Mục lục)
                markdown_content = re.sub(r'^#+?\s*Mục lục\s*\n', '', markdown_content, flags=re.MULTILINE)
                markdown_content = re.sub(r'\bMục lục\b', '', markdown_content)

                # Tạo tiêu đề cho từng bài viết con (cấp 2, với URL ngắn gọn)
                # short_url = result.url.split('/')[-1] if '/' in result.url else result.url  # Lấy phần cuối URL làm tiêu đề
                # short_url = re.sub(r'[^\w\-]', '_', short_url)[:50]  # Làm sạch và giới hạn
                # article_title = f"## Bài viết {i}: {short_url}\n\n{markdown_content}\n\n---\n\n"  # Thêm phân cách

                # processed_contents.append(article_title)

                processed_contents.append(f'##{markdown_content}')

                # Tùy chọn: In stats để theo dõi
                # print(f"Xử lý {result.url}: {len(markdown_content)} chars")

            # Nối tất cả nội dung và thêm tiêu đề chính cho file (cấp 1)
            # total_content = f"# Nội dung từ URL: {url}\n\n" + "".join(processed_contents)
            
            total_content = "".join(processed_contents)

            # Ghi nội dung đã xử lý xuống file
            with open(fit_file_path, "w", encoding="utf-8") as f:
                f.write(total_content)

            print(f"Đã lưu {len(results)} bài viết vào file: {fit_file_path}")
        
        
        # Lưu mỗi bài viết một file
        def each_article_one_file():
                for result in results:
                    # Print stats and save the fit markdown
                    # print(f"Raw: {len(result.markdown.raw_markdown)} chars")
                    # print(f"Fit: {len(result.markdown.fit_markdown)} chars")

                    # depth = result.metadata.get("depth", "unknown")
                    # print(f"{result.url} (Depth: {depth})")



                    # Đường dẫn thư mục lưu file
                    cur_dir = os.path.dirname(os.path.abspath(__file__))
                    os.makedirs(cur_dir, exist_ok=True)

                    # Làm sạch URL để tạo tên file hợp lệ
                    safe_url = re.sub(r'[^\w\-]', '_', result.url)  # Thay ký tự không hợp lệ bằng '_'
                    safe_url = safe_url.replace('https___', '')  # Loại bỏ phần https://
                    safe_url = safe_url[:100]  # Giới hạn độ dài tên file để tránh lỗi

                    # Lưu raw markdown
                    # raw_file_path = os.path.join(cur_dir+"/final_bvntp", f"raw_markdown_{safe_url}.md")
                    # with open(raw_file_path, "w", encoding="utf-8") as f:
                    #     f.write(result.markdown.raw_markdown)
                    
                    # Lưu fit markdown
                    fit_file_path = os.path.join(cur_dir+"/final_bvntp", f"fit_markdown_{safe_url}.md")
                    with open(fit_file_path, "w", encoding="utf-8") as f:
                        # Lấy nội dung markdown từ result
                        markdown_content = result.markdown.fit_markdown

                        # Xóa chữ "Mục lục" (bao gồm cả trường hợp là tiêu đề markdown như ## Mục lục)
                        markdown_content = re.sub(r'^#+?\s*Mục lục\s*\n', '', markdown_content, flags=re.MULTILINE)
                        markdown_content = re.sub(r'\bMục lục\b', '', markdown_content)

                        # Thêm dấu # vào đầu file (giả sử là tiêu đề cấp 2)
                        final_content = f"##{markdown_content}"

                        # Ghi nội dung đã xử lý xuống file
                        f.write(final_content)
            

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

    while not stop_flag:
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
        "https://bvnguyentriphuong.com.vn/khoa-nhi",
        "https://bvnguyentriphuong.com.vn/y-hoc-co-truyen",
        # "https://bvnguyentriphuong.com.vn/huyet-hoc-truyen-mau"
    ]

    async with AsyncWebCrawler() as crawler:
        # Chạy crawl song song cho tất cả URL
        tasks = [crawl_single_url(crawler, url) for url in urls]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Xử lý lỗi (nếu có)
        for url, results in zip(urls, all_results):
            if isinstance(results, Exception):
                print(f"Lỗi khi crawl {url}: {results}")





async def demo_basic_crawl():
    """Basic web crawling with markdown generation"""
    print("\n=== 1. Basic Web Crawling ===")
    async with AsyncWebCrawler(config = BrowserConfig(
        viewport_height=800,
        viewport_width=1200,
        headless=True,
        verbose=True,
    )) as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url="https://news.ycombinator.com/"
        )

        for i, result in enumerate(results):
            print(f"Result {i + 1}:")
            print(f"Success: {result.success}")
            if result.success:
                print(f"Markdown length: {len(result.markdown.raw_markdown)} chars")
                print(f"First 100 chars: {result.markdown.raw_markdown[:100]}...")
                print(f"Raw HTML: {result.markdown}...")
            else:
                print("Failed to crawl the URL")

async def demo_parallel_crawl():
    """Crawl multiple URLs in parallel"""
    print("\n=== 2. Parallel Crawling ===")

    urls = [
        "https://news.ycombinator.com/",
        "https://example.com/",
        "https://httpbin.org/html",
    ]

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun_many(
            urls=urls,
        )

        print(f"Crawled {len(results)} URLs in parallel:")
        for i, result in enumerate(results):
            print(
                f"  {i + 1}. {result.url} - {'Success' if result.success else 'Failed'}"
            )

async def demo_fit_markdown():
    """Generate focused markdown with LLM content filter"""
    print("\n=== 3. Fit Markdown with LLM Content Filter ===")

    async with AsyncWebCrawler() as crawler:
        result: CrawlResult = await crawler.arun(
            url = "https://bvnguyentriphuong.com.vn/pho-bien-phap-luat/mot-so-cau-hoi-thuong-gap-va-quy-dinh-tuong-ung-cua-phap-luat-ve-dau-thau-p2",
            config=CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter()
                )
            ),
        )

        # Print stats and save the fit markdown
        print(f"Raw: {len(result.markdown.raw_markdown)} chars")
        print(f"Fit: {len(result.markdown.fit_markdown)} chars")
        
        # Save the raw markdown to a file
        with open(f"{__cur_dir__}/raw_markdown.md", "w", encoding="utf-8") as f:
            f.write(result.markdown.raw_markdown)
        # Save the fit markdown to a file
        with open(f"{__cur_dir__}/fit_markdown.md", "w", encoding="utf-8") as f:
            f.write(result.markdown.fit_markdown)

async def demo_llm_structured_extraction_no_schema():
    # Create a simple LLM extraction strategy (no schema required)
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="groq/qwen-2.5-32b",
            api_token="env:GROQ_API_KEY",
        ),
        instruction="This is news.ycombinator.com, extract all news, and for each, I want title, source url, number of comments.",
        extract_type="schema",
        schema="{title: string, url: string, comments: int}",
        extra_args={
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        verbose=True,
    )

    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            "https://news.ycombinator.com/", config=config
        )

        for result in results:
            print(f"URL: {result.url}")
            print(f"Success: {result.success}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")

async def demo_css_structured_extraction_no_schema():
    """Extract structured data using CSS selectors"""
    print("\n=== 5. CSS-Based Structured Extraction ===")
    # Sample HTML for schema generation (one-time cost)
    sample_html = """
<div class="body-post clear">
    <a class="story-link" href="https://thehackernews.com/2025/04/malicious-python-packages-on-pypi.html">
        <div class="clear home-post-box cf">
            <div class="home-img clear">
                <div class="img-ratio">
                    <img alt="..." src="...">
                </div>
            </div>
            <div class="clear home-right">
                <h2 class="home-title">Malicious Python Packages on PyPI Downloaded 39,000+ Times, Steal Sensitive Data</h2>
                <div class="item-label">
                    <span class="h-datetime"><i class="icon-font icon-calendar"></i>Apr 05, 2025</span>
                    <span class="h-tags">Malware / Supply Chain Attack</span>
                </div>
                <div class="home-desc"> Cybersecurity researchers have...</div>
            </div>
        </div>
    </a>
</div>
    """

    # Check if schema file exists
    schema_file_path = f"{__cur_dir__}/tmp/schema.json"
    if os.path.exists(schema_file_path):
        with open(schema_file_path, "r") as f:
            schema = json.load(f)
    else:
        # Generate schema using LLM (one-time setup)
        schema = JsonCssExtractionStrategy.generate_schema(
            html=sample_html,
            llm_config=LLMConfig(
                provider="groq/qwen-2.5-32b",
                api_token="env:GROQ_API_KEY",
            ),
            query="From https://thehackernews.com/, I have shared a sample of one news div with a title, date, and description. Please generate a schema for this news div.",
        )

    print(f"Generated schema: {json.dumps(schema, indent=2)}")
    # Save the schema to a file , and use it for future extractions, in result for such extraction you will call LLM once
    with open(f"{__cur_dir__}/tmp/schema.json", "w") as f:
        json.dump(schema, f, indent=2)

    # Create no-LLM extraction strategy with the generated schema
    extraction_strategy = JsonCssExtractionStrategy(schema)
    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

    # Use the fast CSS extraction (no LLM calls during extraction)
    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            "https://thehackernews.com", config=config
        )

        for result in results:
            print(f"URL: {result.url}")
            print(f"Success: {result.success}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")

async def demo_deep_crawl():
    """Deep crawling with BFS strategy"""
    print("\n=== 6. Deep Crawling ===")

    filter_chain = FilterChain([DomainFilter(allowed_domains=["bvnguyentriphuong.com.vn"])])

    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=1, max_pages=20, filter_chain=filter_chain
    )

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url="https://bvnguyentriphuong.com.vn/",
            config=CrawlerRunConfig(deep_crawl_strategy=deep_crawl_strategy),
        )

        print(f"Deep crawl returned {len(results)} pages:")
        for i, result in enumerate(results):
            depth = result.metadata.get("depth", "unknown")
            print(f"  {i + 1}. {result.url} (Depth: {depth})")
            # Save extracted content to a markdown file, create the md file if it doesn't exist
            with open(f"{__cur_dir__}/deep_crawl/deep_crawl_{i}.md", "w", encoding="utf-8") as f:
                f.write(result.markdown.raw_markdown)

async def demo_js_interaction():
    """Execute JavaScript to load more content"""
    print("\n=== 7. JavaScript Interaction ===")

    # A simple page that needs JS to reveal content
    async with AsyncWebCrawler(config=BrowserConfig(headless=False)) as crawler:
        # Initial load

        news_schema = {
            "name": "news",
            "baseSelector": "tr.athing",
            "fields": [
                {
                    "name": "title",
                    "selector": "span.titleline",
                    "type": "text",
                }
            ],
        }
        results: List[CrawlResult] = await crawler.arun(
            url="https://news.ycombinator.com",
            config=CrawlerRunConfig(
                session_id="hn_session",  # Keep session
                extraction_strategy=JsonCssExtractionStrategy(schema=news_schema),
            ),
        )

        news = []
        for result in results:
            if result.success:
                data = json.loads(result.extracted_content)
                news.extend(data)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")

        print(f"Initial items: {len(news)}")

        # Click "More" link
        more_config = CrawlerRunConfig(
            js_code="document.querySelector('a.morelink').click();",
            js_only=True,  # Continue in same page
            session_id="hn_session",  # Keep session
            extraction_strategy=JsonCssExtractionStrategy(
                schema=news_schema,
            ),
        )

        result: List[CrawlResult] = await crawler.arun(
            url="https://news.ycombinator.com", config=more_config
        )

        # Extract new items
        for result in results:
            if result.success:
                data = json.loads(result.extracted_content)
                news.extend(data)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")
        print(f"Total items: {len(news)}")

async def demo_media_and_links():
    """Extract media and links from a page"""
    print("\n=== 8. Media and Links Extraction ===")

    async with AsyncWebCrawler() as crawler:
        result: List[CrawlResult] = await crawler.arun("https://en.wikipedia.org/wiki/Main_Page")

        for i, result in enumerate(result):
            # Extract and save all images
            images = result.media.get("images", [])
            print(f"Found {len(images)} images")

            # Extract and save all links (internal and external)
            internal_links = result.links.get("internal", [])
            external_links = result.links.get("external", [])
            print(f"Found {len(internal_links)} internal links")
            print(f"Found {len(external_links)} external links")

            # Print some of the images and links
            for image in images[:3]:
                print(f"Image: {image['src']}")
            for link in internal_links[:3]:
                print(f"Internal link: {link['href']}")
            for link in external_links[:3]:
                print(f"External link: {link['href']}")

            # # Save everything to files
            with open(f"{__cur_dir__}/tmp/images.json", "w") as f:
                json.dump(images, f, indent=2)

            with open(f"{__cur_dir__}/tmp/links.json", "w") as f:
                json.dump(
                    {"internal": internal_links, "external": external_links},
                    f,
                    indent=2,
                )

async def demo_screenshot_and_pdf():
    """Capture screenshot and PDF of a page"""
    print("\n=== 9. Screenshot and PDF Capture ===")

    async with AsyncWebCrawler() as crawler:
        result: List[CrawlResult] = await crawler.arun(
            # url="https://example.com",
            url="https://en.wikipedia.org/wiki/Giant_anteater",
            config=CrawlerRunConfig(screenshot=True, pdf=True),
        )

        for i, result in enumerate(result):
            # if result.screenshot_data:
            if result.screenshot:
                # Save screenshot
                screenshot_path = f"{__cur_dir__}/tmp/example_screenshot.png"
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(result.screenshot))
                print(f"Screenshot saved to {screenshot_path}")

            # if result.pdf_data:
            if result.pdf:
                # Save PDF
                pdf_path = f"{__cur_dir__}/tmp/example.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(result.pdf)
                print(f"PDF saved to {pdf_path}")

async def demo_proxy_rotation():
    """Proxy rotation for multiple requests"""
    print("\n=== 10. Proxy Rotation ===")

    # Example proxies (replace with real ones)
    proxies = [
        ProxyConfig(server="http://proxy1.example.com:8080"),
        ProxyConfig(server="http://proxy2.example.com:8080"),
    ]

    proxy_strategy = RoundRobinProxyStrategy(proxies)

    print(f"Using {len(proxies)} proxies in rotation")
    print(
        "Note: This example uses placeholder proxies - replace with real ones to test"
    )

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            proxy_rotation_strategy=proxy_strategy
        )

        # In a real scenario, these would be run and the proxies would rotate
        print("In a real scenario, requests would rotate through the available proxies")

async def demo_raw_html_and_file():
    """Process raw HTML and local files"""
    print("\n=== 11. Raw HTML and Local Files ===")

    raw_html = """
    <html><body>
        <h1>Sample Article</h1>
        <p>This is sample content for testing Crawl4AI's raw HTML processing.</p>
    </body></html>
    """

    # Save to file
    file_path = Path("docs/examples/tmp/sample.html").absolute()
    with open(file_path, "w") as f:
        f.write(raw_html)

    async with AsyncWebCrawler() as crawler:
        # Crawl raw HTML
        raw_result = await crawler.arun(
            url="raw:" + raw_html, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        )
        print("Raw HTML processing:")
        print(f"  Markdown: {raw_result.markdown.raw_markdown[:50]}...")

        # Crawl local file
        file_result = await crawler.arun(
            url=f"file://{file_path}",
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
        )
        print("\nLocal file processing:")
        print(f"  Markdown: {file_result.markdown.raw_markdown[:50]}...")

    # Clean up
    os.remove(file_path)
    print(f"Processed both raw HTML and local file ({file_path})")

async def main():
    """Run all demo functions sequentially"""
    print("=== Comprehensive Crawl4AI Demo ===")
    print("Note: Some examples require API keys or other configurations")

    # Run all demos
    # await demo_basic_crawl()
    # await demo_parallel_crawl()
    # await demo_fit_markdown()
    # await demo_llm_structured_extraction_no_schema()
    # await demo_css_structured_extraction_no_schema()
    # await demo_deep_crawl()
    # await demo_js_interaction()
    # await demo_media_and_links()
    # await demo_screenshot_and_pdf()
    # # await demo_proxy_rotation()
    # await demo_raw_html_and_file()
    
    # await my_crawler()
    await my_crawler_parallel()
    # await my_deep_crawler()

    # Clean up any temp files that may have been created
    print("\n=== Demo Complete ===")
    print("Check for any generated files (screenshots, PDFs) in the current directory")

if __name__ == "__main__":
    asyncio.run(main())