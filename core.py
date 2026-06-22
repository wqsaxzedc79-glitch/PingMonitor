"""
core.py — PingMonitor 핵심 모듈
SystemLogger / CsvLogger / FaultEngine / ConfigValidator / DailyReporter
"""

import csv
import os
import re
import traceback
from datetime import datetime, date, timedelta
from threading import Lock

# ── 경로 기준 (exe/py 실행 모두 지원) ────────────────────────────────
import sys
_BASE = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))

# ── CSV 헤더 정의 ────────────────────────────────────────────────────
H_PING   = ["DateTime", "TargetName", "Host",
            "Status", "ResponseTime_ms", "ErrorMsg"]
H_FAULT  = ["DateTime", "TargetName", "State",
            "FailStreak", "RecoverStreak", "Duration_sec"]
H_EVENT  = ["DateTime", "EventType", "Content", "Source"]
H_AGENT  = ["DateTime", "ProcessName", "Status", "PID", "Note"]
H_REPORT = ["Date", "TargetName", "Host",
            "TotalChecks", "OK", "Fail", "Faults",
            "TotalFaultTime_sec", "AvgRT_ms", "MaxRT_ms", "LastStatus"]


# ══════════════════════════════════════════════════════════════════════
# 1. 시스템 에러 로거 (system_error.log)
# ══════════════════════════════════════════════════════════════════════
class SystemLogger:
    """예외 발생 시 system_error.log에 기록."""

    def __init__(self, log_dir: str):
        self._path = os.path.join(log_dir, "system_error.log")
        self._lock = Lock()
        os.makedirs(log_dir, exist_ok=True)

    def log(self, func_name: str, exc: BaseException, extra: str = "") -> None:
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb  = traceback.format_exc()
        msg = (f"[{ts}] [{func_name}] {type(exc).__name__}: {exc}\n"
               f"{extra}\n{tb}\n{'─'*60}\n")
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(msg)
            except Exception:
                pass  # 로그 쓰기 실패 자체는 무시 (무한 루프 방지)

    def update_path(self, log_dir: str) -> None:
        self._path = os.path.join(log_dir, "system_error.log")
        os.makedirs(log_dir, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════
# 2. CSV 로거
# ══════════════════════════════════════════════════════════════════════
class CsvLogger:
    """CSV 파일 초기화 및 행 추가."""

    def __init__(self, log_dir: str, sys_log: SystemLogger):
        self._dir     = log_dir
        self._sys_log = sys_log
        self._lock    = Lock()
        self._init_files()

    def _init_files(self) -> None:
        os.makedirs(self._dir, exist_ok=True)
        specs = [
            ("ping_log.csv",   H_PING),
            ("fault_log.csv",  H_FAULT),
            ("event_log.csv",  H_EVENT),
            ("agent_log.csv",  H_AGENT),
        ]
        for fname, hdr in specs:
            path = os.path.join(self._dir, fname)
            if not os.path.exists(path):
                try:
                    with open(path, "w", newline="", encoding="utf-8-sig") as f:
                        csv.writer(f).writerow(hdr)
                except Exception as e:
                    self._sys_log.log("CsvLogger._init_files", e, fname)

    def update_dir(self, log_dir: str) -> None:
        self._dir = log_dir
        self._init_files()

    def write(self, filename: str, row: list) -> None:
        path = os.path.join(self._dir, filename)
        try:
            with self._lock:
                with open(path, "a", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerow(row)
        except Exception as e:
            self._sys_log.log("CsvLogger.write", e, filename)

    def write_ping(self, target_name: str, host: str,
                   ok: bool, rt, err: str = "") -> None:
        now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK" if ok else "FAIL"
        rt_val = rt if rt is not None else ""
        self.write("ping_log.csv",
                   [now, target_name, host, status, rt_val, err])

    def write_fault(self, target_name: str, state: str,
                    fail_streak: int, recover_streak: int,
                    duration_sec: int = 0) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.write("fault_log.csv",
                   [now, target_name, state,
                    fail_streak, recover_streak, duration_sec])

    def write_event(self, event_type: str, content: str, source: str = "") -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.write("event_log.csv", [now, event_type, content, source])

    def write_agent(self, process: str, status: str,
                    pid="", note: str = "") -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.write("agent_log.csv", [now, process, status, pid, note])


# ══════════════════════════════════════════════════════════════════════
# 3. 장애 판정 정책
# ══════════════════════════════════════════════════════════════════════
class FaultPolicy:
    """장애 판정 임계값. config.json fault_policy에서 읽어 적용."""

    def __init__(self, cfg: dict = None):
        p = (cfg or {}).get("fault_policy", {})
        self.suspect_count  = max(1, int(p.get("suspect_fail_count",  3)))
        self.fault_count    = max(1, int(p.get("fault_fail_count",    5)))
        self.recovery_count = max(1, int(p.get("recovery_success_count", 3)))

    def as_dict(self) -> dict:
        return {
            "suspect_fail_count":    self.suspect_count,
            "fault_fail_count":      self.fault_count,
            "recovery_success_count": self.recovery_count,
        }


# ══════════════════════════════════════════════════════════════════════
# 4. 장애 판정 엔진 (대상별 상태 머신)
# ══════════════════════════════════════════════════════════════════════
class FaultEngine:
    """
    대상 하나에 대한 장애 상태 머신.

    상태 전이:
        정상 ─[1회 실패]─► 응답 누락
        응답 누락 ─[복구]─► 정상           (일시적)
        응답 누락 ─[≥suspect]─► 장애 의심
        장애 의심 ─[복구]─► 정상
        장애 의심 ─[≥fault]──► 장애 발생
        장애 발생 ─[1회 성공]─► 복구 중
        복구 중   ─[≥recovery]─► 정상      (완전 복구)
        복구 중   ─[실패]──────► 장애 발생
    """

    S_NORMAL     = "정상"
    S_MISS       = "응답 누락"
    S_SUSPECT    = "장애 의심"
    S_FAULT      = "장애 발생"
    S_RECOVERING = "복구 중"

    STATE_COLORS = {
        S_NORMAL:     ("#006600", "#E2EFDA"),
        S_MISS:       ("#b87a00", "#FFEB9C"),
        S_SUSPECT:    ("#cc5500", "#FCE4D6"),
        S_FAULT:      ("#cc0000", "#FFC7CE"),
        S_RECOVERING: ("#005500", "#CCFFCC"),
    }

    def __init__(self, name: str, host: str, role: str,
                 policy: FaultPolicy, csv_log: CsvLogger):
        self.name    = name
        self.host    = host
        self.role    = role
        self.policy  = policy
        self._csv    = csv_log

        self.state          = self.S_NORMAL
        self.fail_streak    = 0
        self.success_streak = 0
        self.fault_start    = None   # datetime when FAULT began

        # Today's per-target stats
        self.today_pings    = 0
        self.today_ok       = 0
        self.today_faults   = 0
        self.today_fault_sec = 0
        self.today_rt_sum   = 0
        self.today_rt_count = 0
        self.today_rt_max   = 0

        self.last_rt        = None
        self.last_check     = None

    # ── 핑 결과 입력 ──────────────────────────────────────────────
    def update(self, ok: bool, rt, ts: datetime) -> list:
        """
        Ping 결과를 받아 상태를 갱신.
        반환: 발생한 이벤트 목록 (각 dict: type, state, ...)
        """
        self.today_pings += 1
        self.last_check   = ts
        self.last_rt      = rt

        if ok:
            self.today_ok += 1
            if rt is not None and rt > 0:
                self.today_rt_sum   += rt
                self.today_rt_count += 1
                self.today_rt_max    = max(self.today_rt_max, rt)

        events = []
        prev   = self.state

        if ok:
            self.fail_streak = 0
            if self.state in (self.S_FAULT, self.S_RECOVERING):
                self.success_streak += 1
                self.state = self.S_RECOVERING
                if self.success_streak >= self.policy.recovery_count:
                    # 완전 복구
                    dur  = self._close_fault(ts)
                    self.state = self.S_NORMAL
                    events.append({"type": "RECOVERED", "state": self.S_NORMAL,
                                   "fail_streak": self.fail_streak,
                                   "recover_streak": self.success_streak,
                                   "duration": dur})
                    self._csv.write_fault(self.name, "RECOVERED",
                                          0, self.success_streak, dur)
                    self.success_streak = 0
            elif self.state in (self.S_MISS, self.S_SUSPECT):
                self.success_streak += 1
                self.state = self.S_NORMAL
                events.append({"type": "TRANSIENT", "state": self.S_NORMAL,
                               "fail_streak": self.fail_streak})
                self._csv.write_fault(self.name, "TRANSIENT",
                                      self.fail_streak, self.success_streak)
                self.fail_streak = 0
            else:
                self.success_streak += 1
        else:
            self.success_streak = 0
            self.fail_streak   += 1

            if self.fail_streak >= self.policy.fault_count:
                if self.state != self.S_FAULT:
                    if self.fault_start is None:
                        self.fault_start = ts
                    self.state = self.S_FAULT
                    self.today_faults += 1
                    events.append({"type": "FAULT", "state": self.S_FAULT,
                                   "fail_streak": self.fail_streak})
                    self._csv.write_fault(self.name, "FAULT",
                                          self.fail_streak, 0)

            elif self.fail_streak >= self.policy.suspect_count:
                if self.state not in (self.S_SUSPECT, self.S_FAULT):
                    self.state = self.S_SUSPECT
                    events.append({"type": "SUSPECT", "state": self.S_SUSPECT,
                                   "fail_streak": self.fail_streak})
                    self._csv.write_fault(self.name, "SUSPECT",
                                          self.fail_streak, 0)
            else:
                if self.state == self.S_NORMAL:
                    self.state = self.S_MISS
                    events.append({"type": "MISS", "state": self.S_MISS,
                                   "fail_streak": self.fail_streak})

        return events

    def _close_fault(self, ts: datetime) -> int:
        if self.fault_start:
            dur = int((ts - self.fault_start).total_seconds())
            self.today_fault_sec += dur
        else:
            dur = 0
        self.fault_start = None
        return dur

    def reset_day(self) -> dict:
        """일일 통계 스냅샷 반환 후 초기화."""
        snap = {
            "name":            self.name,
            "host":            self.host,
            "total_pings":     self.today_pings,
            "ok":              self.today_ok,
            "fail":            self.today_pings - self.today_ok,
            "faults":          self.today_faults,
            "fault_sec":       self.today_fault_sec,
            "avg_rt":          (round(self.today_rt_sum / self.today_rt_count)
                                if self.today_rt_count > 0 else 0),
            "max_rt":          self.today_rt_max,
            "last_status":     self.state,
        }
        self.today_pings = self.today_ok = self.today_faults = 0
        self.today_fault_sec = self.today_rt_sum = 0
        self.today_rt_count  = self.today_rt_max = 0
        return snap

    # ── UI 표시용 ─────────────────────────────────────────────────
    @property
    def fg_color(self) -> str:
        return self.STATE_COLORS.get(self.state, ("#333333", "#FFFFFF"))[0]

    @property
    def bg_color(self) -> str:
        return self.STATE_COLORS.get(self.state, ("#333333", "#FFFFFF"))[1]

    @property
    def avg_rt(self) -> int:
        return (round(self.today_rt_sum / self.today_rt_count)
                if self.today_rt_count > 0 else 0)

    @property
    def fault_duration_str(self) -> str:
        if self.state in (self.S_FAULT, self.S_RECOVERING) and self.fault_start:
            sec = int((datetime.now() - self.fault_start).total_seconds())
            return (f"{sec//60}분 {sec%60}초" if sec >= 60 else f"{sec}초")
        return "—"


# ══════════════════════════════════════════════════════════════════════
# 5. 설정값 검증
# ══════════════════════════════════════════════════════════════════════
_RE_IP     = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
_RE_DOMAIN = re.compile(
    r"^(?:[a-zA-Z0-9\-]{1,63}\.)+[a-zA-Z]{2,}$")
_RE_HOST   = re.compile(
    r"^(?:(?:\d{1,3}\.){3}\d{1,3}|(?:[a-zA-Z0-9\-]{1,63}\.)+[a-zA-Z]{2,})$")


def validate_host(host: str) -> tuple:
    """(is_valid: bool, message: str)"""
    h = host.strip()
    if not h:
        return False, "호스트/IP가 비어 있습니다."
    if not _RE_HOST.match(h):
        return False, f"'{h}'은(는) 유효한 IP 또는 도메인 형식이 아닙니다."
    if _RE_IP.match(h):
        parts = h.split(".")
        if any(int(p) > 255 for p in parts):
            return False, f"'{h}'의 IP 범위가 올바르지 않습니다 (0~255)."
    return True, "OK"


def validate_config(cfg: dict) -> tuple:
    """(is_valid: bool, errors: list[str])"""
    errors = []

    targets = cfg.get("targets", [])
    if not targets:
        errors.append("대상 IP가 하나도 없습니다.")
    for t in targets:
        name = str(t.get("name", "")).strip()
        host = str(t.get("host", "")).strip()
        if not name:
            errors.append(f"대상명이 비어 있습니다 (host={host or '?'}).")
        ok, msg = validate_host(host)
        if not ok:
            errors.append(msg)

    interval = cfg.get("interval", 5)
    try:
        interval = int(interval)
    except (TypeError, ValueError):
        errors.append("검사 주기가 숫자가 아닙니다.")
        interval = 5
    if interval < 1:
        errors.append("검사 주기는 최소 1초 이상이어야 합니다.")

    return len(errors) == 0, errors


def validate_interval_warn(interval: int) -> str:
    """1~4초 입력 시 경고 문자열 반환, 5초 이상이면 빈 문자열."""
    if 1 <= interval <= 4:
        return (f"검사 주기 {interval}초는 권장값(5초 이상)보다 짧습니다.\n"
                f"로그가 빠르게 쌓이며 성능에 영향을 줄 수 있습니다.")
    return ""


# ══════════════════════════════════════════════════════════════════════
# 6. 일별 보고서
# ══════════════════════════════════════════════════════════════════════
class DailyReporter:
    """reports/YYYY-MM-DD_summary.csv 생성."""

    def __init__(self, report_dir: str, sys_log: SystemLogger):
        self._dir     = report_dir
        self._sys_log = sys_log

    def update_dir(self, report_dir: str) -> None:
        self._dir = report_dir

    def generate(self, engines: list, report_date: date = None) -> str:
        """엔진 목록의 오늘 통계로 CSV 보고서 생성. 경로 반환."""
        if report_date is None:
            report_date = date.today()

        try:
            os.makedirs(self._dir, exist_ok=True)
            path = os.path.join(self._dir,
                                f"{report_date.strftime('%Y-%m-%d')}_summary.csv")
            exists = os.path.exists(path)
            with open(path, "a", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                if not exists:
                    w.writerow(H_REPORT)
                for eng in engines:
                    snap = eng.reset_day()
                    w.writerow([
                        str(report_date),
                        snap["name"],
                        snap["host"],
                        snap["total_pings"],
                        snap["ok"],
                        snap["fail"],
                        snap["faults"],
                        snap["fault_sec"],
                        snap["avg_rt"],
                        snap["max_rt"],
                        snap["last_status"],
                    ])
            return path
        except Exception as e:
            self._sys_log.log("DailyReporter.generate", e)
            return ""
