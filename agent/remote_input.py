import ctypes
from ctypes import wintypes

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

if not hasattr(wintypes, 'ULONG_PTR'):
    wintypes.ULONG_PTR = ctypes.POINTER(ctypes.c_ulong) if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_ulonglong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]

class _INPUTunion(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTunion)]

SendInput = ctypes.windll.user32.SendInput

prev_keys = bytearray(32)
# prev_buttons = 0

def handle_packet(pkt: bytes):
    global prev_keys#, prev_buttons

    if len(pkt) != 32: # 39:
        return

    # Keyboard state
    new_keys = pkt[0:32]
    diff = int.from_bytes(prev_keys, 'little') ^ int.from_bytes(new_keys, 'little')
    while diff:
        vk = (diff & -diff).bit_length() - 1
        byte_i = vk >> 3
        bit = 1 << (vk & 7)
        is_down = new_keys[byte_i] & bit
        print(f"Now changing key {vk}")
        key_event(vk, down=bool(is_down))
        diff &= diff - 1
    prev_keys[:] = new_keys

    # Mouse buttons
    #buttons = pkt[32]
    #changed = buttons ^ prev_buttons
    #if changed & 1: (mouse_left_down if buttons & 1 else mouse_left_up)()
    #if changed & 2: (mouse_right_down if buttons & 2 else mouse_right_up)()
    #if changed & 4: (mouse_middle_down if buttons & 4 else mouse_middle_up)()
    #prev_buttons = buttons

    # Mouse move (relative)
    #dx, dy = struct.unpack_from('<hh', pkt, 33)
    #if dx or dy:
    #    mouse_move(dx, dy)

    # Mouse wheel
    #wheel, = struct.unpack_from('<h', pkt, 37)
    #if wheel:
    #    mouse_wheel(wheel)

def key_event(vk, down=True):
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP

    # Add extended flag for certain keys
    if vk in (0x1D, 0x38, 0x9D, 0xB8,  # Ctrl, Alt (L/R)
              0x25, 0x26, 0x27, 0x28,  # Arrow keys
              0x2D, 0x2E, 0x23, 0x24,  # Ins, Del, End, Home
              0x21, 0x22, 0x6A, 0x6B,  # PgUp, PgDn, NumPad ops
              0x6D, 0x6F):             # NumPad -, /
        flags |= KEYEVENTF_EXTENDEDKEY

    ki = KEYBDINPUT(wVk=0, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    inp = INPUT(type=INPUT_KEYBOARD, union=_INPUTunion(ki=ki))
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def mouse_event(flags, data=0):
    mi = MOUSEINPUT(0, 0, data, flags, 0, 0)
    inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def mouse_move(dx, dy, absolute=False):
    flags = MOUSEEVENTF_MOVE
    if absolute:
        flags |= MOUSEEVENTF_ABSOLUTE
    mi = MOUSEINPUT(dx, dy, 0, flags, 0, 0)
    inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def mouse_wheel(delta):
    mouse_event(MOUSEEVENTF_WHEEL, delta)

def mouse_left_down():  mouse_event(MOUSEEVENTF_LEFTDOWN)
def mouse_left_up():    mouse_event(MOUSEEVENTF_LEFTUP)
def mouse_right_down(): mouse_event(MOUSEEVENTF_RIGHTDOWN)
def mouse_right_up():   mouse_event(MOUSEEVENTF_RIGHTUP)
def mouse_middle_down(): mouse_event(MOUSEEVENTF_MIDDLEDOWN)
def mouse_middle_up():   mouse_event(MOUSEEVENTF_MIDDLEUP)
