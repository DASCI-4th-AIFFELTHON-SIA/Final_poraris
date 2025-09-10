import pymongo
import re

# --- MongoDB 연결 설정 ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "polaris"
SOURCE_COLLECTION_NAME = "yna_preprocessed_v2" # 본문 길이 기준 필터링된 컬렉션
DESTINATION_COLLECTION_NAME = "yna_preprocessed_v3" # 제목 기준 필터링된 최종 컬렉션

# --- 필터링할 제목 키워드 리스트 ---
EXCLUDE_TITLE_KEYWORDS = [
    re.escape('[이시각헤드라인]'),
    re.escape('[뉴스초점]'),
    re.escape('[뉴스리뷰]'),
    re.escape('[라이브투데이]'),
    re.escape('[현장연결]'),
    re.escape('[씬속뉴스]'),
    re.escape('[1번지이슈]'),
    re.escape('[주요 신문 사설]'),
    re.escape('[연합시론]')
]

# 키워드들을 OR 조건으로 합쳐 하나의 정규표현식 패턴 생성
EXCLUDE_TITLE_PATTERN = '|'.join(EXCLUDE_TITLE_KEYWORDS)
exclude_title_regex = re.compile(EXCLUDE_TITLE_PATTERN)

# --- MongoDB 연결 및 필터링 실행 ---
client = None
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    source_collection = db[SOURCE_COLLECTION_NAME]
    destination_collection = db[DESTINATION_COLLECTION_NAME]
    
    # yna_preprocessed_v3 컬렉션이 이미 존재하면 삭제하고 시작 (선택 사항)
    # destination_collection.drop()

    print(f"MongoDB에 연결되었습니다. '{SOURCE_COLLECTION_NAME}' -> '{DESTINATION_COLLECTION_NAME}' 필터링 및 정렬을 시작합니다...")

    # 필터링 쿼리 생성
    query = {
        "title": { "$not": { "$regex": EXCLUDE_TITLE_PATTERN } }
    }
    
    # 쿼리를 사용하여 필터링하고, pubDate 필드를 기준으로 오름차순(1) 정렬하여 커서 생성
    # 오래된 기사가 먼저 오도록 정렬
    cursor = source_collection.find(query).sort("pubDate", 1)
    
    processed_docs = []
    
    total_docs_to_insert = source_collection.count_documents(query)
    print(f"필터링 기준에 맞는 총 {total_docs_to_insert}개의 문서를 시간 순서대로 정렬하여 저장합니다.")

    # 1000개 단위로 배치 처리
    batch_size = 1000
    inserted_count = 0

    for doc in cursor:
        doc_copy = doc.copy()
        if '_id' in doc_copy:
            del doc_copy['_id']
        processed_docs.append(doc_copy)

        if len(processed_docs) >= batch_size:
            destination_collection.insert_many(processed_docs)
            inserted_count += len(processed_docs)
            print(f"{inserted_count}개 문서 삽입 완료...")
            processed_docs = []

    # 남은 문서 삽입
    if processed_docs:
        destination_collection.insert_many(processed_docs)
        inserted_count += len(processed_docs)
    
    # 필터링으로 제외된 문서 수 계산
    skipped_count = source_collection.count_documents({}) - inserted_count
    
    print(f"\n--- 전체 {inserted_count}개 문서 삽입 완료 (제외된 문서: {skipped_count}) ---")

except pymongo.errors.ConnectionFailure as e:
    print(f"MongoDB 연결 오류: {e}")
except Exception as e:
    print(f"전처리 중 오류 발생: {e}")
finally:
    if client:
        client.close()
        print("MongoDB 연결을 닫았습니다.")