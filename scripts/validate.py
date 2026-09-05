"""schedule.json / events.json 을 show-info.json 기준으로 검증한다."""

import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEEK = "월화수목금토일"

info = json.loads((ROOT / "show-info.json").read_text(encoding="utf-8"))
schedule = json.loads((ROOT / "schedule.json").read_text(encoding="utf-8"))
events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))

roles = {r["key"]: set(r["actors"]) for r in info["roles"]}
start = date.fromisoformat(info["startDate"])
end = date.fromisoformat(info["endDate"])

# 공식 공연시간: 화~금 20:00 / 토·공휴일 15:00,19:00 / 일 14:00,18:00
# 예외: 10/5(월) 15:00 — 월요일 공연은 이 회차뿐
# weekday(): 월=0 … 일=6
EXPECTED = {0: {"15:00"}, 1: {"20:00"}, 2: {"20:00"}, 3: {"20:00"},
            4: {"20:00"}, 5: {"15:00", "19:00"}, 6: {"14:00", "18:00"}}

# 공휴일은 토요일과 같은 시간표(15:00 / 19:00)를 따른다
HOLIDAYS = {
    "2026-10-03": "개천절",
    "2026-10-09": "한글날",
}

errors, warnings = [], []
seen = set()

for i, s in enumerate(schedule, 1):
    tag = f"[{i}] {s.get('date')} {s.get('time')}"

    try:
        d = date.fromisoformat(s["date"])
    except (KeyError, ValueError):
        errors.append(f"{tag} 날짜 형식 오류")
        continue

    if not (start <= d <= end):
        errors.append(f"{tag} 공연기간({start}~{end}) 밖")

    key = (s["date"], s["time"])
    if key in seen:
        errors.append(f"{tag} 중복 회차")
    seen.add(key)

    if s["date"] in HOLIDAYS:
        allowed = {"15:00", "19:00"}
        why = f"공휴일({HOLIDAYS[s['date']]})"
    else:
        allowed = EXPECTED.get(d.weekday(), set())
        why = f"{WEEK[d.weekday()]}요일"
    if s["time"] not in allowed:
        warnings.append(f"{tag} {why} 예상 시간 {sorted(allowed)} 와 불일치")

    for rk, cast in roles.items():
        actor = s.get(rk)
        if not actor:
            errors.append(f"{tag} 배역 '{rk}' 누락")
        elif actor not in cast:
            errors.append(f"{tag} '{rk}' = '{actor}' 는 캐스팅 목록에 없음")

    extra = set(s) - {"date", "time"} - set(roles)
    if extra:
        errors.append(f"{tag} 알 수 없는 필드: {sorted(extra)}")

for i, e in enumerate(events, 1):
    try:
        s0, e0 = date.fromisoformat(e["startDate"]), date.fromisoformat(e["endDate"])
    except (KeyError, ValueError):
        errors.append(f"[event {i}] 날짜 형식 오류")
        continue
    if s0 > e0:
        errors.append(f"[event {i}] {e['name']}: 시작일이 종료일보다 늦음")
    if not e.get("color", "").startswith("#"):
        errors.append(f"[event {i}] {e.get('name')}: color 형식 오류")

# ── 좌석 검증 ────────────────────────────────────────────────
seating = json.loads((ROOT / "seating.json").read_text(encoding="utf-8"))
seen_rows, grand = set(), 0

for floor in seating["floors"]:
    total = 0
    for r in floor["rows"]:
        row, first, last = r["row"], r["first"], r["last"]
        if row in seen_rows:
            errors.append(f"[좌석] 열 '{row}' 중복")
        seen_rows.add(row)

        if first > last:
            errors.append(f"[좌석] {row}열: first({first}) > last({last})")
            continue

        n = last - first + 1 + r.get("wheelchair", 0)
        total += n

        for u in r.get("unavailable", []):
            if not (first <= u <= last):
                errors.append(f"[좌석] {row}열 비판매석 {u} 이 범위 {first}~{last} 밖")
        if len(set(r.get("unavailable", []))) != len(r.get("unavailable", [])):
            errors.append(f"[좌석] {row}열 비판매석 중복")

    if total != floor["seatCount"]:
        errors.append(
            f"[좌석] {floor['name']} 합계 {total} != 선언값 {floor['seatCount']}")
    grand += total

if grand != seating["totalSeats"]:
    errors.append(f"[좌석] 전체 합계 {grand} != 선언값 {seating['totalSeats']}")

letters = [r["row"] for f in seating["floors"] for r in f["rows"]]
expected_letters = [chr(ord("A") + i) for i in range(len(letters))]
if letters != expected_letters:
    errors.append(f"[좌석] 열 문자가 연속이 아님: {letters}")

print(f"공연 회차 {len(schedule)}건 / 이벤트 {len(events)}건")
print(f"좌석 {grand}석 " + " · ".join(
    f"{f['name']} {f['seatCount']}({f['grade']})" for f in seating["floors"]))
blocked = sum(len(r.get("unavailable", [])) for f in seating["floors"] for r in f["rows"])
chairs = sum(r.get("wheelchair", 0) for f in seating["floors"] for r in f["rows"])
print(f"  비판매석 {blocked}석 · 휠체어석 {chairs}석 · 실판매 {grand - blocked - chairs}석")
print(f"공연일 {len({s['date'] for s in schedule})}일")

mondays = sorted({s["date"] for s in schedule
                  if date.fromisoformat(s["date"]).weekday() == 0})
print(f"월요일 공연: {mondays or '없음'}")

for rk, cast in roles.items():
    counts = {a: sum(1 for s in schedule if s.get(rk) == a) for a in sorted(cast)}
    label = next(r["label"] for r in info["roles"] if r["key"] == rk)
    print(f"  {label:4s} " + " · ".join(f"{a} {n}" for a, n in counts.items()))

if warnings:
    print("\n[경고]")
    for w in warnings:
        print("  " + w)

if errors:
    print("\n[오류]")
    for e in errors:
        print("  " + e)
    raise SystemExit(1)

print("\n검증 통과 — 오류 없음")
