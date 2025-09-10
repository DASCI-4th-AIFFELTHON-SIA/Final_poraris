import pymongo
import datetime
import re

# --- MongoDB 연결 설정 ---
MONGO_URI = "mongodb://localhost:27017/" # MongoDB 서버 주소 (필요시 수정)
DB_NAME = "polaris"                      # 데이터베이스 이름
SOURCE_COLLECTION_NAME = "yna"           # 원본 컬렉션 이름
DESTINATION_COLLECTION_NAME = "yna_preprocessed_v1" # 전처리된 데이터를 저장할 새로운 컬렉션 이름 (이름을 바꿔주세요!)

# --- 검색 키워드 정의 ---
# 이 키워드들을 포함하는 문서만 전처리 대상으로 삼습니다.
keyword_string = """
북한, 김정은, 김여정, 조선중앙통신, 조선인민군, 오물풍선, 남북, 남측, 북측, 평양, 대북, 대남, 군사합의, 비무장지대, 이산가족, 장마당, 
통일부, 장거리 미사일, ICBM, SLBM, NLL, 휴전선
김주애, 리설주, 최룡해, 장성택, 김정남, 최선희, 김일성, 현송월, 김영철, 
광명성절, 김정일, 6.25, 방사포, 판문점, JSA, 러시아, 특수부대, 남파공작원, 정찰총국, 
군사, 탈북, 조선, 인민, 주석궁, 동창리, 나진항, 선봉, 北, 당대회, 금수산태양궁전, 
김일성종합대학, 김책공업대학, 주체사상, 금강산, 개성공단, 
북핵, 북중, 북러, 로동신문, DPRK, 조선로동당 중앙위원회
"""

# --- 키워드 파싱 ---
keywords = [
    word.strip()
    for word in re.split(r'[, \n]+', keyword_string) 
    if word.strip()
]

# --- 1차 전처리 함수 (여기를 수정하여 원하는 전처리 로직을 구현하세요!) ---
def preprocess_document(doc):
    """
    원본 문서를 받아서 1차 전처리를 수행하고, 전처리된 새 문서 객체를 반환합니다.
    이 함수는 이미 필터링된 문서에 대해서만 호출됩니다.
    """
    processed_doc = doc.copy() 

    # --- 중요: _id 필드 처리 (새 컬렉션에 새 _id를 부여받기 위해 원본 _id 제거) ---
    if '_id' in processed_doc:
        del processed_doc['_id'] 

    return processed_doc

# --- MongoDB 연결 및 전처리 실행 ---
client = None
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    source_collection = db[SOURCE_COLLECTION_NAME]
    destination_collection = db[DESTINATION_COLLECTION_NAME]

    print(f"MongoDB에 연결되었습니다. '{SOURCE_COLLECTION_NAME}' -> '{DESTINATION_COLLECTION_NAME}' 전처리를 시작합니다...")

    # --- 필터링 조건 동적 생성 ---
    filter_conditions = []
    filter_conditions.append({"category": "북한"}) # 카테고리가 '북한'인 문서

    for kw in keywords:
        filter_conditions.append({"title": {"$regex": re.compile(kw, re.IGNORECASE)}}) # 제목에 키워드 포함
        filter_conditions.append({"content": {"$regex": re.compile(kw, re.IGNORECASE)}}) # 내용에 키워드 포함

    # 최종 쿼리 필터 (OR 조건)
    filter_query = {"$or": filter_conditions}

    batch_size = 1000 
    processed_docs_batch = []
    processed_count = 0

    # --- 필터링 조건을 적용하여 문서 조회 ---
    cursor = source_collection.find(filter_query).sort('_id', 1) 

    for doc in cursor:
        processed_doc = preprocess_document(doc)
        processed_docs_batch.append(processed_doc)

        if len(processed_docs_batch) >= batch_size:
            destination_collection.insert_many(processed_docs_batch)
            processed_count += len(processed_docs_batch)
            processed_docs_batch = []
            print(f"{processed_count}개 문서 전처리 및 삽입 완료...")

    if processed_docs_batch:
        destination_collection.insert_many(processed_docs_batch)
        processed_count += len(processed_docs_batch)

    print(f"\n--- 전체 {processed_count}개 문서 전처리 및 '{DESTINATION_COLLECTION_NAME}'에 삽입 완료 ---")

except pymongo.errors.ConnectionFailure as e:
    print(f"MongoDB 연결 오류: {e}")
except Exception as e:
    print(f"전처리 및 삽입 중 오류 발생: {e}")
finally:
    if client:
        client.close()
        print("MongoDB 연결을 닫았습니다.")