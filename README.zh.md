# Enable Chrome AI ✨

[English](README.md) | 中文

在 Google Chrome 中启用 Gemini、AI 历史搜索、DevTools AI 等创新功能——无需清除数据或重新安装。

轻量 Python 脚本，通过修改本地 Chrome 配置（`variations_country`、`variations_permanent_consistency_country` 和 `is_glic_eligible`）启用浏览器内置 AI 功能，无需额外开关。

## ✅ 环境要求
- Python `3.13+`（见 `.python-version` / `pyproject.toml`）
- 已安装 Google Chrome（Stable/Canary/Dev/Beta）

## ⚡️ 快速开始（uv）
1. 安装 uv（PowerShell，一次性）：`irm https://astral.sh/uv/install.ps1 | iex`（其他 shell 请参考 uv 文档）。
2. 安装依赖（自动创建虚拟环境）：`uv sync`。
3. 运行脚本：`uv run main.py`。
4. 补丁过程中 Chrome 会被关闭；重启后根据提示按 Enter 结束。

## ⚡️ 快速开始（pip）
1. 创建并激活虚拟环境。
2. 安装依赖：`python -m pip install psutil`。
3. 运行：`python main.py`。

## 🔧 做了什么
- 自动定位 Windows / macOS / Linux 上的 Chrome Stable / Canary / Dev / Beta 用户数据目录。
- 关闭顶层 Chrome 进程以避免文件锁，再在补丁后恢复。
- 在 `Local State` 中递归查找并将所有 `is_glic_eligible` 设为 `true`。
- 在 `Local State` 中将 `variations_country` 设为 `"us"`。
- 在 `Local State` 中将 `variations_permanent_consistency_country` 设为 `["<版本号>", "us"]`。
- 重启补丁前已运行的 Chrome 版本。

## ⚠️ 已知限制 / 注意事项
- 脚本假设 `User Data/Local State` 已存在；若缺失可能直接失败（可先启动一次 Chrome 生成配置）。
- 只有在能从进程信息中取到可执行文件路径时，脚本才会自动重启 Chrome。
- macOS 上按进程名（`Google Chrome*`）识别，可能会终止不止"顶层"应用进程。
- Linux 上按可执行文件名 `chrome` 识别；若你的发行版/安装方式使用其他名字，可能不会关闭 Chrome（从而仍可能有文件锁）。

## 🛟 注意
- 脚本会修改现有 Chrome 配置，如需保险请先备份 `User Data`。
- 使用拥有该 Chrome 配置的同一系统用户运行，确保有写入权限。
- 与 Google 无关，风险自担。
