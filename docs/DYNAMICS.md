# 结构动力学专业工作区 / Structural dynamics

[English guide](#english-guide) · [损伤变形](DEFORMATION.md) · [三维爆破](BLAST_3D.md) · [流固耦合](FSI.md)

2026-11-26，main 分支新增“结构动力学”专业计算，在右上角“专业计算”中启用后出现**结构动力学**（设置）和**动力学结果**两个页签。关闭“三维计算”时使用二维 TRI3 工作区；开启后两个页签变为“三维结构动力学 / 三维动力学结果”，使用三维 CAD 模型与四面体网格。几何、区域、基础材料、约束、载荷和网格与其他工作区共享；分析类型、参数、部件初速度、本构卡、刚性墙与结果由本模块独立保存（二维随模型 JSON 的 `dynamicsSettings` 保存，三维随三维模型的 `dynamics3d` 保存）。

与其他专业模块相同，程序只整理模型、写出上游求解器的输入卡片、启动随包的求解器并读取输出，**不自行实现特征值、时间积分、接触或本构计算**。

## 四种分析与调用的求解器

| 分析类型 | 典型问题 | 求解器与关键字 | 主要结果 |
| --- | --- | --- | --- |
| 模态分析 | 固有频率、振型、共振校核 | CalculiX 2.22 `*FREQUENCY`（移位逆迭代 Lanczos / ARPACK，PaStiX 稀疏求解） | 频率、周期、质量归一化振型及应力分布、参与因子、有效质量及累计占比 |
| 谐响应（机械振动） | 激振器、旋转机械不平衡、简谐力作用下的稳态振动 | CalculiX `*FREQUENCY` + `*STEADY STATE DYNAMICS`（模态叠加）+ `*MODAL DAMPING` | 各频率点的位移幅值与相位、应力幅值、周期内 von Mises 峰值、频响曲线 |
| 瞬态动力学（隐式） | 冲击载荷、突加载荷、启停、任意时程强迫振动 | 默认用 CalculiX `*MODAL DYNAMIC` 模态叠加，也可选 `*DYNAMIC,DIRECT` 直接积分。两种方法均支持载荷时程和瑞利阻尼 | 位移、速度、应力随时间的变化，载荷时程 |
| 显式碰撞冲击 | 小球对撞、汽车撞墙、跌落、高速冲击 | OpenCourant 20261011：`/INIVEL`、`/INTER/TYPE7`、`/RWALL/PLANE`、`/GRAV`、`/CLOAD`+`/FUNCT`，材料取自共享卡片库（`blast3d-cards.js`） | 位移、速度、应力、压力、等效塑性应变、本构损伤，动能/内能/塑性功/接触能等能量曲线，刚性墙冲量与墙力 |

## 操作

1. **建模**：二维在“结构绘制”中画出区域并分配材料（需要密度），在“计算”页划分网格；三维在三维工作区建立 CAD 实体、分配体域材料并生成四面体网格。约束与载荷沿用结构模型。
2. **结构动力学**页选择分析类型：
   - 模态：输入所需的弹性模态阶数。程序按网格连通部件和约束方向计算剩余刚体自由度。每个完全自由的三维部件有 6 个，二维有 3 个。求解时额外提取特征对，结果表单独标出近零频率的刚体模态。
   - 谐响应：扫频起点/终点、相邻固有频率之间的频率点数（CalculiX 自动把频率点偏向共振峰）、模态阻尼比 ζ、参与叠加的模态数。结构中的载荷作为简谐力幅值。
   - 瞬态：选择模态叠加或直接积分，设置计算时长、时间步长、保存帧数、瑞利阻尼 α、β 和载荷时程。当时长不是步长的整数倍时，模态叠加使用均分时长且不大于输入值的步长，直接积分允许缩短最后一步。结果帧和测点使用求解器输出的时间。载荷时程可选阶跃、斜坡、正弦、半正弦脉冲、梯形脉冲或时间–系数表格。
   - 显式：计算时长、保存帧数、时间步安全系数、重力、接触摩擦系数、是否部件间自动接触/自接触、是否施加结构外载荷（同样可选时程），以及：
     - **部件初速度**：网格中互不相连的部分自动识别为部件（按颜色显示），为每个部件填写初速度；
     - **材料本构**：每种基础材料可选线弹性、双线性弹塑性（屈服应力、切线模量、可选失效塑性应变）或在“材料绑定”页为该材料激活的爆破材料卡（Johnson–Cook、JH2、Drucker–Prager 等）；
     - **刚性墙**：无限大平面，给出墙上一点与法向（三维可点选部件端面后“在选中面外侧添加刚性墙”），法向自动指向模型一侧。
3. 查看“计算前检查”，点击运行。进度条显示求解阶段、仿真时间、时间步、循环数和已用时间，可随时取消。
4. **动力学结果**：选择结果场；模态和谐响应可“振型动画”（谐响应按各节点相位动画），瞬态和显式可逐帧播放；模态与有效质量表（单击查看该阶振型）；曲线（频响、最大位移/应力时程、载荷时程、能量、墙力、有效质量占比柱状图）；单击节点查看测点曲线（三维用测点面板）；导出结果 JSON 和曲线 CSV。

## 实现要点

- **谐响应峰值与动画**：用每个应力分量的实部、虚部得到周期内 von Mises 应力平方关于正弦和余弦的二次型，其最大特征值的平方根即为周期峰值。二维、三维动画均使用每个节点各自的分量幅值和相位。

- **二次单元**：隐式分析默认把 TET4 / TRI3 网格升阶为 C3D10 / C3D15（共享边中点），弯曲振动频率明显更准确（1 m × 0.1 m 悬臂梁：线性 C3D4 为 101.3 Hz，C3D10 为 83.50 Hz，欧拉梁解析 83.54 Hz）。结果只在原网格节点上读取。
- **二维**：CalculiX 自带的平面单元通过内部展开和多点约束实现，其集中力在 `*STEADY STATE DYNAMICS` 中不能正确传递，且厚截面的平面应力单元表现为“宽板”。因此二维模型由 TENSORA 显式拉伸为一层厚度 t 的楔形单元：平面应变约束全部面外位移；平面应力为可自由变薄的薄层（二次单元在中面、线性单元在底面约束面外刚体位移）。单位厚度载荷按 t 分配到前后面（二次单元按 1/6–2/3–1/6），报告的质量、有效质量按单位厚度换算。二维显式计算与二维爆破相同，采用平面应变单层 HEPH 六面体薄片，能量与力按单位厚度给出。
- **多线程**：CalculiX 线程数按单元数自动选取（每约 1500 单元 1 线程，最多 8），通过 `OMP_NUM_THREADS`、`CCX_NPROC_*` 和 `PASTIX_NUM_THREADS` 传给 PaStiX/ARPACK；随包 PaStiX 多线程偶发堆损坏（0xC0000374）时自动改用单线程重算并在结果中注明。OpenCourant Starter/Engine 使用 `-nt`（每约 4000 单元 1 线程）；动画帧由多个 `anim_to_vtk` 进程并行转换，按顺序读取（81 帧钢球对撞算例的后处理由 37.7 s 降到 13.3 s）。
- **刚性墙力**：`/TH/RWALL` 输出累计法向/切向冲量（N·s），程序给出冲量曲线并以中心差分求墙力。
- 结果按节点逐帧保存为二进制（`calculation-data/dynamics/run-*`，保留最近 8 个任务，含输入卡片、`solver.log` 和 `summary.json`）。

## 接口与文件

| 文件 | 作用 |
| --- | --- |
| `dynamics-settings.js` | 浏览器与 Node 共用的参数规范化、默认值、载荷时程、部件识别（`window.DynamicsSettings`） |
| `dynamics-model.js` | 把二维直接模型或三维网格 + CAD 条件整理为中性模型（坐标、单元、材料、节点力、约束） |
| `dynamics-calculix.js` | CalculiX 卡片（模态 / 谐响应 / 瞬态）、二次单元与二维楔形拉伸、`.dat`/`.frd` 读取 |
| `dynamics-explicit.js` | OpenCourant 卡片（部件、初速度、接触、刚性墙、重力、载荷、材料卡）、帧与时程读取 |
| `dynamics-runner.js` | 任务目录、逐帧二进制保存、摘要与测点接口 |
| `src/core/dynamics-common.js` | 二维页面与三维阶段共用的场名、进度、曲线、模态表与计算信息 |
| `src/pages/dynamics.js`、`dynamics-results.js` | 二维设置页与结果页 |
| `src/pages/solid3d-dynamics.js` | 三维工作区的动力学设置与结果阶段 |

HTTP 接口：`GET /api/dynamics-status`；`POST /api/dynamics-runs`（`{model|solid, settings}`，`Accept: application/x-ndjson` 时流式返回进度）；`GET /api/dynamics-runs/<run>`（摘要）、`/frames/<k>`（Float32 帧）、`/probe?nodes=`（测点序列）。同一服务同时只运行一个动力学任务，默认超时 2 小时。

## 示例模型

`examples/classic-models` 中的脚本生成以下示例（二维在 `Example/二维`，三维在 `Example/三维`）：

| 模型 | 分析 | 要点 |
| --- | --- | --- |
| 悬臂梁模态分析-二维-动力学-线弹性 | 模态 | Q235 1 m × 0.1 m，基频 ≈ 81 Hz（欧拉梁 81.5 Hz），一阶有效质量 ≈ 61% |
| 悬臂梁端部激振谐响应-二维-动力学-线弹性 | 谐响应 | 端部 1 kN/m 简谐力，ζ = 0.02，共振幅值 ≈ 静挠度 / 2ζ |
| 简支梁跨中冲击瞬态-二维-动力学-线弹性 | 瞬态 | 2 m 跨简支梁，跨中 50 kN/m、2 ms 半正弦脉冲，自由振动周期 ≈ 17.5 ms |
| 圆盘对心碰撞-二维-动力学-线弹性 | 显式 | 平面应变钢圆柱 10 m/s 撞静止圆柱，碰后速度交换，动能恢复 |
| 铝环撞刚性墙压溃-二维-动力学-双线性弹塑性 | 显式 | 6061-T6 薄壁环 30 m/s 撞刚性墙，塑性铰与压溃 |
| 钢球对心碰撞-三维-动力学-线弹性 | 显式 | 牛顿摆：A 球 10 → ≈1 m/s，B 球 0 → ≈10 m/s，接触约 0.2 ms |
| 汽车撞刚性墙-三维-动力学-双线性弹塑性 | 显式 | 180 kg 简化车身 + 铝合金吸能盒，15 m/s 撞墙；20.4 kJ 动能中约 19.4 kJ 被吸能盒塑性吸收 |
| 悬臂钢板模态-三维-动力学-线弹性 | 模态 | 400 × 100 × 20 mm，基频 102.8 Hz（解析 102 Hz） |
| 悬臂钢板端部激振谐响应-三维-动力学-线弹性 | 谐响应 | 端面 500 N，低频幅值 7.9×10⁻⁴ m（解析 8.0×10⁻⁴），共振 102.8 Hz |

```powershell
.\node-v24.21.0-win-x64\node.exe examples/classic-models/build-2d.cjs ..\Example\二维 cantileverModal cantileverHarmonic beamImpact diskCollision ringCrush
.\node-v24.21.0-win-x64\node.exe examples/classic-models/build-3d.cjs ..\Example\三维 ballCollision3d carCrash3d plateModal3d plateHarmonic3d
```

## 验证

```powershell
.\node-v24.21.0-win-x64\node.exe --test tests/dynamics.test.js tests/i18n.test.js
.\node-v24.21.0-win-x64\node.exe --test tests/dynamics-browser.cjs
```

回归测试真实调用 CalculiX 与 OpenCourant：三维 C3D10 与二维平面应力悬臂梁基频与欧拉梁解析值相差 < 1%；自由–自由模态给出刚体模态且无伪模态；二维谐响应低频幅值与静挠度相差 < 3%，共振幅值与 1/(2ζ) 放大系数相差 < 10%；三维突加载荷的端部最大挠度为静挠度的 1.8–2.1 倍；两等质量方块对撞后反弹、初始动能与解析值一致；钢杆以 40 m/s 撞刚性墙时塑性功超过初始动能的一半并记录墙力；二维显式对撞按单位厚度给出动能。这些算例验证调用链、单位与物理趋势，不代表网格收敛或工程认证。

## 适用范围与限制

- 隐式分析为线弹性小变形；材料取基础材料的 E、ν、ρ。谐响应与模态叠加只包含所求模态。
- 显式接触为节点–面罚函数接触（每对部件双向），部件之间初始需留有间隙；自接触可用于压溃折叠，但会增加初始穿透处理与计算时间。刚性墙为固定的无限大平面，不能运动。
- 二维显式按平面应变计算（垂直纸面无限长）；圆盘即圆柱。四面体单元偏刚，薄壁结构需要足够细的网格（可用局部加密）。
- 结果中的“振型”为质量归一化值，只表示相对形状；振型应力为相对值。

## English guide

Enable **Dynamics** in Specialties to add the **Dynamics** (setup) and **Dynamics Results** tabs; with 3D Analysis on they become the 3D stages on the tetrahedral mesh. Geometry, materials (density required), restraints, loads and the mesh are shared. TENSORA writes solver input, runs the bundled solvers and reads their output:

- **Modal analysis** — CalculiX `*FREQUENCY`: frequencies, mass-normalized mode shapes, participation factors and effective masses with cumulative ratios. Unrestrained models get extra rigid-body modes, which are labeled; spurious negative eigenvalues are dropped.
- **Harmonic response** — CalculiX `*STEADY STATE DYNAMICS` on the modal basis with modal damping: displacement amplitude and phase, stress amplitude, the von Mises peak over a period and frequency-response curves. The model loads are the force amplitudes.
- **Transient dynamics** uses CalculiX modal superposition by default, with direct integration as an option. Both methods support Rayleigh damping and load histories. For a nonintegral number of steps, modal superposition uses equal increments up to the specified end time. Direct integration can take a shorter final increment. Frame and probe timestamps come from the solver.
- **Explicit impact** — OpenCourant: unconnected mesh pieces are parts with their own initial velocities; node-to-surface contact between parts (optional self-contact), planar rigid walls, gravity and optional time-varying loads; materials are linear elastic, bilinear plastic or a linked OpenCourant card. Results include energies and rigid-wall impulse and force.

Implicit analyses use quadratic elements by default (C3D10; 2D models are extruded into one layer of C3D15 wedges — plane strain fixes the out-of-plane motion, plane stress is a thin free layer — because CalculiX's own plane elements do not carry concentrated loads into steady-state dynamics). Solver threads scale with the mesh size; a multithreaded PaStiX crash is retried on one thread, and OpenCourant animation frames are converted by parallel `anim_to_vtk` processes. The result pages provide contour playback, mode-shape animation, the mode table, curves, node probes and JSON/CSV export. See the examples and validation sections above.
