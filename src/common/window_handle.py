from ctypes import wintypes
import ctypes
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.windll.user32
SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_uint
]

def set_topmost(win):
        hwnd = win._hWnd
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)