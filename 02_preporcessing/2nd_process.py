import pymongo
import re

# --- MongoDB 연결 설정 ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "polaris"
SOURCE_COLLECTION_NAME = "yna_preprocessed_v1"  # 1차 전처리된 기사 컬렉션
DESTINATION_COLLECTION_NAME = "yna_preprocessed_v2"  # 본문 길이 기준 필터링된 컬렉션

# --- 길이 기준 설정 ---
MIN_CONTENT_BYTES = 500  # 바이트 기준 최소 길이 (조정 가능)

# --- 본문 길이 필터링 함수 ---
def is_content_long_enough(doc):
    content = doc.get("content", "")
    return len(content.encode("utf-8")) >= MIN_CONTENT_BYTES

# --- MongoDB 연결 및 필터링 실행 ---
client = None
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    source_collection = db[SOURCE_COLLECTION_NAME]
    destination_collection = db[DESTINATION_COLLECTION_NAME]

    print(f"MongoDB에 연결되었습니다. '{SOURCE_COLLECTION_NAME}' -> '{DESTINATION_COLLECTION_NAME}' 본문 길이 필터링을 시작합니다...")

    cursor = source_collection.find().sort('_id', 1)

    batch_size = 1000
    processed_docs_batch = []
    processed_count = 0
    skipped_count = 0

    for doc in cursor:
        if is_content_long_enough(doc):
            doc_copy = doc.copy()
            if '_id' in doc_copy:
                del doc_copy['_id']
            processed_docs_batch.append(doc_copy)
        else:
            skipped_count += 1

        if len(processed_docs_batch) >= batch_size:
            destination_collection.insert_many(processed_docs_batch)
            processed_count += len(processed_docs_batch)
            processed_docs_batch = []
            print(f"{processed_count}개 문서 삽입 완료...")

    if processed_docs_batch:
        destination_collection.insert_many(processed_docs_batch)
        processed_count += len(processed_docs_batch)

    print(f"\n--- 전체 {processed_count}개 문서 삽입 완료 (제외된 문서: {skipped_count}) ---")

except pymongo.errors.ConnectionFailure as e:
    print(f"MongoDB 연결 오류: {e}")
except Exception as e:
    print(f"전처리 중 오류 발생: {e}")
finally:
    if client:
        client.close()
        print("MongoDB 연결을 닫았습니다.")
