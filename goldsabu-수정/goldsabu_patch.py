#!/usr/bin/env python3
"""goldsabu.com 결제 전환 수정 — 문구 자동 치환 (판매가 29,800원 확정판, 2026-11-01)

사용법:  python3 goldsabu_patch.py <사이트 폴더>            # 미리보기(파일 안 바꿈)
         python3 goldsabu_patch.py <사이트 폴더> --apply    # 실제 적용 (.bak 백업 생성)

문구만 바꿉니다. 블록 삭제·이동(사전예약 모달, CTA 정리, 폼 배치 등)은
'수동 작업' 목록으로 위치만 알려 줍니다.
"""
import sys, pathlib, re

EXTS = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".py", ".jinja", ".j2", ".njk", ".ejs", ".hbs", ".json", ".md"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", "__pycache__", "venv", ".venv"}

# (지시서 번호, 찾을 문구, 바꿀 문구)  — 위에서부터 순서대로 적용
REPLACE = [
    ("A-P0-1", "19,900원 한 번, 30쪽 이상", "29,800원 한 번, 50쪽 이상"),
    ("A-P0-1", "아이결 리포트 19,900원", "아이결 리포트 29,800원"),
    ("A-P0-1", "19,900원", "29,800원"),
    ("A-P0-1", "한 달 학원비의 30분의 1로", "한 달 학원비의 20분의 1로"),
    ("A-P0-1", "107,800원 → 39,800원", "107,800원 → 29,800원"),
    ("A-P0-2", "결제·예약한 휴대폰 번호와 아이 생년월일을 넣어 주세요", "결제하신 휴대폰 번호와 아이 생년월일을 넣어 주세요"),
    ("A-P0-2", "내 리포트 · 예약 쿠폰 찾기", "내 리포트 찾기"),
    ("A-P0-2", "결제일(정식 오픈 전 미리 결제하신 경우 오픈일)로부터", "결제일로부터"),
    ("A-P0-4", "2학기 공부 그릇 점검 이벤트 진행 중 · 1월 10일까지", "겨울방학 공부 그릇 점검 · 12월 20일까지"),
    ("A-P0-4", "무료 공부 그릇 확인하고 이벤트가 받기 →", "1분 무료 공부 그릇 확인하기 →"),
    ("A-P0-4", "2학기 성적표 받기 전에, 우리 아이 공부 결부터 확인해요 1월 10일까지", "겨울방학 계획 세우기 전에, 우리 아이 공부 결부터 확인해요 12월 20일까지"),
    ("A-P0-4", "2학기 공부 그릇 점검 이벤트", "겨울방학 공부 그릇 점검"),
    ("A-P1-2", "후기 남기면 바로 할인 쿠폰 — 전체 14,900원 · 주제 하나 4,900원", "후기 남겨 주시면 다음 리포트 5,000원 할인 쿠폰을 드려요"),
    ("B-P0-2", "100% 환불 보장 · 주제 하나 9,800원 · 10분 완성", "100% 환불 보장 · 전체 29,800원 · 10분 완성"),
    ("B-P1-1", 'content="아이결 리포트"', 'content="황금돈사부"'),
    ("B-P1-1", "아이결 리포트는 명리학 해석을 바탕으로 한", "본 리포트는 명리학 해석을 바탕으로 한"),
]
# B-P1-1(브랜드 문구)은 아이결 페이지에선 맞는 문구라 /adult 파일(경로에 'adult')에만 적용.
# 한 파일에 두 페이지가 섞여 있으면 자동 적용하지 않고 수동 목록으로 넘김.
ADULT_ONLY = {"B-P1-1"}

# 바꾼 뒤에도 남아 있으면 안 되는 문구 → 남아 있으면 경고
FORBID = ["19,900", "39,800", "14,900", "4,900원", "사전 예약", "예약하고 쿠폰", "--:--:--", "이벤트가 받기",
          "1월 10일", "10월 11일", "오픈일", "sample_blur", "30분의 1", "15분의 1"]

# 사람이 직접 해야 하는 구조 작업 → 위치만 표시
MANUAL = [
    ("A-P0-2", "예약하고 쿠폰 받기", "사전예약 블록 전체 삭제"),
    ("A-P0-2", "예약 완료! 할인쿠폰", "예약 완료 모달 전체 삭제"),
    ("A-P0-3", "정상가로 돌아가요", "깨진 카운트다운 블록 삭제"),
    ("A-P0-3", "사교육비", "통계 카운트업(0조 원) → 정적 숫자 29조 2천억 원 / 60.4만 원"),
    ("A-P1-1", "친구에게 알려 주고", "무료 결과 CTA → 결제 완료 화면으로 이동"),
    ("A-P1-3", "7일 이내 100% 환불된다는 안내를 확인", "동의 체크박스에서 빼고 결제 버튼 위 배지로"),
    ("A-P1-4", "국외 이전", "동의문 단축 + [자세히 보기] 접기, FAQ에 AI 항목 추가"),
    ("A-P1-5", "먼저 맛보기", "맛보기 9,800원 문구 기본 노출에서 제거"),
    ("B-P0-1", "adBuy", "결제 블록이 무료 진단 없이도 열리는지 확인"),
    ("B-P0-3", "sample_blur/a-1", "a-1.jpg 블러 없는 원본으로 교체 + 본문 샘플 링크"),
    ("B-P1-3", "크게 일어설 운이", "사부 1인칭 문단 → '누가 푸나요' 섹션으로 이동"),
    ("B-P1-4", "잠긴 풀이 한 조각", "후기→잠금해제 혜택 폐기, 5,000원 할인으로"),
    ("분량", "30쪽 이상", "본품 표기면 '22장, 50쪽 이상'으로 (샘플 30쪽 표기는 유지 가능)"),
    ("분량", "25페이지", "'22장, 50쪽 이상'으로 통일"),
    ("분량", "20개 장", "'22장'으로 통일"),
    ("결제금액", "29800", "결제 모듈 실제 금액 확인 (화면과 결제액 일치)"),
    ("결제금액", "39800", "결제 모듈 금액 → 29800 으로 (PG·서버 상품가)"),
    ("결제금액", "19900", "결제 모듈 금액 → 29800 으로"),
    ("결제금액", "14900", "후기 쿠폰 금액 로직 → 5,000원 할인으로"),
]

def files(root):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS and not (SKIP_DIRS & set(p.parts)):
            yield p

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    root = pathlib.Path(sys.argv[1]); apply = "--apply" in sys.argv
    done, warn, manual = [], [], []
    for f in files(root):
        try: text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        orig, rel = text, str(f.relative_to(root))
        is_adult = "adult" in rel.lower()
        for code, old, new in REPLACE:
            n = text.count(old)
            if n and code in ADULT_ONLY and not is_adult:
                for m in re.finditer(re.escape(old), text):
                    manual.append((code, rel, text.count("\n", 0, m.start()) + 1, f"성인 페이지 부분이면 '{old}' → '{new}'"))
                continue
            if n:
                text = text.replace(old, new); done.append((code, rel, n, old, new))
        for w in FORBID:
            for m in re.finditer(re.escape(w), text):
                line = text.count("\n", 0, m.start()) + 1
                warn.append((rel, line, w))
        for code, key, what in MANUAL:
            for m in re.finditer(re.escape(key), text):
                line = text.count("\n", 0, m.start()) + 1
                manual.append((code, rel, line, what))
        if apply and text != orig:
            f.with_suffix(f.suffix + ".bak").write_text(orig, encoding="utf-8")
            f.write_text(text, encoding="utf-8")
    print(f"=== 자동 치환 {'적용' if apply else '미리보기'}: {len(done)}건")
    for c, r, n, o, nw in done: print(f"[{c}] {r} ×{n}\n    - {o}\n    + {nw}")
    print(f"\n=== 남아 있으면 안 되는 문구: {len(warn)}건")
    for r, l, w in warn: print(f"  {r}:{l}  '{w}'")
    print(f"\n=== 수동 작업 위치: {len(manual)}건")
    for c, r, l, w in manual: print(f"  [{c}] {r}:{l}  {w}")
    used = {c for c, *_ in done}
    missing = sorted({c for c, *_ in REPLACE} - used)
    if missing: print(f"\n=== 문구를 못 찾은 항목(이미 바뀌었거나 표현이 다름): {', '.join(missing)}")

if __name__ == "__main__":
    main()
