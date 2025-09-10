# 병렬 크롤링이 적용된 연합뉴스 아카이브 크롤러

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random
import json
from datetime import datetime, timedelta
import re
import os
from concurrent.futures import ThreadPoolExecutor

# --- 설정 ---
BASE_ARCHIVE_INDEX_URL = "https://www.yna.co.kr/sitemap/index"
YONHAP_BASE_URL = "https://www.yna.co.kr"
OUTPUT_JSON_FILE ='c:/Users/nini/Desktop/NOLB/data/1.jsonl'
CRAWL_DELAY_MIN = 2
CRAWL_DELAY_MAX = 4
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

START_YEAR = 2019
START_MONTH = 1
END_YEAR = 2019
END_MONTH = 1

DISALLOWED_PATTERNS = [
    r'\/\*?\*cp=',
    r'\/view\/AEN.*', r'\/view\/ACK.*', r'\/view\/AJP.*', r'\/view\/AAR.*',
    r'\/view\/ASP.*', r'\/view\/AFR.*',
    r'\/hc\.html',
    r'\/search\/', r'\/search\/\*?\*query=',
    r'\/did\/', r'\/program\/', r'\/web\/', r'\/irclub\/', r'\/changwon\/',
    r'\/gangwon-do\/', r'\/coronavirus\/',
    r'\/view\/AKR20221115124100505'
]

def is_allowed_url(url):
    path = url.replace(YONHAP_BASE_URL, "")
    for pattern in DISALLOWED_PATTERNS:
        if re.search(pattern, path):
            return False
    return True

def save_article_to_jsonl(article_data):
    with open(OUTPUT_JSON_FILE, 'a', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False)
        f.write('\n')

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

def get_html_soup(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"에러: {url} 요청 실패 (시도 {attempt+1}/{max_retries}) - {e}")
            time.sleep(random.uniform(CRAWL_DELAY_MAX, CRAWL_DELAY_MAX * 2))
    return None

def fetch_article_details(article_url):
    soup = get_html_soup(article_url)
    if not soup:
        return {"content": None, "pubDate": None, "journalist": None, "category": None}

    content_text = None
    content_div = soup.find('div', class_='story-news article') or soup.find('article', id='article-view-content-div')
    if content_div:
        content_text = ' '.join(content_div.get_text(separator=' ', strip=True).split())

    pub_date_str = None
    match_date = re.search(r'AKR(\d{8})', article_url)
    if match_date:
        try:
            pub_date_str = datetime.strptime(match_date.group(1), '%Y%m%d').isoformat()
        except ValueError:
            pass

    journalist = None
    tag = soup.find('p', class_='byline')
    if tag:
        journalist = tag.get_text(strip=True).replace("기자", "").replace(":", "").strip()

    category = None
    meta = soup.find('meta', property='article:section')
    if meta and 'content' in meta.attrs:
        category = meta['content']
    return {
        "content": content_text,
        "pubDate": pub_date_str,
        "journalist": journalist,
        "category": category
    }

def process_article(article_tag):
    try:
        title = article_tag.get_text(strip=True)
        rel_url = article_tag.get('href')
        if not rel_url:
            return None

        full_url = urljoin(YONHAP_BASE_URL, rel_url)
        if '/view/' not in full_url or not is_allowed_url(full_url):
            return None

        print(f"    - 크롤링: {title} ({full_url})")
        details = fetch_article_details(full_url)
        time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))
        if details["content"]:
            return {
                "id": full_url.split('/')[-1].replace('.html', '').replace('.htm', ''),
                "url": full_url,
                "title": title,
                "pubDate": details["pubDate"],
                "media": "연합뉴스",
                "content": details["content"],
                "journalist": details["journalist"],
                "category": details["category"],
                "crawled_at": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"    [오류] {e}")
    return None

def start_archive_crawling():
    print("--- 연합뉴스 아카이브 크롤링 시작 ---")
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            if (year == START_YEAR and month < START_MONTH) or (year == END_YEAR and month > END_MONTH):
                continue

            print(f"\n--- {year}-{month:02d} ---")
            days = (datetime(year + (month // 12), (month % 12) + 1, 1) - datetime(year, month, 1)).days
            for day in range(1, days + 1):
                for page in range(1, 3):
                    url = f"{YONHAP_BASE_URL}/sitemap/articles/{year}/{month:02d}/{day:02d}-{page}.htm"
                    print(f"  날짜 페이지: {url}")
                    soup = get_html_soup(url)
                    if not soup:
                        continue
                    article_tags = soup.select('ul#sitemap-list a')
                    if not article_tags:
                        print("    기사 없음")
                        continue
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        results = executor.map(process_article, article_tags)
                        for item in results:
                            if item:
                                save_article_to_jsonl(item)

if __name__ == "__main__":
    start_archive_crawling()
    print("\n✅ 크롤링 완료")
