"""
ping_logger.py
NC Agent 네트워크 OFF 원인 분석용 Ping 이력 저장 프로그램
"""

import csv
import os
import re
import signal
import subprocess
import time
from datetime import datetime

# ── 기본값 ────────────────────────────────────────────────────────────
DEFAULT_TARGETS = [
    ("설비 IP", "192.168.0.101"),
    ("서버",    "hidc.cps.org"),
]

LOG_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "ping_log.csv")
FAIL_LOG = os.path.join(LOG_DIR, "fail_log.csv")
INTERVAL = 5  # 초

CSV_HEADER = ["DateTime", "Target", "Status", "ResponseTime_ms"]
# ─────────────────────────────────────────────────────────────────────

_running = True


def _handle_sigint(sig, frame):
    global _running
    _running = False
    print("\n\n[종료 요청] Ctrl+C 감지 — 현재 루프 완료 후 종료합니다.")


signal.signal(signal.SIGINT, _handle_sigint)


# ── IP 설정 입력 화면 ─────────────────────────────────────────────────
def _setup_targets():
    """시작 시 대상 IP/호스트를 입력받는다. Enter 입력 시 기본값 사용."""
    SEP = "-" * 58

    print("=" * 58)
    print("  PingMonitor  IP 설정")
    print("  (Enter = 기본값 유지,  'q' 입력 시 즉시 시작)")
    print("=" * 58)

    targets = []

    for label, default in DEFAULT_TARGETS:
        prompt = f"  {label} [{default}] : "
        try:
            val = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            val = ""
        if val.lower() == "q":
            # 입력된 것까지만 사용하고 나머지는 기본값으로
            targets.append((label, default))
            for lbl2, def2 in DEFAULT_TARGETS[len(targets):]:
                targets.append((lbl2, def2))
            break
        targets.append((label, val if val else default))

    # 추가 IP 입력
    print()
    print(SEP)
    print("  추가 대상 IP 입력 (없으면 Enter 로 건너뜀)")
    print(SEP)

    idx = len(targets) + 1
    while True:
        try:
            host = input(f"  추가 IP #{idx} (Enter = 완료) : ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not host:
            break
        try:
            name = input(f"  '{host}' 이름 (Enter = IP 그대로) : ").strip()
        except (EOFError, KeyboardInterrupt):
            name = ""
        targets.append((name if name else host, host))
        idx += 1

    # 최종 확인 출력
    print()
    print("=" * 58)
    print("  모니터링 대상 목록")
    print("-" * 58)
    for i, (label, host) in enumerate(targets, 1):
        print(f"  {i}. {label:10}  {host}")
    print("-" * 58)
    try:
        input("  위 설정으로 시작합니다. Enter 를 누르세요...")
    except (EOFError, KeyboardInterrupt):
        pass

    return targets


# ── 로그 초기화 ───────────────────────────────────────────────────────
def _ensure_logs():
    os.makedirs(LOG_DIR, exist_ok=True)
    for path in (LOG_FILE, FAIL_LOG):
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(CSV_HEADER)


# ── Ping ──────────────────────────────────────────────────────────────
def _ping(host):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", host],
            capture_output=True,
            text=True,
            timeout=6,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            m = re.search(r"(?:time|시간)[=<](\d+)ms", result.stdout)
            return True, int(m.group(1)) if m else 0
        return False, None
    except Exception:
        return False, None


def _write_csv(path, row):
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow(row)


# ── 메인 루프 ─────────────────────────────────────────────────────────
def main():
    targets = _setup_targets()
    _ensure_logs()

    print()
    print("=" * 58)
    print("  PingMonitor  —  NC Agent 네트워크 분석 시작")
    print(f"  전체 로그 : {LOG_FILE}")
    print(f"  실패 로그 : {FAIL_LOG}")
    print(f"  Ping 간격 : {INTERVAL}초   |   종료 : Ctrl+C")
    print("=" * 58)

    while _running:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{now}]")

        for label, host in targets:
            if not _running:
                break

            ok, rt = _ping(host)
            status  = "OK" if ok else "FAIL"
            rt_disp = f"{rt} ms" if rt is not None else "-"
            row     = [now, host, status, rt if rt is not None else ""]

            _write_csv(LOG_FILE, row)
            if not ok:
                _write_csv(FAIL_LOG, row)

            tag = "[OK]  " if ok else "[FAIL]"
            print(f"  {tag}  {label:10}  {host:26}  {rt_disp:>8}")

        if _running:
            time.sleep(INTERVAL)

    print("\n[완료] 프로그램이 정상 종료되었습니다.")
    print(f"  전체 로그 : {LOG_FILE}")
    print(f"  실패 로그 : {FAIL_LOG}")


if __name__ == "__main__":
    main()
