import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random
import json
from datetime import datetime, timedelta
import re
import os

# --- 설정 ---
BASE_ARCHIVE_INDEX_URL = "https://www.yna.co.kr/sitemap/index"
YONHAP_BASE_URL = "https://www.yna.co.kr"
OUTPUT_JSON_FILE = "D:\\Users\\tonyn\\Desktop\\da_sci_4th\\AIFFEL_THON\\source\\yonhap_news_raw_data_archive.jsonl"
CRAWL_DELAY_MIN = 5 # 각 요청 간 최소 지연 시간 (초)
CRAWL_DELAY_MAX = 15 # 각 요청 간 최대 지연 시간 (초)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 크롤링 시작 및 종료 연월 설정 (10년치)
START_YEAR = 2025 # 2016/01/01부터 시작
START_MONTH = 7
END_YEAR = 2025
END_MONTH = 7 # 현재 2025년 7월까지 데이터 있다고 가정

# --- robots.txt Disallow 규칙 정의 ---
DISALLOWED_PATTERNS = [
    r'\/\*?\*cp=',
    r'\/view\/AEN.*', r'\/view\/ACK.*', r'\/view\/AJP.*', r'\/view\/AAR.*',
    r'\/view\/ASP.*', r'\/view\/AFR.*',
    r'\/hc\.html',
    r'\/search\/', # 이 부분이 중요! 검색 페이지 불허
    r'\/search\/\*?\*query=',
    r'\/did\/', r'\/program\/', r'\/web\/', r'\/irclub\/', r'\/changwon\/',
    r'\/gangwon-do\/', r'\/coronavirus\/',
    # --- 중요: robots.txt에서 가져온 모든 개별 기사 ID Disallow를 여기에 추가하세요 ---
    # 예시:
    r'\/view\/AKR20150422172700003', r'\/view\/AKR20140829043800065',
    r'\/view\/AKR20140829043851065', r'\/view\/AKR20170628100600004',
    r'\/view\/AKR20180312046500004', r'\/view\/AKR20001016000500007',
    r'\/view\/AKR20120627179800004', r'\/view\/AKR20120627179851004',
    r'\/view\/AKR20090217198200051', r'\/view\/AKR20200612149500005',
    r'\/view\/AKR20121210065200061', r'\/view\/AKR20121210099600061',
    r'\/view\/AKR20180323024000033', r'\/view\/AKR20121018033100014',
    r'\/view\/AKR20210225119251001', r'\/view\/AKR20210225119200001',
    r'\/view\/AKR20210225155200005', r'\/view\/AKR20111228151200061',
    r'\/view\/AKR20210528145800065', r'\/view\/AKR20210420149500051',
    r'\/view\/AKR20210420149551051', r'\/view\/AKR20071018085900004',
    r'\/view\/AKR20070709049600004', r'\/view\/AKR20080124092800004',
    r'\/view\/AKR20150728117000060', r'\/view\/AKR20100414090000017',
    r'\/view\/AKR20200428055400004', r'\/view\/MYH20140829007500038',
    r'\/view\/MYH20161104017200038', r'\/view\/MYH20121211002300038',
    r'\/view\/MYH20180323010400038', r'\/view\/PYH20191203158600013',
    r'\/view\/PYH20190918134800013', r'\/view\/PYH20190918134900013',
    r'\/view\/PYH20210225267400013', r'\/view\/IIS20110401000200365',
    r'\/view\/AKR20221115124100505'
]

# 이미 크롤링된 URL을 저장하여 중복 크롤링 방지 (재시작 시 유용)
# crawled_urls = set()
# if os.path.exists(OUTPUT_JSON_FILE):
#     with open(OUTPUT_JSON_FILE, 'r', encoding='utf-8') as f:
#         for line in f:
#             try:
#                 data = json.loads(line)
#                 crawled_urls.add(data['url'])
#             except json.JSONDecodeError:
#                 continue
#     print(f"기존에 {len(crawled_urls)}개의 URL이 파일에서 로드되었습니다.")


# --- 유틸리티 함수 ---
def is_allowed_url(url):
    """robots.txt 규칙에 따라 URL이 허용되는지 확인"""
    path = url.replace(YONHAP_BASE_URL, "") # Base URL 부분을 제거하여 경로만 비교
    for pattern in DISALLOWED_PATTERNS:
        if re.search(pattern, path):
            return False
    return True

def save_article_to_jsonl(article_data):
    """크롤링된 기사 데이터를 JSON Lines 형식으로 파일에 추가"""
    with open(OUTPUT_JSON_FILE, 'a', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False)
        f.write('\n')

def get_html_soup(url, max_retries=3):
    """URL에서 HTML을 가져와 BeautifulSoup 객체 반환 (재시도 포함)"""
    headers = {'User-Agent': USER_AGENT}
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status() # 200 OK가 아니면 예외 발생
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"에러: {url} 요청 실패 (시도 {attempt+1}/{max_retries}) - {e}")
            time.sleep(random.uniform(CRAWL_DELAY_MAX, CRAWL_DELAY_MAX * 2)) # 실패 시 더 긴 지연
    return None

# --- 기사 상세 정보 크롤링 함수 ---
def fetch_article_details(article_url):
    """
    주어진 기사 URL에서 본문, 발행일, 기자, 카테고리 등 상세 정보를 크롤링
    """
    soup = get_html_soup(article_url)
    if not soup:
        return {"content": None, "pubDate": None, "journalist": None, "category": None}

    content_text = None
    content_div = soup.find('div', class_='story-news article')
    if not content_div:
        content_div = soup.find('article', id='article-view-content-div')
    
    if content_div:
        content_text = ' '.join(content_div.get_text(separator=' ', strip=True).split())
    else:
        print(f"경고: {article_url} 에서 기사 본문을 찾을 수 없습니다. HTML 구조 변경 가능성.")

    pub_date_str = None
    match_date = re.search(r'AKR(\d{8})', article_url)
    if match_date:
        try:
            pub_date_str = datetime.strptime(match_date.group(1), '%Y%m%d').isoformat()
        except ValueError:
            pass

    journalist = None
    journalist_tag = soup.find('p', class_='byline')
    if journalist_tag:
        journalist = journalist_tag.get_text(strip=True)
        journalist = journalist.replace("기자 :", "").replace("기자", "").replace("취재 :", "").strip()
        if journalist.startswith("자료사진"):
            journalist = None

    category = None
    category_meta = soup.find('meta', property='article:section')
    if category_meta and 'content' in category_meta.attrs:
        category = category_meta['content']
    elif not category:
        category_span = soup.find('span', class_='location')
        if category_span:
            category_links = category_span.find_all('a')
            if len(category_links) > 1:
                category = category_links[1].get_text(strip=True)

    return {
        "content": content_text,
        "pubDate": pub_date_str,
        "journalist": journalist,
        "category": category
    }

# --- 메인 아카이브 크롤링 로직 ---
def start_archive_crawling():
    print(f"--- 연합뉴스 '지난뉴스' 아카링 시작 ---")
    
    # 1단계: 월별 아카이브 페이지 URL 목록 생성
    month_archive_urls = []
    
    # 바깥 루프 변수 이름을 변경하여 내부 변수와의 혼동 방지
    for year_outer in range(START_YEAR, END_YEAR + 1):
        for month_outer in range(1, 13):
            if year_outer == END_YEAR and month_outer > END_MONTH:
                continue
            if year_outer == START_YEAR and month_outer < START_MONTH:
                continue

            month_url = f"{YONHAP_BASE_URL}/sitemap/articles/{year_outer}-{month_outer:02d}"
            month_archive_urls.append(month_url)
    
    month_archive_urls.sort() 

    for month_url in month_archive_urls:
        print(f"\n--- 2단계: 월별 아카이브 페이지 크롤링: {month_url} ---")
        
        # 현재 month_url에서 연도와 월을 추출
        match = re.search(r'articles/(\d{4})-(\d{2})', month_url)
        if not match:
            print(f"경고: 월별 URL에서 연월 추출 실패: {month_url}. 이 월은 스킵합니다.")
            continue
        
        current_year = int(match.group(1))
        current_month = int(match.group(2))

        # DEBUG: 일별 URL 생성 직전 - 현재 year, month 변수가 아닌 추출된 값을 사용하도록 변경되었는지 확인
        print(f"DEBUG: 일별 URL 생성 직전 - 추출된 year: {current_year}, 추출된 month: {current_month}")
        
        month_soup = get_html_soup(month_url)
        if not month_soup:
            continue # 페이지를 가져오지 못하면 다음으로 넘어감

        # --- 3단계: 일별 아카이브 페이지 URL 직접 생성 및 탐색 ---
        
        # 'current_year'와 'current_month'를 사용하여 날짜 계산
        if current_month == 12:
            days_in_month = (datetime(current_year + 1, 1, 1) - datetime(current_year, current_month, 1)).days
        else:
            days_in_month = (datetime(current_year, current_month + 1, 1) - datetime(current_year, current_month, 1)).days
        
        # 'current_year'와 'current_month'를 사용하여 현재 날짜까지 크롤링 범위 설정
        current_day_in_month = datetime.now().day if current_year == END_YEAR and current_month == END_MONTH else days_in_month

        day_archive_urls = []
        for day in range(1, current_day_in_month + 1):
            for page_num in range(1, 3): # -1.htm, -2.htm 두 페이지씩 존재
                # 'current_year'와 'current_month'를 사용하여 URL 생성
                day_url = f"{YONHAP_BASE_URL}/sitemap/articles/{current_year}/{current_month:02d}/{day:02d}-{page_num}.htm"
                day_archive_urls.append(day_url)
        
        # 이 시점에서 day_archive_urls는 이미 정렬되어 있으므로 추가 sort 필요 없음

        for day_url in day_archive_urls:
            print(f"--- 3단계: 일별 아카이브 페이지 크롤링: {day_url} ---")
            day_soup = get_html_soup(day_url)
            if not day_soup:
                continue # 페이지를 가져오지 못하면 다음으로 넘어감

            # --- 중요: 일별 페이지(image_960f64.png)에서 원본 기사 링크 추출 셀렉터 수정 필요 ---
            article_links = day_soup.select('ul#sitemap-list a') # 셀렉터 
            
            if not article_links:
                print(f"    {day_url} 에서 기사 목록을 찾을 수 없습니다. (이 날짜에 기사가 없거나, 셀렉터 오류일 수 있음)")
                continue

            for article_link_tag in article_links:
                title = article_link_tag.get_text(strip=True)
                relative_article_url = article_link_tag.get('href')

                if not relative_article_url:
                    continue

                full_article_url = urljoin(YONHAP_BASE_URL, relative_article_url)

                if '/view/' not in full_article_url:
                    continue

                # if full_article_url in crawled_urls:
                #     continue
                if not is_allowed_url(full_article_url):
                    print(f"    스킵 (robots.txt 불허): {full_article_url}")
                    continue
                
                print(f"    - 크롤링 대상: {title} ({full_article_url})")
                
                article_details = fetch_article_details(full_article_url)

                if article_details["content"]:
                    article_data = {
                        "id": full_article_url.split('/')[-1].replace('.html', '').replace('.htm', ''),
                        "url": full_article_url,
                        "title": title,
                        "pubDate": article_details["pubDate"],
                        "media": "연합뉴스",
                        "content": article_details["content"],
                        "journalist": article_details["journalist"],
                        "category": article_details["category"],
                        "crawled_at": datetime.now().isoformat()
                    }
                    save_article_to_jsonl(article_data)
                    # crawled_urls.add(full_article_url)
                
                time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))

            time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))
        
        time.sleep(random.uniform(CRAWL_DELAY_MIN * 2, CRAWL_DELAY_MAX * 2))

    print(f"--- 모든 '지난뉴스' 아카이브 크롤링 완료 ---")

# --- 실행 ---
if __name__ == "__main__":
    print(f"연합뉴스 '지난뉴스' 아카이브 크롤링 시작. 데이터는 '{OUTPUT_JSON_FILE}'에 저장됩니다.")
    start_archive_crawling()
    print(f"연합뉴스 '지난뉴스' 아카이브 크롤링 최종 완료.")