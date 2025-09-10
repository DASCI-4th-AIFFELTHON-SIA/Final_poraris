"""
Yonhap News 아카이브 크롤러 – 병렬 버전
------------------------------------
● 기존 기능(기사 필터·랜덤 딜레이·메타데이터 추출)은 그대로 유지
● 개선점
    1) 사이트맵 페이지를 병렬로 요청
    2) 기사 본문도 전역 ThreadPoolExecutor(워커 20개)로 병렬 요청
    3) requests.Session 을 스레드마다 독립적으로 사용해 race condition 방지
    4) JSONL 파일 기록 시 Lock 으로 동기화
"""

import requests, threading, time, random, json, re, os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ────────────────────────────── 설정값 ──────────────────────────────
BASE_ARCHIVE_INDEX_URL = "https://www.yna.co.kr/sitemap/index"
YONHAP_BASE_URL        = "https://www.yna.co.kr"
OUTPUT_JSON_FILE       = r"C:\\Users\\이름\\Desktop\\DS4\\AIFFELthon\\데이터\\yonhap_news_raw_data_archive_2017_3.jsonl"

USER_AGENT       = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CRAWL_DELAY_MIN  = 2
CRAWL_DELAY_MAX  = 4

START_YEAR, START_MONTH = 2017, 3   # inclusive
END_YEAR,   END_MONTH   = 2017, 3  # inclusive

PAGE_WORKERS    = 1    # sitemap 페이지 병렬 수
ARTICLE_WORKERS = 100   # 기사 병렬 수 (네트워크 상황에 맞게 조절)

DISALLOWED_PATTERNS = [
    r'/\*?\*cp=',
    r'/view/AEN.*', r'/view/ACK.*', r'/view/AJP.*', r'/view/AAR.*',
    r'/view/ASP.*', r'/view/AFR.*',
    r'/hc\.html',
    r'/search/', r'/search/\*?\*query=',
    r'/did/', r'/program/', r'/web/', r'/irclub/', r'/changwon/',
    r'/gangwon-do/', r'/coronavirus/',
    r'/view/AKR20221115124100505'
]

# ────────────────────── 내부 공용 도구 (thread‑safe) ──────────────────────
FILE_LOCK = threading.Lock()
crawled_urls = set()
if os.path.exists(OUTPUT_JSON_FILE):
    with open(OUTPUT_JSON_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                crawled_urls.add(data['url'])
            except json.JSONDecodeError:
                continue
    print(f"기존에 {len(crawled_urls)}개의 URL이 파일에서 로드되었습니다.")

_thread_local = threading.local()

def get_session():
    """스레드마다 독립적인 requests.Session 반환"""
    if not hasattr(_thread_local, "sess"):
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        _thread_local.sess = s
    return _thread_local.sess

def is_allowed_url(url: str) -> bool:
    path = url.replace(YONHAP_BASE_URL, "")
    return not any(re.search(pat, path) for pat in DISALLOWED_PATTERNS)

def get_html_soup(url: str, max_retries: int = 3):
    sess = get_session()
    for attempt in range(max_retries):
        try:
            resp = sess.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"[에러] {url} (시도 {attempt+1}/{max_retries}) → {e}")
            time.sleep(random.uniform(CRAWL_DELAY_MAX, CRAWL_DELAY_MAX*2))
    return None

def save_article_to_jsonl(article_data: dict):
    """JSONL 파일 쓰기 – 동시 접근 보호"""
    with FILE_LOCK:
        with open(OUTPUT_JSON_FILE, "a", encoding="utf-8") as f:
            json.dump(article_data, f, ensure_ascii=False)
            f.write("\n")

# ────────────────────── 기사 세부 정보 추출 ──────────────────────
def fetch_article_details(article_url: str) -> dict:
    soup = get_html_soup(article_url)
    if not soup:
        return {"content": None, "pubDate": None, "journalist": None, "category": None}

    # 본문
    content_div = soup.find("div", class_="story-news article") \
                 or soup.find("article", id="article-view-content-div")
    content_text = None
    if content_div:
        content_text = " ".join(content_div.get_text(" ", strip=True).split())

    # 발행일(기사 URL 안의 AKRYYYYMMDD 패턴 활용)
    pub_date_iso = None

    # 1. div 태그의 data-published-time 속성 사용 (추천)
    update_time_div = soup.find('div', id='newsUpdateTime01')
    if update_time_div and 'data-published-time' in update_time_div.attrs:
        raw_datetime_str = update_time_div['data-published-time']
        try:
            # "YYYY-MM-DD HH:MM" 형식을 ISO 8601로 변환
            pub_date_iso = datetime.strptime(raw_datetime_str, '%Y-%m-%d %H:%M').isoformat()
        except ValueError:
            pass

    # 2. 만약 data-published-time이 없다면, 기존 URL 방식 또는 p 태그 텍스트 파싱으로 폴백 (선택 사항)
    if not pub_date_iso:
        # 기존 URL 방식 폴백 (AKRXXXXXXXX)
        m = re.search(r"AKR(\d{8})", article_url)
        if m:
            try:
                pub_date_iso = datetime.strptime(m.group(1), "%Y%m%d").isoformat()
            except ValueError:
                pass

    # 기자
    journalist = None
    byline = soup.find("p", class_="byline")
    if byline:
        journalist = byline.get_text(strip=True).replace("기자", "").replace(":", "").strip()

    # 카테고리
    category = None
    meta = soup.find("meta", property="article:section")
    if meta and "content" in meta.attrs:
        category = meta["content"]

    return {
        "content":    content_text,
        "pubDate":    pub_date_iso,
        "journalist": journalist,
        "category":   category
    }

# ────────────────────── 기사 태그 처리 (본문 병렬) ──────────────────────
def process_article(article_tag):
    try:
        title   = article_tag.get_text(strip=True)
        rel_url = article_tag.get("href")
        if not rel_url:
            return None

        full_url = urljoin(YONHAP_BASE_URL, rel_url)
        if full_url in crawled_urls:
            print(f"    ⏩ 이미 크롤링된 URL: {full_url}")
            return None

        if "/view/" not in full_url or not is_allowed_url(full_url):
            return None

        print(f"    ▶ {title} ({full_url})")
        details = fetch_article_details(full_url)
        time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))  # polite crawl

        if details["content"]:
            return {
                "id":        full_url.split("/")[-1].split(".")[0],
                "url":       full_url,
                "title":     title,
                "pubDate":   details["pubDate"],
                "media":     "연합뉴스",
                "content":   details["content"],
                "journalist":details["journalist"],
                "category":  details["category"],
                "crawled_at":datetime.now().isoformat()
            }
    except Exception as e:
        print(f"    [오류] {e}")
    return None

# ────────────────────── 사이트맵 페이지 처리 (기사 워커 활용) ──────────────────────
def process_sitemap_page(url: str, article_executor: ThreadPoolExecutor) -> int:
    soup = get_html_soup(url)
    if not soup:
        return 0
    article_tags = soup.select("ul#sitemap-list a")
    if not article_tags:
        return 0

    futures = [article_executor.submit(process_article, tag) for tag in article_tags]
    saved   = 0
    for fut in as_completed(futures):
        item = fut.result()
        if item:
            save_article_to_jsonl(item)
            saved += 1
    return saved

# ────────────────────── 메인 크롤러 ──────────────────────
def start_archive_crawling_parallel():
    print("=== 연합뉴스 아카이브 크롤링 (병렬) 시작 ===")

    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as article_pool, \
         ThreadPoolExecutor(max_workers=PAGE_WORKERS)    as page_pool:

        page_futs = []

        for year in range(START_YEAR, END_YEAR + 1):
            for month in range(1, 13):
                if (year == START_YEAR and month < START_MONTH) or \
                   (year == END_YEAR   and month > END_MONTH):
                    continue

                # 해당 월의 마지막 날 계산
                days_in_month = (datetime(year + (month // 12),
                                          (month % 12) + 1, 1)
                                 - datetime(year, month, 1)).days

                for day in range(1, days_in_month + 1):
                    for page in range(1, 3):  # 1~2페이지만 존재
                        sitemap_url = f"{YONHAP_BASE_URL}/sitemap/articles/{year}/{month:02d}/{day:02d}-{page}.htm"
                        print(f"[QUEUE] {sitemap_url}")
                        page_futs.append(
                            page_pool.submit(process_sitemap_page, sitemap_url, article_pool)
                        )

        # 진행 상황 수집
        total_saved = 0
        for fut in as_completed(page_futs):
            total_saved += fut.result()

    print(f"=== 크롤링 완료: 총 {total_saved:,}건 저장 ===")

# ────────────────────── 실행 스크립트 진입점 ──────────────────────
if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUTPUT_JSON_FILE), exist_ok=True)
    t0 = time.time()
    start_archive_crawling_parallel()
    print(f"소요 시간: {(time.time() - t0)/3600:.2f} 시간")
