"""index.html 정적 점검.

배역 6→5 축소처럼 HTML 요소를 지우면 JS가 참조하던 id 가 사라져
`document.getElementById(...)` 가 null 을 반환하고 런타임에서 터진다.
이 스크립트는 브라우저 없이 그 조합을 찾아낸다.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"

# 잔재 검사 대상 (TEST_PLAN E1)
# 배역·작품명뿐 아니라 베이스 고유 명칭·테마색·구 배우명까지 포함한다.
# 초기 감사에서 '아이드 도서카드'·구 테마색을 놓쳤던 경험 반영.
RESIDUE = re.compile(
    r"\b(magnus|abel|fredrick|hagen|jasper|claire)\b"
    r"|비더슈탄트|[Ww]iderstand|⚔|링크아트센터|클레어"
    r"|매그너스|프레드릭|하겐|재스퍼"
    r"|아이드 ?도서카드"
    r"|MYSTIC__CULTURE|미스틱"
    r"|#9B7B5A|#7A5E40|#C09870|#D0A880|#A88560|#A08878"
    r"|최석진|한상훈|황순종|박정원|강병훈|김도현|김방언|김준식"
    r"|조모세|김지웅|황건우|김태환|최기정|김도민|김보현|이형훈|고철순"
)

# 잔재 검사를 적용할 파일들
APP_FILES = ("index.html", "manifest.json", "guide.html", "sw.js")

# 동적으로 만들어지는 id 는 정적 검사에서 제외
DYNAMIC_PREFIXES = ("combo-", "board-", "stamp-", "rec-photo-")


def main() -> int:
    text = HTML.read_text(encoding="utf-8")
    errors = []

    # ── 1. 잔재 ──────────────────────────────────────────
    residue = [
        (i, line.strip())
        for i, line in enumerate(text.splitlines(), 1)
        if RESIDUE.search(line)
    ]
    if residue:
        errors.append(f"비더슈탄트 잔재 {len(residue)}줄")
        for i, line in residue[:10]:
            errors.append(f"    L{i}: {line[:90]}")

    # ── 2. getElementById 참조 대비 실제 id ───────────────
    defined = set(re.findall(r"""\bid=["']([^"']+)["']""", text))
    referenced = set(re.findall(r"""getElementById\(\s*['"]([^'"]+)['"]\s*\)""", text))

    missing = {
        r for r in referenced - defined
        if not r.startswith(DYNAMIC_PREFIXES)
    }
    if missing:
        errors.append(f"HTML 에 없는 id 를 JS 가 참조 {len(missing)}건")
        for m in sorted(missing):
            errors.append(f"    #{m}")

    # ── 3. 배역 키 정합성 ─────────────────────────────────
    roles_block = re.search(r"const ROLES = \[(.*?)\];", text, re.S)
    if not roles_block:
        errors.append("ROLES 배열을 찾지 못함")
        keys = []
    else:
        keys = re.findall(r"key:\s*'([^']+)'", roles_block.group(1))
        expected = ["marco", "soma", "yuo", "uiju", "eunhui"]
        if keys != expected:
            errors.append(f"ROLES 키 불일치: {keys} != {expected}")

    for key in keys:
        if f'id="rec-{key}"' not in text:
            errors.append(f"배역 '{key}' 의 입력 요소 #rec-{key} 없음")

    # SHORT 맵과 calFilter 가 ROLES 와 같은 키를 쓰는지
    for name, pattern in (("SHORT", r"const SHORT = \{(.*?)\};"),
                          ("calFilter", r"let calFilter = \{(.*?)\};")):
        m = re.search(pattern, text, re.S)
        if not m:
            errors.append(f"{name} 를 찾지 못함")
            continue
        found = re.findall(r"(\w+)\s*:", m.group(1))
        if sorted(found) != sorted(keys):
            errors.append(f"{name} 키 불일치: {found} != {keys}")

    # ── 4. 외부 참조 인벤토리 ─────────────────────────────
    # 블랙리스트만으로는 MYSTIC__CULTURE 같은 낯선 고유명사를 못 잡는다.
    # 외부로 나가는 링크·핸들을 전부 뽑아 눈으로 검토할 수 있게 한다.
    ALLOWED = {
        "x.com/_LIVECONNECTION",       # 이끼숲 제작사 라이브커넥션
        "_LIVECONNECTION",             # X 검색 URL (from%3A_LIVECONNECTION)
        "instagram.com/lc.musical_",   # 라이브커넥션 인스타그램
        "x.com/zen__ym",               # 앱 제작자 문의처
        "ticketlink.co.kr",
        "www.w3.org/2000/svg",         # SVG 네임스페이스
    }
    urls = set(re.findall(r"https?://([^\s\"'<>)]+)", text))
    unknown = sorted(
        u for u in urls
        if not any(a in u for a in ALLOWED)
    )

    # ── 결과 ─────────────────────────────────────────────
    print(f"정의된 id {len(defined)}개 / JS 참조 {len(referenced)}개")
    print(f"ROLES 키: {keys}")
    print(f"외부 링크 {len(urls)}개 (미확인 {len(unknown)}개)")
    for u in unknown:
        print(f"    ? {u[:100]}")

    if errors:
        print("\n[실패]")
        for e in errors:
            print("  " + e)
        return 1

    print("\n정적 점검 통과 — 오류 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
