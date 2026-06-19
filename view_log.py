"""
view_log.py
ping_log.csv / fail_log.csv 로그 뷰어 및 요약 통계
"""

import csv
import os

LOG_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "ping_log.csv")
FAIL_LOG = os.path.join(LOG_DIR, "fail_log.csv")


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def print_table(rows, title, limit=30):
    W = 70
    print()
    print("=" * W)
    print(f"  {title}")
    print("=" * W)

    if not rows:
        print("  (데이터 없음)")
        return

    display = rows[-limit:]
    print(f"  {'날짜/시간':<20} {'대상':<24} {'상태':<6} {'응답시간':>8}")
    print(f"  {'-'*20} {'-'*24} {'-'*6} {'-'*8}")

    for r in display:
        dt     = r.get("DateTime", "")
        target = r.get("Target", "")
        status = r.get("Status", "")
        rt     = r.get("ResponseTime_ms", "")
        rt_str = f"{rt} ms" if rt else "-"
        tag    = "OK  " if status == "OK" else "FAIL"
        print(f"  {dt:<20} {target:<24} {tag:<6} {rt_str:>8}")


def print_summary(rows, title):
    if not rows:
        return

    total  = len(rows)
    ok     = sum(1 for r in rows if r.get("Status") == "OK")
    fail   = total - ok
    rate   = ok / total * 100

    rts    = [int(r["ResponseTime_ms"]) for r in rows if r.get("ResponseTime_ms")]
    avg_rt = round(sum(rts) / len(rts)) if rts else 0
    max_rt = max(rts) if rts else 0
    min_rt = min(rts) if rts else 0

    print()
    print(f"  [{title} 요약]")
    print(f"  총 {total}건  |  OK: {ok}  |  FAIL: {fail}  |  성공률: {rate:.1f}%")
    if rts:
        print(f"  응답시간  평균: {avg_rt}ms  최소: {min_rt}ms  최대: {max_rt}ms")


def print_fail_by_target(fail_rows):
    if not fail_rows:
        return

    counts = {}
    for r in fail_rows:
        t = r.get("Target", "")
        counts[t] = counts.get(t, 0) + 1

    print()
    print("  [대상별 FAIL 횟수]")
    for target, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {target:<28}  {cnt}회")


def main():
    print()
    print("  PingMonitor Log Viewer")
    print(f"  경로: {LOG_DIR}")

    if not os.path.exists(LOG_DIR):
        print()
        print("  [오류] 로그 폴더가 없습니다. 먼저 ping_logger.py 를 실행하세요.")
        print(f"  경로: {LOG_DIR}")
        return

    ping_rows = read_csv(LOG_FILE)
    fail_rows = read_csv(FAIL_LOG)

    # 전체 이력 (최근 30건)
    print_table(ping_rows, f"전체 Ping 이력 — 최근 30건  (총 {len(ping_rows)}건)", limit=30)
    print_summary(ping_rows, "전체")

    # FAIL 이력 (최근 20건)
    print_table(fail_rows, f"FAIL 이력 — 최근 20건  (총 {len(fail_rows)}건)", limit=20)
    print_fail_by_target(fail_rows)

    print()
    print("=" * 70)
    print(f"  ping_log.csv : {LOG_FILE}")
    print(f"  fail_log.csv : {FAIL_LOG}")
    print("=" * 70)


if __name__ == "__main__":
    main()
    print()
    input("  종료하려면 Enter 를 누르세요...")
