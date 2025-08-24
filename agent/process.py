import time
import win32gui
import win32process
import win32com.client
import win32con


def get_hwnd_from_pid(pid):
    def callback(hwnd, hwnds):
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid and win32gui.IsWindowVisible(hwnd):
            hwnds.append(hwnd)
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if hwnds else None

def wait_for_window(pid, timeout=10.0, check_interval=0.1):
    print(f"Waiting for window with PID {pid}")
    start = time.time()
    while time.time() - start < timeout:
        hwnd = get_hwnd_from_pid(pid)
        if hwnd:
            return hwnd
        time.sleep(check_interval)
    return None

def bring_window_to_foreground(hwnd):
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys('%')

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)