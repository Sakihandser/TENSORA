using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("TENSORA")]
[assembly: AssemblyProduct("TENSORA")]
[assembly: AssemblyDescription("Browser application launcher and local server owner")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace FemDesktop {
    public sealed class BrowserSpec {
        public string Name, Path;
        public BrowserSpec(string name, string path) { Name = name; Path = path; }
    }
    public sealed class LaunchOptions {
        public bool Headless;
        public bool StopHeadless;
        public bool StrictPort;
        public bool ShowHelp;
        public string DiagnosePath;
        public string InstanceName;
        public int? Port;
        public int? PortRange;
    }
    public static class Launcher {
        public static bool IsValidInstanceName(string name) {
            if (string.IsNullOrEmpty(name) || name.Length > 32) return false;
            foreach (char c in name) {
                bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_';
                if (!ok) return false;
            }
            return true;
        }
        public static LaunchOptions ParseOptions(string[] args) {
            var opt = new LaunchOptions();
            if (args == null) return opt;
            for (int i = 0; i < args.Length; i++) {
                string arg = args[i] ?? "";
                string value = null;
                int eq = arg.IndexOf('=');
                if (arg.StartsWith("--") && eq > 2) {
                    value = arg.Substring(eq + 1);
                    arg = arg.Substring(0, eq);
                }
                Func<string, string> nextValue = flag => {
                    if (value != null) return value;
                    if (i + 1 >= args.Length) throw new ArgumentException("参数 " + flag + " 缺少取值。");
                    return args[++i];
                };
                if (arg == "--headless") { opt.Headless = true; }
                else if (arg == "--stop-headless") { opt.StopHeadless = true; opt.Headless = true; }
                else if (arg == "--strict-port") { opt.StrictPort = true; }
                else if (arg == "--help" || arg == "-h") { opt.ShowHelp = true; }
                else if (arg == "--diagnose") {
                    opt.DiagnosePath = nextValue("--diagnose");
                    if (string.IsNullOrWhiteSpace(opt.DiagnosePath)) throw new ArgumentException("--diagnose 需要输出文件路径。");
                }
                else if (arg == "--port" || arg == "-p") {
                    int p;
                    string raw = nextValue(arg);
                    if (!Int32.TryParse(raw, out p) || (p != 0 && (p < 1024 || p > 65535)))
                        throw new ArgumentException("端口无效：" + raw + "（允许 0 自动分配，或 1024–65535）。");
                    opt.Port = p;
                }
                else if (arg == "--port-range" || arg == "--max-port-attempts") {
                    int r;
                    string raw = nextValue(arg);
                    if (!Int32.TryParse(raw, out r) || r < 0 || r > 1000)
                        throw new ArgumentException("端口尝试范围无效：" + raw + "（允许 0–1000）。");
                    opt.PortRange = r;
                }
                else if (arg == "--instance") {
                    string name = nextValue("--instance");
                    if (!IsValidInstanceName(name))
                        throw new ArgumentException("实例名无效：" + name + "（仅允许 1–32 位字母、数字、-、_）。");
                    opt.InstanceName = name;
                }
                else {
                    throw new ArgumentException("未知启动参数：" + args[i]);
                }
            }
            return opt;
        }
        public static int ResolveStartPort(LaunchOptions opt, string envPort, string portFile) {
            if (opt.Port.HasValue) return opt.Port.Value;
            int p;
            if (!string.IsNullOrWhiteSpace(envPort) && Int32.TryParse(envPort.Trim(), out p) && (p == 0 || (p >= 1024 && p <= 65535)))
                return p;
            if (!string.IsNullOrEmpty(portFile) && File.Exists(portFile) && Int32.TryParse(File.ReadAllText(portFile).Trim(), out p) && p >= 1024 && p <= 65535)
                return p;
            return opt.Headless ? 5183 : 5173;
        }
        public static string Quote(string value) {
            var result = new StringBuilder("\""); int slashes = 0;
            foreach (char c in value) {
                if (c == '\\') { slashes++; continue; }
                result.Append('\\', c == '"' ? slashes * 2 + 1 : slashes);
                result.Append(c); slashes = 0;
            }
            return result.Append('\\', slashes * 2).Append('"').ToString();
        }
        public static string InstallationId(string root) {
            using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(
                Encoding.UTF8.GetBytes(System.IO.Path.GetFullPath(root).TrimEnd('\\', '/').ToUpperInvariant())))
                .Replace("-", "").Substring(0, 20);
        }
        public static BrowserSpec SelectBrowser(List<BrowserSpec> browsers, string defaultId) {
            foreach (var browser in browsers) if (browser.Name == "Bundled") return browser;
            string preferred = (defaultId ?? "").StartsWith("MSEdge", StringComparison.OrdinalIgnoreCase) ? "Edge" : "Chrome";
            foreach (var browser in browsers) if (browser.Name == preferred) return browser;
            return browsers.Count == 0 ? null : browsers[0];
        }
        public static List<BrowserSpec> FindBrowsers() {
            var result = new List<BrowserSpec>();
            string portable = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, @"browser\chrome-win64\chrome.exe");
            if (File.Exists(portable)) result.Add(new BrowserSpec("Bundled", portable));
            foreach (string executable in new[] { "chrome.exe", "msedge.exe" }) {
                string name = executable == "chrome.exe" ? "Chrome" : "Edge";
                var candidates = new List<string>();
                foreach (var hive in new[] { Registry.CurrentUser, Registry.LocalMachine }) {
                    using (var key = hive.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\App Paths\" + executable))
                        if (key != null) candidates.Add(Convert.ToString(key.GetValue(null)).Trim('"'));
                }
                foreach (string folder in new[] { Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                    Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) })
                    candidates.Add(System.IO.Path.Combine(folder, name == "Chrome" ? @"Google\Chrome\Application\chrome.exe" : @"Microsoft\Edge\Application\msedge.exe"));
                foreach (string candidate in candidates) if (File.Exists(candidate)) { result.Add(new BrowserSpec(name, candidate)); break; }
            }
            return result;
        }
        public static string DefaultBrowserId() {
            using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"))
                return key == null ? "" : Convert.ToString(key.GetValue("ProgId"));
        }
        public static string BrowserArguments(string url, string profile, bool bundled = false) {
            Uri uri;
            if (!Uri.TryCreate(url, UriKind.Absolute, out uri) || uri.Scheme != "http" || uri.Host != "127.0.0.1" || uri.AbsolutePath != "/" || uri.Query != "" || uri.Fragment != "" || uri.UserInfo != "")
                throw new ArgumentException("启动器只允许打开本机计算服务。");
            return "--no-first-run --no-default-browser-check --disable-background-mode " +
                (bundled ? "--disable-infobars " : "") +
                Quote("--user-data-dir=" + profile) + " " + Quote("--app=" + uri.AbsoluteUri);
        }
        public static bool TryReady(string line, int pid, out string url, out int port) {
            url = null; port = 0;
            const string prefix = "FEM_DESKTOP_READY ";
            if (line == null || !line.StartsWith(prefix, StringComparison.Ordinal)) return false;
            try {
                var data = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(line.Substring(prefix.Length));
                if (Convert.ToInt32(data["pid"]) != pid) return false;
                port = Convert.ToInt32(data["port"]); url = Convert.ToString(data["url"]);
                if (port < 1 || port > 65535 || url != "http://127.0.0.1:" + port + "/") { url = null; return false; }
                return true;
            } catch { url = null; port = 0; return false; }
        }

        [STAThread]
        public static int Main(string[] args) {
            Application.EnableVisualStyles();
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string id = InstallationId(root);
            string baseState = System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FemDesktop", id);
            LaunchOptions opt;
            try { opt = ParseOptions(args); }
            catch (Exception parseError) {
                bool quiet = Array.Exists(args ?? new string[0], a => a == "--headless" || a == "--stop-headless");
                if (!quiet) MessageBox.Show("参数错误：" + parseError.Message, "TENSORA", MessageBoxButtons.OK, MessageBoxIcon.Error);
                else Console.Error.WriteLine(parseError.Message);
                return 2;
            }
            if (opt.ShowHelp) {
                string help =
                    "TENSORA 启动参数：\n" +
                    "  --port <N> / -p <N>     指定端口（0 为系统自动分配，或 1024–65535）\n" +
                    "  --strict-port           端口被占用时直接报错，不自动顺延\n" +
                    "  --port-range <N>        端口冲突时最多向后顺延尝试 N 个端口（0–1000，默认 20）\n" +
                    "  --headless              以无窗口后台 HTTP 服务模式启动（默认端口 5183）\n" +
                    "  --stop-headless         停止当前安装目录（或指定实例）的后台服务\n" +
                    "  --instance <名称>       使用独立实例标识与配置目录，允许并发运行多实例\n" +
                    "  --diagnose <路径>       输出只读运行环境诊断 JSON\n";
                MessageBox.Show(help, "TENSORA", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return 0;
            }
            string instanceSuffix = string.IsNullOrEmpty(opt.InstanceName) ? "" : "-" + opt.InstanceName;
            string state = baseState;
            if (opt.Headless) state = System.IO.Path.Combine(baseState, "Headless" + instanceSuffix);
            else if (!string.IsNullOrEmpty(opt.InstanceName)) state = System.IO.Path.Combine(baseState, "Desktop" + instanceSuffix);
            string mutexName = (opt.Headless ? @"Local\FemHeadless-" : @"Local\FemDesktop-") + id + instanceSuffix;
            string stopEvent = @"Local\FemHeadless-Stop-" + id + instanceSuffix;
            string activateEvent = @"Local\FemDesktop-Activate-" + id + instanceSuffix;
            try {
                if (opt.StopHeadless) return StopHeadless(mutexName, stopEvent);
                Directory.CreateDirectory(state);
                if (!string.IsNullOrEmpty(opt.DiagnosePath)) {
                    var selected = SelectBrowser(FindBrowsers(), DefaultBrowserId());
                    File.WriteAllText(opt.DiagnosePath, new JavaScriptSerializer().Serialize(new {
                        root, state, browser = selected == null ? null : selected.Name,
                        browserPath = selected == null ? null : selected.Path,
                        node = System.IO.Path.Combine(root, @"node-v24.21.0-win-x64\node.exe") }), Encoding.UTF8);
                    return 0;
                }
                bool created;
                using (var mutex = new Mutex(true, mutexName, out created)) {
                    if (!created) {
                        if (opt.Headless) return 0;
                        // A duplicate can arrive while the first instance is still
                        // starting. Wait briefly for its activation event to exist.
                        for (int i = 0; i < 20; i++) {
                            try { using (var existing = EventWaitHandle.OpenExisting(activateEvent)) existing.Set(); return 0; }
                            catch (WaitHandleCannotBeOpenedException) { Thread.Sleep(100); }
                        }
                        return 0;
                    }
                    using (var signal = new EventWaitHandle(false, EventResetMode.AutoReset, opt.Headless ? stopEvent : activateEvent))
                        Run(root, state, signal, opt);
                }
                return 0;
            } catch (Exception error) {
                try { File.AppendAllText(System.IO.Path.Combine(state, "launcher.log"), DateTime.Now.ToString("s") + " " + error + Environment.NewLine, Encoding.UTF8); } catch { }
                if (!opt.Headless) MessageBox.Show("启动失败：" + error.Message + "\n\n请保留完整程序文件夹。日志位置：\n" + System.IO.Path.Combine(state, "launcher.log"),
                    "TENSORA", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
        static int StopHeadless(string mutexName, string stopEvent) {
            Mutex owner;
            try { owner = Mutex.OpenExisting(mutexName); }
            catch (WaitHandleCannotBeOpenedException) { return 0; }
            using (owner) {
                var timer = Stopwatch.StartNew();
                while (timer.ElapsedMilliseconds < 10000) {
                    try { using (var signal = EventWaitHandle.OpenExisting(stopEvent)) signal.Set(); break; }
                    catch (WaitHandleCannotBeOpenedException) { Thread.Sleep(50); }
                }
                try { if (!owner.WaitOne(10000)) return 1; }
                catch (AbandonedMutexException) { /* The service exited while owning the mutex. */ }
                owner.ReleaseMutex();
            }
            return 0;
        }
        static void Run(string root, string state, EventWaitHandle activate, LaunchOptions opt) {
            bool headless = opt.Headless;
            string node = System.IO.Path.Combine(root, @"node-v24.21.0-win-x64\node.exe");
            string script = System.IO.Path.Combine(root, "server.js");
            if (!File.Exists(node) || !File.Exists(script)) throw new FileNotFoundException("未找到 Node.js 或 server.js。请将 EXE 放在完整程序目录内，不能单独移动 EXE。");
            var browser = SelectBrowser(FindBrowsers(), DefaultBrowserId());
            if (!headless && browser == null) throw new FileNotFoundException("未找到随包浏览器或系统 Chrome/Edge，请保留完整程序文件夹。");
            string portFile = System.IO.Path.Combine(state, "port.txt");
            int port = ResolveStartPort(opt, Environment.GetEnvironmentVariable("PORT"), portFile);
            string logPath = System.IO.Path.Combine(state, "launcher.log");
            using (var log = new StreamWriter(logPath, false, Encoding.UTF8))
            using (var ready = new ManualResetEvent(false))
            using (var icons = new WindowIcons(System.IO.Path.Combine(root, "assets", "app.ico")))
            using (var job = new ProcessJob())
            using (var server = new Process()) {
                log.AutoFlush = true; object gate = new object();
                Action<string> write = line => { if (line != null) lock (gate) log.WriteLine(DateTime.Now.ToString("s") + " " + line); };
                string readyUrl = null; int readyPort = 0;
                server.StartInfo = new ProcessStartInfo(node, Quote(script)) {
                    WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true,
                    RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
                };
                server.StartInfo.EnvironmentVariables["FEM_OPEN_BROWSER"] = "0";
                server.StartInfo.EnvironmentVariables["FEM_DESKTOP"] = "1";
                server.StartInfo.EnvironmentVariables["TENSORA_INSTANCE"] = string.IsNullOrEmpty(opt.InstanceName) ? (headless ? "default" : "desktop") : opt.InstanceName;
                if (opt.StrictPort) server.StartInfo.EnvironmentVariables["TENSORA_STRICT_PORT"] = "1";
                if (opt.PortRange.HasValue) server.StartInfo.EnvironmentVariables["TENSORA_PORT_ATTEMPTS"] = opt.PortRange.Value.ToString();
                if (headless) {
                    server.StartInfo.EnvironmentVariables["TENSORA_HEADLESS_PROFILE"] = System.IO.Path.Combine(state, "Browser");
                    server.StartInfo.EnvironmentVariables["TENSORA_HEADLESS_BROWSER"] = browser == null ? "" : browser.Path;
                }
                server.StartInfo.EnvironmentVariables["PORT"] = port.ToString();
                server.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) {
                    write(e.Data); string url; int actual;
                    if (TryReady(e.Data, server.Id, out url, out actual)) { readyUrl = url; readyPort = actual; ready.Set(); }
                };
                server.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { write(e.Data); };
                try {
                    server.Start();
                    try { job.Add(server); } catch { server.Kill(); throw; }
                    server.BeginOutputReadLine(); server.BeginErrorReadLine();
                    var startup = Stopwatch.StartNew();
                    while (!ready.WaitOne(100)) {
                        if (server.HasExited) throw new InvalidOperationException("本地服务启动失败。请查看启动日志。");
                        if (startup.ElapsedMilliseconds > 30000) throw new TimeoutException("本地服务启动超时。");
                    }
                    File.WriteAllText(portFile, readyPort.ToString());
                    if (headless) {
                        write("headless service=" + server.Id + " url=" + readyUrl);
                        while (!activate.WaitOne(250)) if (server.HasExited) throw new InvalidOperationException("后台服务意外退出。");
                        return;
                    }
                    string profile = System.IO.Path.Combine(state, "Browser", browser.Name);
                    Directory.CreateDirectory(profile);
                    write("server=" + server.Id + " url=" + readyUrl + " browser=" + browser.Name);
                    using (var windowProcess = job.StartBrowser(browser.Path, BrowserArguments(readyUrl, profile, browser.Name == "Bundled"), root)) {
                        write("browserPid=" + windowProcess.Id);
                        bool seenWindow = false, activationPending = true;
                        var sinceWindow = Stopwatch.StartNew();
                        startup.Restart();
                        while (true) {
                            if (server.HasExited) throw new InvalidOperationException("本地服务意外退出。请重新打开软件；详细信息已写入日志。");
                            var windows = job.Windows();
                            foreach (IntPtr window in windows) icons.Apply(window);
                            if (activate.WaitOne(200)) activationPending = true;
                            if (windows.Count > 0) {
                                seenWindow = true; sinceWindow.Restart();
                                if (activationPending) { ProcessJob.Activate(windows[0]); activationPending = false; }
                            } else if (seenWindow && sinceWindow.ElapsedMilliseconds > 1200) break;
                            else if (!seenWindow && startup.ElapsedMilliseconds > 30000)
                                throw new TimeoutException("浏览器窗口未能打开，请关闭后重试或检查浏览器安装。");
                        }
                    }
                } finally {
                    // Gracefully stop accepting requests; job disposal is the
                    // final guarantee for in-flight solvers and browser helpers.
                    try { if (!server.HasExited) { server.StandardInput.Close(); server.WaitForExit(2500); } }
                    catch (InvalidOperationException) { } catch (IOException) { }
                    job.Dispose();
                    try {
                        // The parameterless overload also drains asynchronous
                        // output callbacks before their log/event are disposed.
                        if (server.WaitForExit(3000)) server.WaitForExit();
                        server.CancelOutputRead(); server.CancelErrorRead();
                    } catch (InvalidOperationException) { }
                    write("Desktop session closed.");
                }
            }
        }
    }
}
