# Enable Chrome AI (One-Click macOS App)

This project repackages the original `enable-chrome-ai` script into a click-and-run macOS app.

The goal is simple: no terminal setup, no manual Python environment steps, and a cleaner user flow for non-technical users.

English | [中文](README.zh.md)

## Quick Start (No Coding)

1. Open [Releases](../../releases).
2. Download the latest `.zip` containing `Enable Chrome AI.app`.
3. Unzip it.
4. Move `Enable Chrome AI.app` to `/Applications` (recommended).
5. Open the app.
6. If macOS blocks it the first time: right-click the app and choose **Open**.
7. Click **Continue** in the app dialog and wait for completion.

## What The App Does Automatically

- Uses the original upstream script source for updates by default (`lcandy2/enable-chrome-ai`).
- Falls back to bundled scripts when update tools or network are unavailable.
- Installs required runtime/dependencies automatically on first run.
- Applies the local graceful-quit compatibility patch, so Chrome is less likely to show an unexpected-close warning.
- Runs the Chrome AI patch process and relaunches Chrome.

## Important Notes

- Chrome may close and reopen while setup runs.
- The script edits your Chrome profile `Local State` file.
- Back up your Chrome profile if you want a rollback option.
- Run the app as the same macOS user that owns the Chrome profile.

## Troubleshooting

- If setup fails, click **Open Logs** in the app dialog.
- Logs and runtime files are stored at: `~/Library/Application Support/Enable Chrome AI/`.
- If Chrome is missing, the app opens the Chrome download page.

## For Maintainers

- Fork/release workflow: `FORKING.md`
- Third-party attribution notice: `THIRD_PARTY_NOTICES.md`
- Rebuild portable app bundle:

```bash
scripts/build_portable_app.sh
```

## Credits

- Original research/script: [lcandy2](https://github.com/lcandy2)
- Original project: [lcandy2/enable-chrome-ai](https://github.com/lcandy2/enable-chrome-ai)
- Repackaging/UX/app-bundle work: this fork

## License

MIT. Keep license and attribution when redistributing derivative work.
