# Enable Chrome AI

用于恢复 / 启用 Chrome 内置 Gemini 与 AI 功能的一键工具。

这个 fork 现在包含：

- Windows 双击版：`EnableChromeAI.exe`
- macOS 应用包：`Enable Chrome AI.app`
- 适合高级用户手动运行的 Python 脚本

目标很简单：下载对应系统的应用，运行，让它重启 Chrome，然后检查 Chrome AI 是否恢复。

[English](README.md) | 中文

<img width="512" alt="Google Chrome Gemini in Chrome" src="https://github.com/user-attachments/assets/a88c56a7-f20b-432a-926c-0184194225b4" />

## 下载

打开 [Releases](../../releases) 页面，下载适合你系统的版本。

Windows 用户：

- 下载 `EnableChromeAI-Release.zip`。
- 解压。
- 双击 `EnableChromeAI.exe`。

macOS 用户：

- 下载包含 `Enable Chrome AI.app` 的最新 `.zip`。
- 解压。
- 可以把 `Enable Chrome AI.app` 移到 `/Applications`。
- 打开应用。如果 macOS 第一次拦截，请右键点击应用并选择 `Open`。

## 使用方法

1. 先保存 Chrome 里重要的网页或工作。
2. 打开对应系统的应用。
3. 如果 Chrome 正在运行，允许应用重启 Chrome。
4. 等待应用完成。
5. Chrome 应该会自动重新打开。
6. 检查 Gemini / Chrome AI 是否恢复。

使用打包好的应用时，不需要安装 Python，也不需要打开 PowerShell、Terminal 或开发工具。

## 程序会做什么

- 自动找到你的 Google Chrome 配置。
- 关闭 Chrome，避免配置文件正在被占用。
- 应用 Chrome AI 可用性相关的本地修复。
- 重新打开 Chrome，并尽量恢复之前的窗口和标签页。
- 如果 Chrome 仍然显示账号或地区相关限制，会给出提示。

## 注意事项

- 电脑上必须已经安装 Google Chrome。
- 程序不会创建或修改你的 Google 账号。
- 程序不能保证所有 Chrome 版本、所有账号、所有网络地区都一定显示 Gemini。
- 如果 Chrome 更新后 Gemini 又消失，可以再次运行本程序。
- 如果仍然不显示，请确认 Chrome 已登录账号，并且网络出口位于支持 Gemini in Chrome 的地区。

## 隐私说明

程序只会修改你电脑上的本地 Chrome 设置。它不会收集你的数据，不会上传 Chrome 配置，也不会发送浏览历史。

## 高级用户

手动运行 Python 脚本：

```powershell
uv sync
uv run main.py
```

本地构建 Windows 应用：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

本地构建 macOS 应用：

```bash
scripts/build_portable_app.sh
```

构建输出不会提交到 git。

## 维护者信息

- Fork / 发布流程：`FORKING.md`
- 第三方署名说明：`THIRD_PARTY_NOTICES.md`
- Windows 用户说明源文件：`release/Read Me First - Enable Chrome AI.txt`

## 致谢

- 原始研究 / 脚本：[lcandy2](https://github.com/lcandy2)
- 原始项目：[lcandy2/enable-chrome-ai](https://github.com/lcandy2/enable-chrome-ai)
- 参考项目：[show-copilot](https://github.com/hzkaai/show-copilot)

## 许可

MIT。转载或发布修改版时请保留许可与署名。
