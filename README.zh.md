# Enable Chrome AI

用一个简单的 Windows 小工具，尝试恢复 / 启用 Chrome 内置的 Gemini 和 AI 功能。

本项目基于 [lcandy2](https://twitter.com/vanillaCitron) 的原始研究和脚本，并额外加入了适合普通用户使用的 Windows 双击版程序。

[English](README.md) | 中文

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

## Windows 下载

打开 [Releases](https://github.com/wcwishson/enable-chrome-ai/releases) 页面，下载：

- `EnableChromeAI-Release.zip`：包含程序、说明文件和许可证。
- `EnableChromeAI.exe`：只下载程序本体。

如果下载的是 zip，先解压，然后双击 `EnableChromeAI.exe`。

## 使用方法

1. 先保存 Chrome 中重要的网页或工作。
2. 双击 `EnableChromeAI.exe`。
3. 如果 Chrome 正在运行，程序会提示需要重启 Chrome。
4. 点击 `OK` 继续。
5. 等待几秒钟。
6. Chrome 会自动重新打开。
7. 打开 Chrome，检查右上角或相关页面里 Gemini / Chrome AI 是否恢复。

这个程序面向普通 Windows 用户，不需要安装 Python，也不需要打开命令行。

## 程序会做什么

- 自动找到你的 Google Chrome 配置。
- 关闭 Chrome，避免配置文件正在被占用。
- 应用 Chrome AI 可用性相关的本地修复。
- 重新打开 Chrome，并尽量恢复之前的窗口和标签页。
- 如果 Chrome 仍然显示账号或地区相关的限制，会在运行前给出提示。

## 注意事项

- 这个双击版程序面向 Windows 版 Google Chrome。
- 它不会帮你安装 Chrome。
- 它不会创建 Google 账号，也不会修改你的 Google 账号地区。
- 它不能保证所有 Chrome 版本、所有账号、所有网络环境都一定显示 Gemini。
- 如果 Chrome 自动更新后 Gemini 消失，可以再次运行本程序尝试恢复。
- 如果仍然不显示，请确认 Chrome 已登录账号，并且网络出口位于支持 Gemini in Chrome 的地区。

## 高级用户

如果你想手动运行 Python 脚本，也可以使用：

```powershell
uv sync
uv run main.py
```

本地构建 Windows 程序：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

构建结果会生成在 `dist/`，该目录不会提交到 git。

## 隐私说明

程序只会修改你电脑上的本地 Chrome 设置。它不会收集你的数据，不会上传 Chrome 配置，也不会发送浏览历史。

## 许可与致谢

如果转载或发布修改版，请注明原始项目和此 Windows 版本来源。

致谢：

- [lcandy2/enable-chrome-ai](https://github.com/lcandy2/enable-chrome-ai)
- [show-copilot](https://github.com/hzkaai/show-copilot)
