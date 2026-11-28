# Windows EXE 启动器 / Windows launcher

[English guide](#english-guide)

在完整程序目录内双击 **`TENSORA.exe`** 即可使用。可以给它创建桌面快捷方式；不能只复制这个 EXE 到其他目录。运行需要 Windows 10/11 x64、系统 .NET Framework 4.x 和完整程序文件。便携发布包包含 `browser/chrome-win64/chrome.exe`、Node.js、Gmsh 和求解器，不需另行安装浏览器、CAD 或网格程序；源码目录缺少随包浏览器时仍可使用已安装的 Chrome 或 Edge。

## 使用方式

- 启动器为其管理的 Chrome/Edge 应用窗口直接设置原生图标，按窗口 DPI 分别加载标题栏和任务栏尺寸；浏览器刷新 favicon 或移动到不同缩放的显示器后自动恢复，避免将低分辨率 favicon 放大显示。
- 优先使用随包浏览器；源码运行时没有随包浏览器，则使用已安装的 Chrome 或 Edge。没有兼容浏览器时显示错误，不会启动一个无人管理的后台服务。
- 以浏览器 `--app` 模式打开独立软件窗口，去掉常规标签栏和地址栏，沿用现有网页界面。不会更改系统默认浏览器。
- 服务在后台启动，不弹服务器控制台。确认监听成功后才打开窗口，端口冲突时使用后续端口。
- 关闭软件的最后一个窗口后，启动器结束服务，并清理这次会话的浏览器辅助进程和 C++ 计算进程。正在进行的计算也会结束，因此请在关闭之前导出需要保存的模型、结果。
- 同一目录重复双击，只唤回已有窗口。最小化窗口会还原。
- 启动器意外退出时，Windows Job Object 自动清理其进程树。它只管理自己创建的进程，不接管此前运行的本地服务或普通浏览器窗口。

材料库等文件仍保存在原程序目录。浏览器界面设置保存在独立配置目录，第一次使用 EXE 时需要重新选择语言、专业计算等偏好；原来普通浏览器中的偏好不会自动复制。后续启动复用配置及端口。如果原端口后来被其他程序占用而改用新端口，浏览器会将其视为新的本地站点，可能需要重新设置这些偏好。移动程序目录会建立另一套启动器配置。

## 日志和故障排查

每个安装目录使用独立的 `%LOCALAPPDATA%\FemDesktop\<目录标识>\`，其中：

- `launcher.log`：最近一次启动、服务器输出和异常记录。
- `port.txt`：上次成功监听的端口。
- `Browser\Chrome` 或 `Browser\Edge`：独立浏览器配置，不包含你原有浏览器配置的复制件。

启动失败时错误框会给出日志路径。如果缺少程序文件，应重新解压完整包；不要直接打开 `index.html`。保留的 `start.bat` 可以用于控制台调试，它们仍采用原来的浏览器和控制台启动方式。

只读诊断命令（不会启动服务或浏览器）：

```powershell
.\TENSORA.exe --diagnose "$env:TEMP\fem-launcher-diagnose.json"
```

## 构建与验证

源码在 `windows-launcher/`，借鉴同一用户的 HomTube 启动器的浏览器应用窗口方案，增加服务就绪协议、每目录单实例、窗口生命周期及进程树管理。不依赖 Electron 或 npm 安装。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows-launcher\build.ps1
.\node-v24.21.0-win-x64\node.exe --test tests/desktop-server.test.js
```

构建使用 Windows 自带的 .NET Framework C# 编译器，先在独立临时目录构建并运行验证，通过后才覆盖主目录 EXE。测试覆盖默认兼容浏览器选择、路径/参数中的中文和空格、URL/服务身份校验、实际 Windows Job 的子孙进程清理和无关进程保留。Node 测试在临时文件夹中验证端口占用、服务就绪、父进程管道断开、活跃连接关闭，不改动用户材料库。

本机已实测 EXE 打开独立 Chrome 应用窗口、重复启动不新建会话、强制结束启动器后服务与浏览器退出且原有 5173 服务仍保留。桌面工具无法确认应用窗口的浏览器地址，因此未通过界面自动化验证点击右上角关闭按钮。

进程组管理依据 [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)；浏览器在暂停状态下创建，加入组后才恢复，避免子进程在登记前逃逸。Node 的所有者管道断开时主动关闭 HTTP 连接，Job 的关闭清理作为最终保障。
## 端口控制与后台自动化接口

`TENSORA.exe`（桌面与后台模式）、`start.bat` 及 `server.js` 均支持灵活的端口控制，优先级为：**命令行参数 > 环境变量 `PORT` > 状态目录中的 `port.txt` > 默认端口（桌面 `5173` / 后台 `5183`）**。

| 参数 / 环境变量 | 适用入口 | 作用 |
| --- | --- | --- |
| `--port <N>` / `-p <N>` / `PORT=<N>` | `TENSORA.exe`、`start.bat`、`server.js` | 指定监听端口；`0` 表示由操作系统自动分配空闲端口，常规固定端口范围 `1024–65535`。 |
| `--strict-port` / `TENSORA_STRICT_PORT=1` | 全部入口 | 严格端口模式：目标端口被占用时直接报错退出，不向后顺延，避免地址漂移。 |
| `--port-range <N>` / `TENSORA_PORT_ATTEMPTS=<N>` | 全部入口 | 非严格模式下端口冲突时最多向后顺延尝试 `N` 个端口（`0–1000`，默认 `20`）。 |
| `--instance <名称>` | `TENSORA.exe`、`automation-api.js` | 指定命名实例（1–32 位字母/数字/`-`/`_`），隔离互斥锁、停止事件与状态目录（`Headless-<名称>` / `Desktop-<名称>`），支持同一安装目录并发启动多个不同端口的实例。 |
| `--no-open` / `FEM_OPEN_BROWSER=0` | `start.bat`、`server.js` | 仅启动本地 HTTP 服务，不自动打开系统浏览器。 |
| `--headless` / `--stop-headless` | `TENSORA.exe` | 启动或停止独立后台 HTTP 服务（可与 `--port`、`--strict-port`、`--instance` 组合使用）。 |

**直接调用**。从安装目录以随包 Node.js 执行 `automation-api.js` 可读取当前实例的实际地址与完整接口目录（覆盖静力学、损伤变形、结构动力学、流固耦合、二维/三维爆破、材料/炸药/气体/流体库、健康检查 `/api/health`、运行状态 `/api/server-info` 与任务取消 `/api/specialty-runs/{runId}/cancel`）：

- `node automation-api.js`：发现默认后台实例（`Headless/port.txt`），输出完整 JSON；
- `node automation-api.js --instance worker1` / `--desktop` / `--port 5200` / `--all`：按命名实例、桌面模式、指定端口或扫描本安装目录全部在线实例；
- `node automation-api.js --url-only` / `--port-only`：仅输出根地址或端口号，便于脚本直接赋值。

**完整工作区**。`POST /api/automation/session` 按需启动无可见窗口的 Chromium，返回 Chrome DevTools Protocol（CDP）连接地址，供需要绘图、交互划网或后处理页面功能的程序使用；`DELETE /api/automation/session` 可仅关闭无头浏览器引擎而保留 HTTP 服务继续响应求解。并发请求共享同一个会话。无头引擎使用本安装的专用配置。发现接口和会话接口供本机原生客户端使用；具有本机访问权的进程可以控制该会话。

| 响应字段 | 用途 |
| --- | --- |
| `serviceUrl`、`port`、`pid`、`instance` | 当前 TENSORA HTTP 服务根地址、实际监听端口、进程号与实例名 |
| `operations`、`engineRunning`、`strictPort` | 发现接口返回的完整 HTTP 操作目录、无头引擎运行状态与严格端口标志 |
| `browserWebSocketUrl`、`browserUrl` | 会话接口返回的 CDP 地址，支持 Playwright、Puppeteer 等客户端 |
| `pages[]` | 应用页面的 `id`、`title`、`url` 和可直接连接的 `webSocketUrl` |
| `apiVersion`、`installationId`、`ready` | 发现接口版本、安装目录标识和就绪状态 |

引擎启动期间会话接口可能返回 HTTP 503 和 `headless_not_ready`，客户端可按 `Retry-After` 重试。普通桌面模式或缺少浏览器运行时返回 `headless_engine_unavailable`。停止服务会终止其无头引擎与求解器，重新启动后需重新发现地址。

## 导出文件

在启动器窗口中导出当前模型、计算结果、PNG 云图或爆破结果时，会先显示系统“另存为”对话框。选择保存文件夹和文件名后直接写入文件，无需使用浏览器下载列表；取消对话框会结束本次导出。此功能使用 Chrome/Edge 的文件系统访问接口，结果 ZIP 和爆破报告按块写入，写入失败时不会提交不完整内容。

## English guide

Extract the complete Windows x64 ZIP and double-click **TENSORA.exe** inside it. Keep the launcher and runtime directories together. Windows 10 or 11 x64 and the system .NET Framework 4.x are required. The ZIP includes Chromium and Node.js. A source checkout without bundled Chromium can use an installed Chrome or Edge.

The launcher starts the local service in the background and opens a dedicated browser application window. It remembers the port and profile for each installation directory. Double-clicking the launcher again activates the existing window. Save your model and results before closing the last window, which ends the local session and its calculations.

Logs, port preference and browser profiles are stored under `%LOCALAPPDATA%\FemDesktop\<installation ID>\`. Use `start.bat` for console diagnostics or run `TENSORA.exe --diagnose <report path>` for a read-only runtime report. For a source build, run `windows-launcher/build.ps1`.
