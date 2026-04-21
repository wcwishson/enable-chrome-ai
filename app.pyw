from __future__ import annotations

import ctypes

from chrome_ai_enabler import (
    apply_enable_flow,
    build_console_summary,
    build_preflight_warning_message,
    collect_preflight_reports,
    is_chrome_running,
)


APP_TITLE = "Enable Chrome AI"

MB_OK = 0x00000000
MB_OKCANCEL = 0x00000001
MB_ICONINFORMATION = 0x00000040
MB_ICONWARNING = 0x00000030
MB_ICONERROR = 0x00000010
MB_SETFOREGROUND = 0x00010000

IDOK = 1
_DPI_AWARE_ENABLED = False


def enable_high_dpi() -> None:
    global _DPI_AWARE_ENABLED
    if _DPI_AWARE_ENABLED:
        return

    user32 = ctypes.windll.user32

    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        _DPI_AWARE_ENABLED = True
        return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _DPI_AWARE_ENABLED = True
        return
    except Exception:
        pass

    try:
        user32.SetProcessDPIAware()
        _DPI_AWARE_ENABLED = True
    except Exception:
        pass


def get_scaling_factor() -> float:
    try:
        user32 = ctypes.windll.user32
        dc = user32.GetDC(0)
        gdi32 = ctypes.windll.gdi32
        LOGPIXELSX = 88
        dpi = gdi32.GetDeviceCaps(dc, LOGPIXELSX)
        user32.ReleaseDC(0, dc)
        if dpi:
            return max(1.0, dpi / 96.0)
    except Exception:
        pass
    return 1.0


def message_box(message: str, flags: int) -> int:
    # Native Windows dialog; ensure DPI awareness before showing it.
    enable_high_dpi()
    return ctypes.windll.user32.MessageBoxW(0, message, APP_TITLE, flags)


def message_box_scaled(message: str, flags: int) -> int:
    scale = get_scaling_factor()
    if scale <= 1.0:
        return message_box(message, flags)

    # Add padding lines to reduce cramped appearance on high-DPI displays.
    padded_message = f"{message}\n\n"
    return message_box(padded_message, flags)


def main() -> None:
    try:
        preflight_warning = build_preflight_warning_message(collect_preflight_reports())
        if preflight_warning:
            proceed = message_box_scaled(preflight_warning, MB_OKCANCEL | MB_ICONWARNING | MB_SETFOREGROUND)
            if proceed != IDOK:
                return

        if is_chrome_running():
            prompt = (
                "Chrome is currently running and must restart to apply the AI feature changes.\n\n"
                "Click OK to close Chrome normally, switch Chrome to English if needed, apply the changes, "
                "and relaunch Chrome with the previous session restored."
            )
            result = message_box_scaled(prompt, MB_OKCANCEL | MB_ICONWARNING | MB_SETFOREGROUND)
            if result != IDOK:
                return

        # Run the patch flow. This may take a few seconds.
        result = apply_enable_flow()
        summary = build_console_summary(result)
        message_box_scaled(summary, MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND)
    except Exception as exc:
        message_box_scaled(str(exc), MB_OK | MB_ICONERROR | MB_SETFOREGROUND)


if __name__ == "__main__":
    main()
