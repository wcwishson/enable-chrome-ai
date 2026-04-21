from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import psutil


if sys.platform == "win32":
    from ctypes import wintypes

    USER32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    ENUM_WINDOWS_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


USER_DATA_PATHS = {
    "win32": {
        "stable": "~/AppData/Local/Google/Chrome/User Data",
        "canary": "~/AppData/Local/Google/Chrome SxS/User Data",
        "dev": "~/AppData/Local/Google/Chrome Dev/User Data",
        "beta": "~/AppData/Local/Google/Chrome Beta/User Data",
    },
    "linux": {
        "stable": "~/.config/google-chrome",
        "canary": "~/.config/google-chrome-canary",
        "dev": "~/.config/google-chrome-unstable",
        "beta": "~/.config/google-chrome-beta",
    },
    "darwin": {
        "stable": "~/Library/Application Support/Google/Chrome",
        "canary": "~/Library/Application Support/Google/Chrome Canary",
        "dev": "~/Library/Application Support/Google/Chrome Dev",
        "beta": "~/Library/Application Support/Google/Chrome Beta",
    },
}


@dataclass(slots=True)
class PatchResult:
    channel: str
    user_data_path: Path
    last_version: str | None
    success: bool
    changed: bool = False
    details: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ChromeRestartTarget:
    executable_path: Path
    arguments: tuple[str, ...] = ()

    def command(self) -> list[str]:
        return [str(self.executable_path), *self.arguments]


@dataclass(slots=True)
class EnableResult:
    chrome_was_running: bool
    reopened_paths: tuple[Path, ...]
    patch_results: list[PatchResult]

    @property
    def failures(self) -> list[PatchResult]:
        return [result for result in self.patch_results if not result.success]


@dataclass(slots=True)
class PreflightReport:
    channel: str
    user_data_path: Path
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.blockers or self.warnings)


@dataclass(frozen=True, slots=True)
class ChromeProfileInfo:
    channel: str
    user_data_path: Path
    directory: str
    name: str
    user_name: str
    gaia_name: str
    gaia_id: str

    @property
    def is_signed_in(self) -> bool:
        return bool(self.user_name or self.gaia_id)


RESTART_SWITCHES = ("--restore-last-session", "--restart")
FILTERED_RESTART_SWITCHES = ("--restore-last-session", "--restart", "--no-startup-window")
ENGLISH_UI_LOCALE = "en"
ENGLISH_LANGUAGE_CODE = "en"
DEFAULT_GLIC_COUNTRY = "us"
DEFAULT_GLIC_ROLLOUT_ELIGIBLE = True
DEFAULT_GEMINI_SETTINGS_ENABLED = 0
PROFILE_PREFERENCES_FILENAME = "Preferences"
IGNORED_PROFILE_DIRECTORIES = frozenset({"System Profile"})
DISABLED_BY_ADMIN_STATUS = 1
DISABLED_OTHER_STATUS = 2
SERVER_UNAVAILABLE_STATUS = 3


def get_version_and_user_data_path() -> dict[str, Path]:
    for platform_name, version_paths in USER_DATA_PATHS.items():
        if not sys.platform.startswith(platform_name):
            continue

        available_paths: dict[str, Path] = {}
        for version, user_data_path in version_paths.items():
            expanded_path = Path(user_data_path).expanduser().resolve()
            if expanded_path.exists():
                available_paths[version] = expanded_path
        return available_paths

    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def iter_chrome_processes() -> Iterable[psutil.Process]:
    for process in psutil.process_iter(["name", "exe"]):
        try:
            process_name = process.info.get("name") or process.name()
            if sys.platform == "darwin":
                if not process_name.startswith("Google Chrome"):
                    continue
            elif sys.platform == "win32":
                if process_name.lower() != "chrome.exe":
                    continue
            elif os.path.splitext(process_name)[0] != "chrome":
                continue

            if process.is_running():
                yield process
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def _get_process_cmdline(process: psutil.Process) -> list[str]:
    try:
        return process.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def _is_browser_process(process: psutil.Process) -> bool:
    command_line = _get_process_cmdline(process)
    if not command_line:
        return False

    return not any(argument.startswith("--type=") for argument in command_line[1:])


def get_running_chrome_executables() -> tuple[Path, ...]:
    executable_paths: set[Path] = set()
    for process in iter_chrome_processes():
        try:
            executable_path = process.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        if executable_path:
            executable_paths.add(Path(executable_path))

    return tuple(sorted(executable_paths))


def _extract_profile_directory(command_line: Sequence[str]) -> str | None:
    for index, argument in enumerate(command_line[1:], start=1):
        if argument.startswith("--profile-directory="):
            return argument.split("=", 1)[1]
        if argument == "--profile-directory" and index + 1 < len(command_line):
            return command_line[index + 1]
    return None


def _channel_from_executable(executable_path: Path) -> str:
    lower_path = str(executable_path).lower()
    if "chrome sxs" in lower_path:
        return "canary"
    if "chrome dev" in lower_path:
        return "dev"
    if "chrome beta" in lower_path:
        return "beta"
    return "stable"


def _get_last_active_profiles(user_data_path: Path) -> list[str]:
    local_state_file = user_data_path / "Local State"
    if not local_state_file.exists():
        return []

    try:
        data = json.loads(local_state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    profile = data.get("profile", {})
    profiles: list[str] = []

    last_active = profile.get("last_active_profiles")
    if isinstance(last_active, list):
        profiles.extend([str(item) for item in last_active if isinstance(item, str)])

    last_used = profile.get("last_used")
    if isinstance(last_used, str):
        profiles.append(last_used)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for name in profiles:
        if name and name not in seen:
            ordered.append(name)
            seen.add(name)
    return ordered


def build_restart_arguments(command_line: Sequence[str]) -> tuple[str, ...]:
    arguments: list[str] = []
    seen_arguments: set[str] = set()

    for index, argument in enumerate(command_line[1:], start=1):
        if not argument.startswith("-"):
            continue

        normalized_argument = argument.lower()
        if any(
            normalized_argument == filtered_switch
            or normalized_argument.startswith(f"{filtered_switch}=")
            for filtered_switch in FILTERED_RESTART_SWITCHES
        ):
            continue

        if normalized_argument in seen_arguments:
            continue

        arguments.append(argument)
        seen_arguments.add(normalized_argument)

        # Handle two-part flags like "--profile-directory Profile 1".
        if argument == "--profile-directory" and index + 1 < len(command_line):
            arguments.append(command_line[index + 1])

    for switch in RESTART_SWITCHES:
        if switch not in seen_arguments:
            arguments.append(switch)
            seen_arguments.add(switch)

    return tuple(arguments)


def collect_restart_targets(
    version_paths: dict[str, Path] | None = None,
    target_profiles_by_channel: dict[str, set[str]] | None = None,
) -> tuple[ChromeRestartTarget, ...]:
    restart_targets: dict[tuple[str, tuple[str, ...]], ChromeRestartTarget] = {}
    profile_targets: dict[tuple[str, str], ChromeRestartTarget] = {}

    for process in iter_chrome_processes():
        if not _is_browser_process(process):
            continue

        try:
            executable_path = process.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        if not executable_path:
            continue

        command_line = _get_process_cmdline(process)
        profile_directory = _extract_profile_directory(command_line)
        restart_target = ChromeRestartTarget(
            executable_path=Path(executable_path),
            arguments=build_restart_arguments(command_line),
        )

        restart_targets[(str(restart_target.executable_path).lower(), restart_target.arguments)] = restart_target

        if profile_directory:
            profile_target = ChromeRestartTarget(
                executable_path=Path(executable_path),
                arguments=(
                    f"--profile-directory={profile_directory}",
                    *RESTART_SWITCHES,
                ),
            )
            profile_targets[(str(profile_target.executable_path).lower(), profile_directory)] = profile_target

    if profile_targets:
        return tuple(
            sorted(
                profile_targets.values(),
                key=lambda target: (str(target.executable_path).lower(), target.arguments),
            )
        )

    if restart_targets:
        return tuple(
            sorted(
                restart_targets.values(),
                key=lambda target: (str(target.executable_path).lower(), target.arguments),
            )
        )

    fallback_targets = {
        str(executable_path).lower(): ChromeRestartTarget(executable_path=executable_path, arguments=RESTART_SWITCHES)
        for executable_path in get_running_chrome_executables()
    }

    if version_paths and fallback_targets and target_profiles_by_channel:
        for executable_path in get_running_chrome_executables():
            channel = _channel_from_executable(executable_path)
            if channel not in version_paths:
                continue

            for profile_directory in sorted(target_profiles_by_channel.get(channel, ())):
                profile_target = ChromeRestartTarget(
                    executable_path=executable_path,
                    arguments=(
                        f"--profile-directory={profile_directory}",
                        *RESTART_SWITCHES,
                    ),
                )
                profile_targets[(str(executable_path).lower(), profile_directory)] = profile_target

        if profile_targets:
            return tuple(
                sorted(
                    profile_targets.values(),
                    key=lambda target: (str(target.executable_path).lower(), target.arguments),
                )
            )

    if version_paths and fallback_targets:
        for executable_path in get_running_chrome_executables():
            channel = _channel_from_executable(executable_path)
            user_data_path = version_paths.get(channel)
            if not user_data_path:
                continue

            for profile_directory in _get_last_active_profiles(user_data_path):
                profile_target = ChromeRestartTarget(
                    executable_path=executable_path,
                    arguments=(
                        f"--profile-directory={profile_directory}",
                        *RESTART_SWITCHES,
                    ),
                )
                profile_targets[(str(executable_path).lower(), profile_directory)] = profile_target

        if profile_targets:
            return tuple(
                sorted(
                    profile_targets.values(),
                    key=lambda target: (str(target.executable_path).lower(), target.arguments),
                )
            )

    return tuple(sorted(fallback_targets.values(), key=lambda target: str(target.executable_path).lower()))


def is_chrome_running() -> bool:
    return any(True for _ in iter_chrome_processes())


def is_browser_chrome_running() -> bool:
    return any(_is_browser_process(process) for process in iter_chrome_processes())


def force_shutdown_chrome_processes(timeout_seconds: float = 8.0) -> bool:
    for process in iter_chrome_processes():
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            try:
                process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    deadline = time.monotonic() + max(timeout_seconds, 0.5)
    while time.monotonic() < deadline:
        if not is_chrome_running():
            return True
        time.sleep(0.2)

    for process in iter_chrome_processes():
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    hard_kill_deadline = time.monotonic() + 2.0
    while time.monotonic() < hard_kill_deadline:
        if not is_chrome_running():
            return True
        time.sleep(0.2)

    return False


def _get_window_handles_for_pids(process_ids: set[int]) -> list[int]:
    if sys.platform != "win32":
        return []

    handles: list[int] = []

    def callback(hwnd: int, _: int) -> bool:
        process_id = wintypes.DWORD()
        USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value in process_ids and USER32.IsWindowVisible(hwnd):
            handles.append(hwnd)
        return True

    USER32.EnumWindows(ENUM_WINDOWS_PROC(callback), 0)
    return handles


def close_chrome_gracefully(
    timeout_seconds: float = 30.0,
    version_paths: dict[str, Path] | None = None,
    target_profiles_by_channel: dict[str, set[str]] | None = None,
) -> tuple[ChromeRestartTarget, ...]:
    restart_targets = collect_restart_targets(version_paths, target_profiles_by_channel)
    if not restart_targets:
        return ()

    if sys.platform != "win32":
        raise RuntimeError("Graceful Chrome shutdown is only implemented for Windows in the GUI workflow.")

    process_ids = {process.pid for process in iter_chrome_processes()}
    window_handles = _get_window_handles_for_pids(process_ids)

    if not window_handles:
        if force_shutdown_chrome_processes(timeout_seconds=min(8.0, timeout_seconds)):
            return restart_targets

        raise RuntimeError("Chrome is running, but it could not be closed automatically.")

    for handle in window_handles:
        USER32.PostMessageW(handle, WM_CLOSE, 0, 0)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_browser_chrome_running():
            break
        time.sleep(0.5)

    if force_shutdown_chrome_processes(timeout_seconds=min(8.0, timeout_seconds)):
        return restart_targets

    raise RuntimeError("Chrome did not finish closing in time. Please close it manually, then run again.")


def restart_chrome(restart_targets: Iterable[ChromeRestartTarget]) -> None:
    for restart_target in restart_targets:
        subprocess.Popen(restart_target.command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_last_version(user_data_path: Path) -> str | None:
    last_version_file = user_data_path / "Last Version"
    if not last_version_file.exists():
        return None

    return last_version_file.read_text(encoding="utf-8").strip()


def set_all_is_glic_eligible(obj: object) -> bool:
    modified = False

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "is_glic_eligible" and value is not True:
                obj[key] = True
                modified = True
            elif isinstance(value, (dict, list)) and set_all_is_glic_eligible(value):
                modified = True
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)) and set_all_is_glic_eligible(item):
                modified = True

    return modified


def set_selected_profiles_is_glic_eligible(
    local_state: dict[str, object],
    target_profiles: set[str],
) -> tuple[bool, list[str]]:
    profile_section = local_state.get("profile")
    if not isinstance(profile_section, dict):
        return False, []

    info_cache = profile_section.get("info_cache")
    if not isinstance(info_cache, dict):
        return False, []

    modified = False
    updated_profiles: list[str] = []
    for profile_name in sorted(target_profiles):
        profile_info = info_cache.get(profile_name)
        if not isinstance(profile_info, dict):
            continue
        if profile_info.get("is_glic_eligible") is not True:
            profile_info["is_glic_eligible"] = True
            modified = True
            updated_profiles.append(profile_name)

    return modified, updated_profiles


def ensure_dict(parent: dict[str, object], key: str) -> dict[str, object]:
    value = parent.get(key)
    if isinstance(value, dict):
        return value

    created: dict[str, object] = {}
    parent[key] = created
    return created


def is_english_locale(value: str) -> bool:
    normalized = value.strip().replace("_", "-").lower()
    return normalized == ENGLISH_LANGUAGE_CODE or normalized.startswith(f"{ENGLISH_LANGUAGE_CODE}-")


def build_english_first_language_list(value: object) -> str:
    raw_languages: list[str] = []

    if isinstance(value, str):
        raw_languages = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        raw_languages = [str(item).strip() for item in value if str(item).strip()]

    ordered_languages = [ENGLISH_LANGUAGE_CODE]
    seen_languages = {ENGLISH_LANGUAGE_CODE}

    for language in raw_languages:
        if not language:
            continue

        normalized_language = language.replace("_", "-")
        if is_english_locale(normalized_language):
            continue

        lowered_language = normalized_language.lower()
        if lowered_language in seen_languages:
            continue

        ordered_languages.append(normalized_language)
        seen_languages.add(lowered_language)

    return ",".join(ordered_languages)


def iter_profile_preference_files(user_data_path: Path) -> tuple[Path, ...]:
    if not user_data_path.exists():
        return ()

    preference_files: list[Path] = []
    for child in sorted(user_data_path.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir() or child.name in IGNORED_PROFILE_DIRECTORIES:
            continue

        preference_file = child / PROFILE_PREFERENCES_FILENAME
        if preference_file.exists():
            preference_files.append(preference_file)

    return tuple(preference_files)


def collect_profile_infos(version_paths: dict[str, Path] | None = None) -> list[ChromeProfileInfo]:
    available_paths = version_paths or get_version_and_user_data_path()
    profiles: list[ChromeProfileInfo] = []

    for channel, user_data_path in available_paths.items():
        local_state_file = user_data_path / "Local State"
        if not local_state_file.exists():
            continue

        try:
            local_state = json.loads(local_state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if not isinstance(local_state, dict):
            continue

        profile_section = local_state.get("profile")
        info_cache = profile_section.get("info_cache") if isinstance(profile_section, dict) else None
        if not isinstance(info_cache, dict):
            continue

        for directory, profile_info in sorted(info_cache.items(), key=lambda item: str(item[0]).lower()):
            if not isinstance(profile_info, dict):
                continue

            profiles.append(
                ChromeProfileInfo(
                    channel=channel,
                    user_data_path=user_data_path,
                    directory=str(directory),
                    name=str(profile_info.get("name") or directory),
                    user_name=str(profile_info.get("user_name") or ""),
                    gaia_name=str(profile_info.get("gaia_name") or ""),
                    gaia_id=str(profile_info.get("gaia_id") or ""),
                )
            )

    return profiles


def format_profile_label(profile: ChromeProfileInfo) -> str:
    account = profile.user_name or profile.gaia_name or "not signed in"
    return f"{profile.name} - {account} ({profile.directory})"


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        ordered.append(value)
        seen.add(value)
    return ordered


def inspect_preflight(
    channel: str,
    user_data_path: Path,
    target_profiles: set[str] | None = None,
) -> PreflightReport:
    report = PreflightReport(channel=channel, user_data_path=user_data_path)
    local_state_file = user_data_path / "Local State"

    if not local_state_file.exists():
        report.blockers.append(f"[{channel}] Missing Local State file: {local_state_file}")
        return report

    try:
        local_state_raw = json.loads(local_state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.blockers.append(f"[{channel}] Local State is not valid JSON: {exc}")
        return report

    if not isinstance(local_state_raw, dict):
        report.blockers.append(f"[{channel}] Local State root is not a JSON object")
        return report

    local_state: dict[str, object] = local_state_raw

    profile_section = local_state.get("profile")
    info_cache = profile_section.get("info_cache") if isinstance(profile_section, dict) else None
    signed_in_profiles = []
    if isinstance(info_cache, dict):
        for profile_name, profile_info in info_cache.items():
            if target_profiles is not None and str(profile_name) not in target_profiles:
                continue
            if not isinstance(profile_info, dict):
                continue
            if profile_info.get("user_name") or profile_info.get("gaia_id"):
                signed_in_profiles.append(str(profile_name))

    if signed_in_profiles:
        report.notes.append(
            f"[{channel}] Signed-in Chrome profiles detected: {', '.join(sorted(signed_in_profiles))}"
        )
    else:
        report.blockers.append(
            f"[{channel}] No signed-in Chrome profile detected. "
            "Current Gemini-in-Chrome checks require account capability."
        )

    session_country = str(local_state.get("variations_safe_seed_session_consistency_country") or "").lower()
    if session_country and session_country != DEFAULT_GLIC_COUNTRY:
        report.warnings.append(
            f"[{channel}] Session country signal is '{session_country}', not '{DEFAULT_GLIC_COUNTRY}'. "
            "Chrome may gate Gemini by server-side geolocation."
        )

    permanent_country = str(local_state.get("variations_country") or "").lower()
    if permanent_country != DEFAULT_GLIC_COUNTRY:
        report.warnings.append(
            f"[{channel}] variations_country is '{permanent_country or '<missing>'}', expected '{DEFAULT_GLIC_COUNTRY}'."
        )

    intl_section = local_state.get("intl")
    app_locale = ""
    if isinstance(intl_section, dict):
        app_locale = str(intl_section.get("app_locale") or "")
    if app_locale and not is_english_locale(app_locale):
        report.warnings.append(f"[{channel}] app_locale is '{app_locale}', not English.")

    glic_section = local_state.get("glic")
    launcher_enabled = None
    if isinstance(glic_section, dict):
        launcher_enabled = glic_section.get("launcher_enabled")
    if launcher_enabled is not True:
        report.warnings.append(f"[{channel}] glic.launcher_enabled is not true.")

    preference_files = iter_profile_preference_files(user_data_path)
    if not preference_files:
        report.warnings.append(f"[{channel}] No profile Preferences files found in User Data.")

    for preference_file in preference_files:
        profile_name = preference_file.parent.name
        if target_profiles is not None and profile_name not in target_profiles:
            continue

        try:
            preferences_raw = json.loads(preference_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.warnings.append(f"[{channel}] {profile_name} Preferences invalid JSON: {exc}")
            continue

        if not isinstance(preferences_raw, dict):
            report.warnings.append(f"[{channel}] {profile_name} Preferences root is not a JSON object")
            continue

        preferences: dict[str, object] = preferences_raw
        browser_section = preferences.get("browser", {})
        sync_section = preferences.get("sync", {})
        glic_section = preferences.get("glic", {})

        gemini_settings = browser_section.get("gemini_settings") if isinstance(browser_section, dict) else None
        if gemini_settings not in (None, DEFAULT_GEMINI_SETTINGS_ENABLED):
            report.blockers.append(
                f"[{channel}] {profile_name}: browser.gemini_settings={gemini_settings!r} "
                "(policy-disabled state)."
            )

        rollout_eligibility = (
            sync_section.get("glic_rollout_eligibility") if isinstance(sync_section, dict) else None
        )
        if rollout_eligibility is False:
            report.warnings.append(f"[{channel}] {profile_name}: sync.glic_rollout_eligibility=false.")

        user_status = glic_section.get("user_status") if isinstance(glic_section, dict) else None
        status_code: int | None = None
        if isinstance(user_status, dict):
            status_candidate = user_status.get("user_status")
            if isinstance(status_candidate, int):
                status_code = status_candidate

        if status_code == DISABLED_BY_ADMIN_STATUS:
            report.blockers.append(f"[{channel}] {profile_name}: remote status says disabled by admin.")
        elif status_code == DISABLED_OTHER_STATUS:
            report.blockers.append(
                f"[{channel}] {profile_name}: remote status says disabled for this account/region."
            )
        elif status_code == SERVER_UNAVAILABLE_STATUS:
            report.warnings.append(f"[{channel}] {profile_name}: remote status check currently unavailable.")
        elif status_code is None:
            report.warnings.append(
                f"[{channel}] {profile_name}: no cached remote user status found yet."
            )

    report.blockers = _dedupe_preserving_order(report.blockers)
    report.warnings = _dedupe_preserving_order(report.warnings)
    report.notes = _dedupe_preserving_order(report.notes)
    return report


def collect_preflight_reports(
    version_paths: dict[str, Path] | None = None,
    target_profiles_by_channel: dict[str, set[str]] | None = None,
) -> list[PreflightReport]:
    available_paths = version_paths or get_version_and_user_data_path()
    if not available_paths:
        raise RuntimeError("No available Chrome user data paths were found.")

    return [
        inspect_preflight(
            channel,
            user_data_path,
            target_profiles_by_channel.get(channel) if target_profiles_by_channel else None,
        )
        for channel, user_data_path in available_paths.items()
    ]


def build_preflight_warning_message(reports: Iterable[PreflightReport]) -> str | None:
    collected_reports = list(reports)
    blockers = _dedupe_preserving_order(
        issue for report in collected_reports for issue in report.blockers
    )
    warnings = _dedupe_preserving_order(
        issue for report in collected_reports for issue in report.warnings
    )

    if not blockers and not warnings:
        return None

    lines = ["Potential Gemini-in-Chrome blockers detected before patching:"]

    if blockers:
        lines.append("")
        lines.append("Likely blockers:")
        for item in blockers:
            lines.append(f"- {item}")

    if warnings:
        lines.append("")
        lines.append("Possible blockers:")
        for item in warnings[:8]:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("Click OK to continue anyway, or Cancel to exit.")
    return "\n".join(lines)


def patch_profile_preferences(
    user_data_path: Path,
    target_profiles: set[str] | None = None,
) -> tuple[bool, list[str], list[str]]:
    modified = False
    updated_language_profiles: list[str] = []
    updated_rollout_profiles: list[str] = []
    updated_policy_profiles: list[str] = []
    updated_pin_profiles: list[str] = []
    errors: list[str] = []

    for preference_file in iter_profile_preference_files(user_data_path):
        if target_profiles is not None and preference_file.parent.name not in target_profiles:
            continue

        try:
            with preference_file.open("r", encoding="utf-8") as file_obj:
                preferences = json.load(file_obj)
        except json.JSONDecodeError as exc:
            errors.append(f"{preference_file.parent.name} Preferences is not valid JSON: {exc}")
            continue

        if not isinstance(preferences, dict):
            errors.append(f"{preference_file.parent.name} Preferences does not contain a JSON object")
            continue

        intl_preferences = ensure_dict(preferences, "intl")
        profile_modified = False
        language_updated = False
        rollout_updated = False
        policy_updated = False
        pin_updated = False

        updated_accept_languages = build_english_first_language_list(intl_preferences.get("accept_languages"))
        if intl_preferences.get("accept_languages") != updated_accept_languages:
            intl_preferences["accept_languages"] = updated_accept_languages
            profile_modified = True
            language_updated = True

        updated_selected_languages = build_english_first_language_list(intl_preferences.get("selected_languages"))
        if intl_preferences.get("selected_languages") != updated_selected_languages:
            intl_preferences["selected_languages"] = updated_selected_languages
            profile_modified = True
            language_updated = True

        sync_preferences = ensure_dict(preferences, "sync")
        if sync_preferences.get("glic_rollout_eligibility") != DEFAULT_GLIC_ROLLOUT_ELIGIBLE:
            sync_preferences["glic_rollout_eligibility"] = DEFAULT_GLIC_ROLLOUT_ELIGIBLE
            profile_modified = True
            rollout_updated = True

        browser_preferences = ensure_dict(preferences, "browser")
        if browser_preferences.get("gemini_settings") != DEFAULT_GEMINI_SETTINGS_ENABLED:
            browser_preferences["gemini_settings"] = DEFAULT_GEMINI_SETTINGS_ENABLED
            profile_modified = True
            policy_updated = True

        glic_preferences = ensure_dict(preferences, "glic")
        if glic_preferences.get("pinned_to_tabstrip") is not True:
            glic_preferences["pinned_to_tabstrip"] = True
            profile_modified = True
            pin_updated = True

        if not profile_modified:
            continue

        with preference_file.open("w", encoding="utf-8") as file_obj:
            json.dump(preferences, file_obj, ensure_ascii=False, separators=(",", ":"))

        modified = True
        profile_name = preference_file.parent.name
        if language_updated:
            updated_language_profiles.append(profile_name)
        if rollout_updated:
            updated_rollout_profiles.append(profile_name)
        if policy_updated:
            updated_policy_profiles.append(profile_name)
        if pin_updated:
            updated_pin_profiles.append(profile_name)

    details: list[str] = []
    if updated_language_profiles:
        details.append(f"Moved English to the front of profile languages: {', '.join(updated_language_profiles)}")
    if updated_rollout_profiles:
        details.append(f"Forced rollout eligibility on profiles: {', '.join(updated_rollout_profiles)}")
    if updated_policy_profiles:
        details.append(f"Forced Gemini settings policy to enabled: {', '.join(updated_policy_profiles)}")
    if updated_pin_profiles:
        details.append(f"Pinned Gemini button to tabstrip: {', '.join(updated_pin_profiles)}")

    return modified, details, errors


def patch_local_state(
    channel: str,
    user_data_path: Path,
    last_version: str | None,
    target_profiles: set[str] | None = None,
) -> PatchResult:
    local_state_file = user_data_path / "Local State"

    if last_version is None:
        return PatchResult(
            channel=channel,
            user_data_path=user_data_path,
            last_version=None,
            success=False,
            error=f"Missing Last Version file at {user_data_path / 'Last Version'}",
        )

    if not local_state_file.exists():
        return PatchResult(
            channel=channel,
            user_data_path=user_data_path,
            last_version=last_version,
            success=False,
            error=f"Missing Local State file at {local_state_file}",
        )

    try:
        with local_state_file.open("r", encoding="utf-8") as file_obj:
            local_state = json.load(file_obj)
    except json.JSONDecodeError as exc:
        return PatchResult(
            channel=channel,
            user_data_path=user_data_path,
            last_version=last_version,
            success=False,
            error=f"Local State is not valid JSON: {exc}",
        )

    modified = False
    details: list[str] = []
    errors: list[str] = []

    if target_profiles:
        glic_modified, updated_profiles = set_selected_profiles_is_glic_eligible(local_state, target_profiles)
        if glic_modified:
            modified = True
            details.append(f"Enabled is_glic_eligible for selected profiles: {', '.join(updated_profiles)}")
    elif set_all_is_glic_eligible(local_state):
        modified = True
        details.append("Enabled is_glic_eligible flags")

    if local_state.get("variations_country") != DEFAULT_GLIC_COUNTRY:
        local_state["variations_country"] = DEFAULT_GLIC_COUNTRY
        modified = True
        details.append("Set variations_country to us")

    expected_consistency = [last_version, DEFAULT_GLIC_COUNTRY]
    if local_state.get("variations_permanent_consistency_country") != expected_consistency:
        local_state["variations_permanent_consistency_country"] = expected_consistency
        modified = True
        details.append("Updated variations_permanent_consistency_country")

    if local_state.get("variations_safe_seed_permanent_consistency_country") != DEFAULT_GLIC_COUNTRY:
        local_state["variations_safe_seed_permanent_consistency_country"] = DEFAULT_GLIC_COUNTRY
        modified = True
        details.append("Set variations_safe_seed_permanent_consistency_country to us")

    if local_state.get("variations_safe_seed_session_consistency_country") != DEFAULT_GLIC_COUNTRY:
        local_state["variations_safe_seed_session_consistency_country"] = DEFAULT_GLIC_COUNTRY
        modified = True
        details.append("Set variations_safe_seed_session_consistency_country to us")

    intl_settings = ensure_dict(local_state, "intl")
    if intl_settings.get("app_locale") != ENGLISH_UI_LOCALE:
        intl_settings["app_locale"] = ENGLISH_UI_LOCALE
        modified = True
        details.append("Set Chrome UI locale to en")

    glic_settings = ensure_dict(local_state, "glic")
    if glic_settings.get("launcher_enabled") is not True:
        glic_settings["launcher_enabled"] = True
        modified = True
        details.append("Enabled glic.launcher_enabled")

    if modified:
        with local_state_file.open("w", encoding="utf-8") as file_obj:
            json.dump(local_state, file_obj, ensure_ascii=False, separators=(",", ":"))

    profile_language_modified, profile_details, profile_errors = patch_profile_preferences(user_data_path, target_profiles)
    if profile_language_modified:
        modified = True
    details.extend(profile_details)
    errors.extend(profile_errors)

    return PatchResult(
        channel=channel,
        user_data_path=user_data_path,
        last_version=last_version,
        success=not errors,
        changed=modified,
        details=details or ["No changes were needed"],
        error="; ".join(errors) if errors else None,
    )


def patch_all_profiles(
    version_paths: dict[str, Path] | None = None,
    target_profiles_by_channel: dict[str, set[str]] | None = None,
) -> list[PatchResult]:
    available_paths = version_paths or get_version_and_user_data_path()
    if not available_paths:
        raise RuntimeError("No available Chrome user data paths were found.")

    patch_results: list[PatchResult] = []
    for channel, user_data_path in available_paths.items():
        target_profiles = target_profiles_by_channel.get(channel) if target_profiles_by_channel else None
        patch_results.append(
            patch_local_state(channel, user_data_path, get_last_version(user_data_path), target_profiles)
        )

    return patch_results


def apply_enable_flow(
    timeout_seconds: float = 30.0,
    target_profiles_by_channel: dict[str, set[str]] | None = None,
) -> EnableResult:
    version_paths = get_version_and_user_data_path()
    if not version_paths:
        raise RuntimeError("No available Chrome user data paths were found.")

    restart_targets: tuple[ChromeRestartTarget, ...] = ()
    reopened_paths: tuple[Path, ...] = ()
    chrome_was_running = is_chrome_running()

    if chrome_was_running:
        restart_targets = close_chrome_gracefully(
            timeout_seconds=timeout_seconds,
            version_paths=version_paths,
            target_profiles_by_channel=target_profiles_by_channel,
        )
        reopened_paths = tuple(target.executable_path for target in restart_targets)

    try:
        patch_results = patch_all_profiles(version_paths, target_profiles_by_channel)
    finally:
        if restart_targets:
            restart_chrome(restart_targets)

    return EnableResult(
        chrome_was_running=chrome_was_running,
        reopened_paths=reopened_paths,
        patch_results=patch_results,
    )


def build_console_summary(result: EnableResult) -> str:
    lines = []

    if result.chrome_was_running:
        lines.append("Chrome was running and has been restarted with session restore.")
    else:
        lines.append("Chrome was not running; no restart was needed.")

    for patch_result in result.patch_results:
        status = "OK" if patch_result.success else "FAILED"
        lines.append(f"[{status}] {patch_result.channel}: {patch_result.user_data_path}")
        for detail in patch_result.details:
            lines.append(f"  - {detail}")
        if patch_result.error:
            lines.append(f"  - Error: {patch_result.error}")

    if result.failures:
        lines.append(f"Completed with {len(result.failures)} failure(s).")
    else:
        lines.append("Completed successfully.")

    return "\n".join(lines)
