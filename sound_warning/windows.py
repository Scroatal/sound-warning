from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


def enable_dpi_awareness() -> None:
    if os.name == "nt":
        ctypes.windll.user32.SetProcessDPIAware()


def monitors(root) -> list[tuple[int, int, int, int]]:
    if os.name != "nt":
        return [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def collect(_monitor, _dc, rect, _data):
        r = rect.contents
        result.append((r.left, r.top, r.right-r.left, r.bottom-r.top))
        return True

    ctypes.windll.user32.EnumDisplayMonitors(None, None, callback_type(collect), 0)
    return result or [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]


def position_meter(window, x: int, y: int, width: int, height: int) -> None:
    window.geometry(f"{width}x{height}+0+0")
    window.update_idletasks()
    if os.name != "nt":
        window.deiconify()
        return
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    hwnd = user32.GetAncestor(window.winfo_id(), 2)
    get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
    set_style = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_style.restype = ctypes.c_ssize_t
    # Layered + transparent makes the strip click-through; NOACTIVATE keeps keyboard focus.
    set_style(hwnd, -20, get_style(hwnd, -20) | 0x80000 | 0x20 | 0x08000000 | 0x80)
    window.deiconify()
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SetWindowPos(hwnd, wintypes.HWND(-1), x, y, width, height, 0x10 | 0x40)


def wait_for_process(pid: int, timeout_seconds: int = 45) -> None:
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        if kernel.GetLastError() == 87:  # Process already exited.
            return
        raise OSError("Cannot wait for Sound Warning to exit")
    try:
        if kernel.WaitForSingleObject(handle, timeout_seconds * 1000) != 0:
            raise TimeoutError("Sound Warning is still running; update was not installed")
    finally:
        kernel.CloseHandle(handle)
