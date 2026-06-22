"""
startup.py — Windows 시작 프로그램 등록 + 트레이 아이콘
"""

import os
import sys

# ── Windows 레지스트리 시작 등록 ──────────────────────────────────────
_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "PingMonitorV2"


def _get_exe_path() -> str:
    """현재 실행 파일 경로 반환."""
    if getattr(sys, "frozen", False):
        return sys.executable          # PyInstaller exe
    py  = sys.executable
    scr = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "ping_monitor_gui.py"))
    return f'"{py}" "{scr}"'


def is_startup_enabled() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY)
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_startup(enabled: bool) -> tuple:
    """(success: bool, message: str)"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY,
                             0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, _APP_NAME, 0,
                              winreg.REG_SZ, _get_exe_path())
            msg = "Windows 시작 시 자동 실행이 등록되었습니다."
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
                msg = "자동 실행 등록이 해제되었습니다."
            except FileNotFoundError:
                msg = "등록된 항목이 없습니다."
        winreg.CloseKey(key)
        return True, msg
    except Exception as e:
        return False, f"레지스트리 접근 실패: {e}"


# ── 트레이 아이콘 (pystray 선택적 사용) ──────────────────────────────
try:
    import pystray
    from pystray import MenuItem as Item, Menu
    try:
        from PIL import Image as PILImage, ImageDraw
        _PIL_OK = True
    except ImportError:
        _PIL_OK = False
    _PYSTRAY_OK = True
except ImportError:
    _PYSTRAY_OK = False
    _PIL_OK     = False


def _make_tray_icon_image(size=64):
    """pystray용 아이콘 이미지 생성."""
    if not _PIL_OK:
        return None
    import math
    img  = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill=(73, 144, 226))
    cx = cy = size // 2
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255))
    for r in (10, 17, 24):
        draw.arc([cx - r, cy - r, cx + r, cy + r],
                 start=210, end=330, fill=(255, 255, 255), width=3)
    return img


class TrayManager:
    """
    트레이 아이콘 관리.
    pystray + PIL이 없으면 트레이 기능은 비활성화됨.
    """

    def __init__(self, on_show, on_quit):
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon    = None
        self._running = False

    @property
    def available(self) -> bool:
        return _PYSTRAY_OK and _PIL_OK

    def start(self, title: str = "핑감지 테스트기") -> None:
        if not self.available or self._running:
            return
        img = _make_tray_icon_image()
        if img is None:
            return

        menu = Menu(
            Item("열기", self._show),
            Item("종료", self._quit),
        )
        self._icon = pystray.Icon(
            name=_APP_NAME,
            icon=img,
            title=title,
            menu=menu,
        )
        import threading
        threading.Thread(target=self._icon.run, daemon=True).start()
        self._running = True

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
        self._running = False

    def notify(self, title: str, message: str) -> None:
        if self._icon and self._running:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def _show(self, icon=None, item=None) -> None:
        self._on_show()

    def _quit(self, icon=None, item=None) -> None:
        self.stop()
        self._on_quit()
