import ctypes


CARBON_FRAMEWORK = "/System/Library/Frameworks/Carbon.framework/Carbon"
EVENT_CLASS_KEYBOARD = 0x6B657962
EVENT_HOT_KEY_PRESSED = 5
CMD_KEY = 1 << 8
SHIFT_KEY = 1 << 9
OPTION_KEY = 1 << 11
CONTROL_KEY = 1 << 12
HOTKEY_SIGNATURE = 0x46505354

MAC_KEYCODES = {
    "a": 0,
    "s": 1,
    "d": 2,
    "f": 3,
    "h": 4,
    "g": 5,
    "z": 6,
    "x": 7,
    "c": 8,
    "v": 9,
    "b": 11,
    "q": 12,
    "w": 13,
    "e": 14,
    "r": 15,
    "y": 16,
    "t": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "=": 24,
    "9": 25,
    "7": 26,
    "-": 27,
    "8": 28,
    "0": 29,
    "]": 30,
    "o": 31,
    "u": 32,
    "[": 33,
    "i": 34,
    "p": 35,
    "l": 37,
    "j": 38,
    "'": 39,
    "k": 40,
    ";": 41,
    "\\": 42,
    ",": 43,
    "/": 44,
    "n": 45,
    "m": 46,
    ".": 47,
    "space": 49,
    "`": 50,
}


class EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


def _load_carbon():
    carbon = ctypes.CDLL(CARBON_FRAMEWORK)
    carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
    carbon.GetApplicationEventTarget.argtypes = []
    carbon.RegisterEventHotKey.restype = ctypes.c_int32
    carbon.RegisterEventHotKey.argtypes = [
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(EventHotKeyID),
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    carbon.UnregisterEventHotKey.restype = ctypes.c_int32
    carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
    carbon.InstallEventHandler.restype = ctypes.c_int32
    carbon.InstallEventHandler.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(EventTypeSpec),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    carbon.RemoveEventHandler.restype = ctypes.c_int32
    carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]
    return carbon


def _parse_hotkey(hotkey_str):
    modifiers = 0
    key_token = ""

    for part in hotkey_str.lower().split("+"):
        if part == "<cmd>":
            modifiers |= CMD_KEY
        elif part == "<shift>":
            modifiers |= SHIFT_KEY
        elif part == "<alt>":
            modifiers |= OPTION_KEY
        elif part == "<ctrl>":
            modifiers |= CONTROL_KEY
        else:
            key_token = part.replace("<", "").replace(">", "").strip()

    return modifiers, key_token


def resolve_hotkey(hotkey_str, native_key_code=None):
    modifiers, key_token = _parse_hotkey(hotkey_str)

    if native_key_code is not None:
        try:
            return int(native_key_code), modifiers
        except (TypeError, ValueError):
            pass

    if key_token == "space":
        return MAC_KEYCODES["space"], modifiers

    if len(key_token) == 1:
        return MAC_KEYCODES.get(key_token), modifiers

    return None, modifiers


class CarbonHotkeyManager:
    def __init__(self, callback):
        self.callback = callback
        self._carbon = None
        self._hotkey_ref = ctypes.c_void_p()
        self._handler_ref = ctypes.c_void_p()
        self._handler_callback = None
        self._event_types = None

    def start(self):
        from configs.settings_manager import settings

        self.stop()

        hotkey_str = settings.get("hotkey", "<cmd>+'")
        native_key_code = settings.get("hotkey_mac_key_code")
        key_code, modifiers = resolve_hotkey(hotkey_str, native_key_code)

        if key_code is None:
            print(f"[FastPaste] Unable to resolve macOS hotkey: {hotkey_str}")
            return

        try:
            self._carbon = _load_carbon()
            self._event_types = EventTypeSpec(EVENT_CLASS_KEYBOARD, EVENT_HOT_KEY_PRESSED)

            def handler(in_call_ref, in_event, in_user_data):
                try:
                    self.callback()
                except Exception as e:
                    print(f"[FastPaste] macOS hotkey callback failed: {e}")
                return 0

            self._handler_callback = ctypes.CFUNCTYPE(
                ctypes.c_int32,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )(handler)

            status = self._carbon.InstallEventHandler(
                self._carbon.GetApplicationEventTarget(),
                self._handler_callback,
                1,
                ctypes.byref(self._event_types),
                None,
                ctypes.byref(self._handler_ref),
            )
            if status != 0:
                raise RuntimeError(f"InstallEventHandler failed with status {status}")

            hotkey_data = EventHotKeyID(HOTKEY_SIGNATURE, 1)
            status = self._carbon.RegisterEventHotKey(
                ctypes.c_uint32(key_code),
                ctypes.c_uint32(modifiers),
                ctypes.byref(hotkey_data),
                self._carbon.GetApplicationEventTarget(),
                0,
                ctypes.byref(self._hotkey_ref),
            )
            if status != 0:
                raise RuntimeError(f"RegisterEventHotKey failed with status {status}")

            print(f"[FastPaste] macOS hotkey registered natively: {hotkey_str}")
        except Exception as e:
            self.stop()
            print(f"[FastPaste] Native macOS hotkey registration failed: {e}")
            raise

    def stop(self):
        if self._carbon and self._hotkey_ref and self._hotkey_ref.value:
            try:
                self._carbon.UnregisterEventHotKey(self._hotkey_ref)
            except Exception:
                pass
        if self._carbon and self._handler_ref and self._handler_ref.value:
            try:
                self._carbon.RemoveEventHandler(self._handler_ref)
            except Exception:
                pass

        self._hotkey_ref = ctypes.c_void_p()
        self._handler_ref = ctypes.c_void_p()
        self._handler_callback = None
        self._event_types = None
        self._carbon = None

    def restart(self):
        self.stop()
        self.start()
