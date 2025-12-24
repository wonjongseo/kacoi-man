# src/common/pyauto_guard.py
import threading, time
import pyautogui
from contextlib import contextmanager

_LOCK = threading.RLock()

def _is_corner():
    x, y = pyautogui.position()
    w, h = pyautogui.size()
    return (x, y) in {(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)}

def nudge_if_corner():
    """FAILSAFE가 켜져있고 커서가 모서리에 있으면 잠시 끄고 중앙으로 이동"""
    if not getattr(pyautogui, "FAILSAFE", True):
        return
    with _LOCK:
        if _is_corner():
            prev = pyautogui.FAILSAFE
            try:
                pyautogui.FAILSAFE = False
                w, h = pyautogui.size()
                pyautogui.moveTo(w // 2, h // 2, duration=0)  # 안전 지점
                time.sleep(0.03)  # OS 반영 대기
            finally:
                pyautogui.FAILSAFE = prev

@contextmanager
def disable_failsafe_temporarily():
    """잠깐 FAILSAFE 끄기 (스레드 안전)"""
    with _LOCK:
        prev = pyautogui.FAILSAFE
        pyautogui.FAILSAFE = False
        try:
            yield
        finally:
            pyautogui.FAILSAFE = prev

def patch_pyautogui():
    """
    pyautogui 주요 함수들을 가드로 래핑.
    어디서 호출해도 호출 직전에 모서리면 중앙으로 옮겨 FailSafe 재발 방지.
    """
    with _LOCK:
        def _wrap(name):
            if not hasattr(pyautogui, name):
                return
            orig = getattr(pyautogui, name)
            def wrapped(*a, **kw):
                nudge_if_corner()
                return orig(*a, **kw)
            setattr(pyautogui, name, wrapped)

        for fn in [
            "keyDown", "keyUp", "press", "write",
            "moveTo", "move", "dragTo", "drag",
            "click", "doubleClick", "mouseDown", "mouseUp",
            "scroll"
        ]:
            _wrap(fn)
