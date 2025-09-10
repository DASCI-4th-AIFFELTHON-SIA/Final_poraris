# Polaris Project (북극성 프로젝트)

북극성 프로젝트는 OSINT(Open Source Intelligence) & GEOINT 기반 북한 분석을 목표로 합니다.    
연합뉴스를 비롯한 대규모 뉴스 데이터를 크롤링하고, 텍스트 마이닝 및 LLM 기반 요약·위치정보 추출을 통해 북한 관련 핵심 이슈와 지리적 맥락을 자동으로 정리합니다.    
    
이 프로젝트의 최종 목표는 북한 분석관에게 필요한 핵심 이슈와 위치 정보를 신속하고 정확하게 제공하여, 분석 효율성을 높이고 전략적 인사이트를 지원하는 것입니다.    

---

## 프로젝트 개요

| 항목 | 설명 |
|------|------|
| 프로젝트명 | **북극성 (Polaris)** |
| 목적 | 뉴스 기반 북한 관련 **핵심 이슈와 위치 정보 추출 자동화** |
| 핵심가치 | 대량의 노이즈 뉴스에서 분석관이 신속히 판단 가능한 **정제 정보 제공** |
| 적용 기술 | TF-IDF, LLM, 형태소 분석기, NER, GeoJSON, 시각화 등 |

---

## 🛠주요 기능 및 구성

| 단계 | 주요 작업 | 설명 |
|------|-----------|------|
| 1️⃣ 데이터 수집 | Web Crawling | 연합뉴스 기사 수집 (`crawl_4.py`) |
| 2️⃣ 전처리 | Preprocessing | 3단계 정제 (`1st_process.py` 등), 북한 필터링 |
| 3️⃣ 요약 생성 | LLM 요약 | LlamaIndex 기반 기사 요약 및 핵심 문장 추출 |
| 4️⃣ 이슈 추출 | TF-IDF 분석 | 월별 상위 키워드 추출 및 클러스터링 |
| 5️⃣ 위치 추출 | NER + Dictionary | 위치명 인식, GeoJSON 변환, 매핑 통합 |
| 6️⃣ 시각화 | Dash + JS | Top 키워드 및 위치 변화 시각화 (React 기반 대시보드 포함) |
| 7️⃣ 성능 평가 | 정확도 검증 | 키워드/위치 성능 정량·정성 평가 결과 기록 |

---

## 사용 기술 및 도구

| 분류 | 사용 기술 |
|------|------------|
| 형태소 분석기 | KoNLPy `Okt` |
| 요약/LLM | LlamaIndex, 경량 한국어 모델 |
| 키워드 추출 | `TF-IDF` (Scikit-Learn 기반) |
| 위치 정보 추출 | `KPF-BERT` NER + 커스텀 Dictionary 기반 매핑 |
| 지리 데이터 | `GeoJSON`, `MapLibre`, `Polygon/Point` 매핑 |
| 프론트 시각화 | React.js, D3.js, Plotly, Bubble Chart |
| 백엔드 | MongoDB on GCP, Python scripts |
| 평가 도구 | `json_vs_csv`, `정성적 평가표`, `성능 비교표` |

---

## 전체 로직 흐름도

```
flowchart TD
    A [뉴스 크롤링] --> B[전처리 및 필터링]
    B --> C[요약 및 LLM 처리]
    C --> D[핵심 이슈 추출 (TF-IDF)]
    D --> E[위치 정보 추출 (NER+사전)]
    E --> F[GeoJSON 매핑]
    F --> G[시각화 대시보드]
    G --> H[성능 검증 및 비교 분석]
```

---

## 프로젝트 폴더 구조

```📁 #FINAL_POLARIS
├── 📁 01_Web Crawling
│   └── 📁 Crawling_data
│       ├── crawl_4.py
│       ├── crawl_data_count.ipynb
│       └── crawling_README.ipynb
│
├── 📁 02_preprocessing
│   ├── 1st_process.py
│   ├── 2nd_process.py
│   ├── 3rd_process.py
│   └── preprocessing_README.ipynb
│
├── 📁 03_LlamaIndex_and_summarization
│   ├── 📁Llamaindex_data
│   ├── 📁Summary_data
│   ├── 1.one_line_summary.ipynb
│   ├── 2.Llamaindex.json.ipynb
│   ├── Llamaindex_README.ipynb
│   └── one_line_summary_README.ipynb
│
├── 📁 04_plus_preprocessing
│   ├── 📁preprocessing_filter_data
│   ├── 📁preprocessing_final_data
│   ├── 0.plus_preprocessing_README.ipynb
│   ├── preprocessing_filter_nk.py
│   └── preprocessing_final_nk.ipynb
│
├── 📁 05_Event_top10
│   ├── 📁monthly_results
│   ├── 📁monthly_results_cluster
│   ├── 📁re_monthly_results
│   ├── 📁re_monthly_results_cluster
│   ├── test
│   ├── 0.Event_README.ipynb
│   ├── 1.Event_keyword.ipynb
│   ├── hs_err_pid17174.log
│   ├── hs_err_pid46014.log
│   ├── idf_vectorizer_for_all_corpus.pkl
│   └── re_idf_vectorizer_for_all_corpus.pkl
│
├── 📁 06_Geo_coding
│   ├── 📁combined_data_by_year
│   ├── 📁combined_data_by_year_point_mapping
│   ├── 📁combined_data_by_year_polygon_mapping
│   ├── 📁Dictionary_data
│   ├── 📁extractor_data
│   ├── 📁Geo_Merge_data
│   ├── 📁Geosjon_data
│   ├── re_combined_data_by_year
│   ├── re_combined_data_by_year_mapping_v1.json
│   ├── re_combined_data_by_year_mapping_v2.json
│   ├── re_combined_data_by_year_mapping_v3.json
│   ├── re_combined_data_by_year_mapping_v4.json
│   ├── 0.geocoding_README.ipynb
│   ├── 1.geo_extractor.ipynb
│   ├── 2.geo_extractor_result_get_id_loc.ipynb
│   ├── 3.geo_output_merge.ipynb
│   ├── 4.geocoding_location_mapping.ipynb
│   ├── extracted_locations_result_ten_year_all.jsonl
│   ├── new_combined_data.json
│   ├── re_extracted_locations_result_ten_year_all.jsonl
│   ├── re_extracted_locations_result_ten_year_all.json
│   └── re_final_combined_data_ten_year.json
│
├── 📁 07_Visualization
│   ├── 📁 1.top_keyword
│   │   ├── bubble_chart.js
│   │   ├── monthly_top_keyword_change_volume_chart.ipynb
│   │   └── top_keyword_change_volume.ipynb
│   │
│   ├── 📁 2.geo_coding
│   │
│   └── 📁 3.site_visualization/src
│       ├── App.css
│       ├── App.js
│       ├── App.test.js
│       ├── ArticleListWindow.css
│       ├── ArticleListWindow.js
│       ├── background.png
│       ├── HomePage.css
│       ├── HomePage.js
│       ├── index.css
│       ├── index.js
│       ├── logo.svg
│       ├── MainApp.css
│       ├── MainApp.js
│       ├── maplibre-gl.css
│       ├── PlanetsTab.js
│       ├── PlanetsTab.css
│       ├── reportWebVitals.js
│       └── setupTests.js
│
├── 08 📁_performance_evaluation
    └── 📁geocoding_performance_data
    │   ├── final_preprocessing_dprk_loc_fac_sample12.csv
    │   ├── geocoding_eval_min_compare.csv
    │   ├── geocoding_performance.ipynb
    │   ├── json_vs_csv_per_id_exact.csv
    │   └── json_vs_csv_summary_exact.csv
    └── 📁 issue_performance_data
        ├── 📁benchmarks
        │   ├── 핵심이슈 다른모델 비교표.csv
        │   └── 핵심이슈 정성적 평가.csv
        ├── hs_err_pid3170.log
        ├── hs_err_pid41853.log
        ├── hs_err_pid51508.log
        ├── issue_performance.ipynb
        └── keyword_extraction_validation_results.csv
```
