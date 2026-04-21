# Enable Chrome AI

One-click helpers for restoring Chrome's built-in Gemini / AI features.

This fork includes:

- A Windows app: `EnableChromeAI.exe`
- A macOS app bundle: `Enable Chrome AI.app`
- The original Python script workflow for advanced users

The goal is simple: download the app for your system, run it, let it restart Chrome, and check whether Chrome AI is back.

English | [中文](README.zh.md)

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

## Download

Open the [Releases](../../releases) page and download the package for your system.

For Windows:

- Download `EnableChromeAI-Release.zip`.
- Unzip it.
- Double-click `EnableChromeAI.exe`.

For macOS:

- Download the latest `.zip` containing `Enable Chrome AI.app`.
- Unzip it.
- Move `Enable Chrome AI.app` to `/Applications` if you like.
- Open the app. If macOS blocks it the first time, right-click the app and choose `Open`.

## How to Use

1. Save anything important in Chrome.
2. Open the app for your system.
3. If Chrome is already open, allow the app to restart it.
4. Wait for the app to finish.
5. Chrome should reopen automatically.
6. Check whether Gemini / Chrome AI is available again.

You do not need Python, PowerShell, Terminal, or developer tools when using the packaged app.

## What the App Does

- Finds your Google Chrome profile.
- Closes Chrome so the settings can be updated safely.
- Applies the local Chrome AI availability fix.
- Reopens Chrome and tries to restore your previous windows and tabs.
- Warns you if Chrome still appears to be blocked by account or region checks.

## Important Notes

- Google Chrome must already be installed.
- The app does not create or modify your Google account.
- The app cannot guarantee Gemini appears for every Chrome version, Google account, or network location.
- If Chrome updates and Gemini disappears again, run the app again.
- If Gemini still does not appear, make sure Chrome is signed in and your network is using a supported region.

## Privacy

The app changes local Chrome settings on your computer. It does not collect your data, upload your Chrome profile, or send your browsing history anywhere.

## Advanced Users

Run the Python script manually:

```powershell
uv sync
uv run main.py
```

Build the Windows app locally:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

Build the macOS app bundle locally:

```bash
scripts/build_portable_app.sh
```

Build outputs are intentionally ignored by git.

## Maintainers

- Fork/release workflow: `FORKING.md`
- Third-party attribution notice: `THIRD_PARTY_NOTICES.md`
- Windows user guide source: `release/Read Me First - Enable Chrome AI.txt`

## Credits

- Original research/script: [lcandy2](https://github.com/lcandy2)
- Original project: [lcandy2/enable-chrome-ai](https://github.com/lcandy2/enable-chrome-ai)
- Additional inspiration: [show-copilot](https://github.com/hzkaai/show-copilot)

## License

MIT. Keep license and attribution when redistributing derivative work.
