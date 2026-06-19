# PingMonitor — NC Agent 네트워크 분석 도구

NC Agent 네트워크 OFF 원인 분석을 위해 두 대상에 주기적으로 Ping을 수행하고 결과를 CSV로 기록합니다.

## 요구 사항

- Python 3.6 이상
- 외부 패키지 없음 (표준 라이브러리만 사용, requirements.txt 불필요)

## 실행 방법

```
python ping_logger.py
```

또는 전체 경로로 실행:

```
python D:\PingLog\PingMonitor\ping_logger.py
```

## Ping 대상

| 구분 | 주소 |
|------|------|
| 설비 IP | 192.168.0.101 |
| 서버 | hidc.cps.org |

## 로그 파일 위치

| 파일 | 내용 |
|------|------|
| `D:\CNC_Network_Monitor\ping_log.csv` | 전체 Ping 이력 (OK + FAIL) |
| `D:\CNC_Network_Monitor\fail_log.csv` | FAIL 발생 이력만 |

> 로그 폴더(`D:\CNC_Network_Monitor\`)와 CSV 파일은 최초 실행 시 자동으로 생성됩니다.

## CSV 컬럼

| 컬럼 | 설명 |
|------|------|
| DateTime | 날짜/시간 (yyyy-MM-dd HH:mm:ss) |
| Target | 대상 IP 또는 호스트명 |
| Status | `OK` 또는 `FAIL` |
| ResponseTime_ms | 응답시간(ms), FAIL이면 빈 값 |

## 콘솔 출력 예시

```
==========================================================
  PingMonitor  —  NC Agent 네트워크 분석
  전체 로그 : D:\CNC_Network_Monitor\ping_log.csv
  실패 로그 : D:\CNC_Network_Monitor\fail_log.csv
  Ping 간격 : 5초   |   종료 : Ctrl+C
==========================================================

[2026-06-19 10:30:00]
  [OK]    설비 IP  192.168.0.101              1 ms
  [FAIL]  서버     hidc.cps.org                  -

[2026-06-19 10:30:05]
  [OK]    설비 IP  192.168.0.101              2 ms
  [OK]    서버     hidc.cps.org              45 ms
```

## 종료 방법

실행 중 `Ctrl+C` 를 누르면 현재 루프 완료 후 안전하게 종료됩니다.
