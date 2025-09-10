#!/usr/bin/env python3
import os, sys, json, argparse

def _is_nk(item) -> bool:
    """제목에 '북한' 또는 '北'이 포함되면 True"""
    md = item.get("metadata") if isinstance(item, dict) else None
    title = (md or {}).get("title", "")
    return isinstance(title, str) and ("북한" in title or "北" in title)

def _filter_from_obj(data):
    if isinstance(data, list):
        return [x for x in data if _is_nk(x)]
    elif isinstance(data, dict):
        return [data] if _is_nk(data) else []
    return []

def main():
    ap = argparse.ArgumentParser(description="폴더 내 JSON 파일 전체에서 제목에 '북한'/'北'이 있으면 추출 후 합쳐 저장")
    ap.add_argument("input_dir", help="입력 JSON 디렉터리")
    ap.add_argument("-o", "--output", required=True, help="최종 출력 JSON 파일 경로")
    args = ap.parse_args()

    results = []

    # 입력 폴더 내 모든 JSON 파일 순회
    for fname in os.listdir(args.input_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(args.input_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            filtered = _filter_from_obj(data)
            results.extend(filtered)
            print(f"✅ {fname}: 제목에 북한/北 포함 {len(filtered)}건 추출")
        except Exception as e:
            print(f"❌ {fname} 처리 중 오류: {e}", file=sys.stderr)

    # 결과를 하나의 JSON 파일로 저장
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📦 최종 결과 {len(results)}건 저장 완료 → {args.output}")

if __name__ == "__main__":
    main()
