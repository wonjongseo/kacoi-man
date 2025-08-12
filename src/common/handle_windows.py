import win32gui, win32con, win32api, win32process
import ctypes

user32 = ctypes.windll.user32

def _alt_jiggle():
    VK_MENU = 0x12  # ALT
    win32api.keybd_event(VK_MENU, 0, 0, 0)
    win32api.keybd_event(VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)

def _bring_to_front(hwnd):
    # 최소화 해제 & 표시
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    # TopMost로 잠깐 올렸다가 해제 (Z-order 밀어올리기)
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )

    # 다른 스레드 포커스 제한 완화
    cur_tid = win32api.GetCurrentThreadId()
    target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
    attached = False
    if target_tid and target_tid != cur_tid:
        user32.AttachThreadInput(cur_tid, target_tid, True)
        attached = True

    try:
        _alt_jiggle()
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur_tid, target_tid, False)

def activate_window(title_substr: str):
    """창 제목에 부분일치하는 첫 창을 앞으로 가져온다."""
    target = {"hwnd": None}

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        txt = win32gui.GetWindowText(hwnd)
        if title_substr.lower() in txt.lower():
            target["hwnd"] = hwnd

    win32gui.EnumWindows(enum_handler, None)
    if target["hwnd"]:
        _bring_to_front(target["hwnd"])
        print(f"창 활성화 완료: {win32gui.GetWindowText(target['hwnd'])}")
        return True
    else:
        print(f"창을 찾지 못함: '{title_substr}'")
        return False

