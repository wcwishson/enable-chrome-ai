# Enable Chrome AI

Enable Chrome's built-in Gemini / AI features with a simple Windows app.

This project is based on the original research and script by [lcandy2](https://twitter.com/vanillaCitron), with a Windows click-to-run app added for people who do not want to use Python or the command line.

English | [中文](README.zh.md)

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

## Download for Windows

Go to the [Releases](https://github.com/wcwishson/enable-chrome-ai/releases) page and download:

- `EnableChromeAI-Release.zip` if you want the app plus a short user guide.
- `EnableChromeAI.exe` if you only want the app.

Unzip the file if needed, then double-click `EnableChromeAI.exe`.

## How to Use

1. Save anything important in Chrome.
2. Double-click `EnableChromeAI.exe`.
3. If Chrome is open, the app will ask for permission to restart it.
4. Click `OK` to continue.
5. Wait a few seconds while the app applies the fix.
6. Chrome should reopen automatically.
7. Look for Gemini / Chrome AI features in Chrome.

The app is designed for normal Windows users. You do not need Python, PowerShell, or developer tools.

## What the App Does

- Finds your installed Google Chrome profile.
- Closes Chrome so the settings can be updated safely.
- Applies the local Chrome AI availability fix.
- Restarts Chrome and tries to restore your previous windows and tabs.
- Shows a warning if Chrome still reports likely account or region blockers.

## Important Notes

- This app works with Google Chrome on Windows.
- It does not install Chrome for you.
- It does not create a Google account or change your Google account region.
- It cannot guarantee Gemini appears for every Chrome version, Google account, or network location.
- If Chrome recently updated and Gemini disappeared, running the app again may restore it.
- If Gemini still does not appear, make sure Chrome is signed in and your network is using a supported region.

## For Advanced Users

The Python script is still available for people who prefer running it manually:

```powershell
uv sync
uv run main.py
```

You can build the Windows app locally with:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

Build output goes to `dist/`, which is intentionally ignored by git.

## Privacy

The app changes local Chrome settings on your computer. It does not collect your data, upload your Chrome profile, or send your browsing history anywhere.

## License and Credits

Please credit the original project and this Windows version if you repost or share modified builds.

Acknowledgments:

- [lcandy2/enable-chrome-ai](https://github.com/lcandy2/enable-chrome-ai)
- [show-copilot](https://github.com/hzkaai/show-copilot)
