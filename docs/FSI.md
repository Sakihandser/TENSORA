# 流固耦合专业工作区 / Fluid–structure interaction

[English guide](#english-guide) · [损伤变形](DEFORMATION.md) · [三维爆破](BLAST_3D.md)

2026-11-16，main 分支新增“流固耦合”专业计算，在右上角“专业计算”中启用，出现三个页签：**流体材料库**、**流固耦合**（设置）和**流固耦合结果**。关闭“三维计算”时为二维（TRI3）工作区；开启后两个页签显示为“三维流固耦合 / 三维流固耦合结果”，使用三维 CAD 模型与四面体网格。几何、区域、基础材料、约束和网格与其他工作区共享；区域角色、流体、边界类型、求解参数与结果由本模块独立保存。

参照损伤变形与三维爆破模块的做法，程序只拆分网格、命名边界、生成上游求解器的输入并读取其输出，**不自行实现流场、结构或耦合计算**。

## 调用的开源求解器

| 组件 | 作用 | 来源 |
| --- | --- | --- |
| SU2 8.6.0 `SU2_CFD` | 多区流固耦合：有限体积流场（不可压缩 / 理想气体，层流、SA、SST）、FEA 结构（线弹性、Neo-Hookean 大变形）、流体网格变形、界面插值与分块 Gauss–Seidel 耦合（Aitken 动态松弛或固定松弛）、Newmark 隐式结构时间积分与二阶双时间步流场 | 官方 Windows 预编译程序，`third_party/su2/runtime-win-x64` |
| MFEM 4.10 `mfem_fsi` | 单向耦合的结构求解：把 SU2 壁面压力和剪应力作为边界载荷积分（`VectorBoundaryFluxLFIntegrator`、`VectorBoundaryLFIntegrator`），用 `ElasticityIntegrator` + PCG 求解位移与单元应力 | `third_party/mfem` 内的源码归档及预编译程序 |
| OpenCourant 20261011（OpenRadioss 延续版） | 三维显式瞬态流固耦合：SPH 粒子流体（`/SPHCEL`、`/PROP/SPH`、`/MAT/HYD_VISC` + `/EOS/POLYNOMIAL`）、拉格朗日 TET4 结构（`/MAT/ELAST`）、粒子–结构与粒子–容器壁接触（`/INTER/TYPE7`）、重力（`/GRAV`）、初速度（`/INIVEL`）、节点质量缩放（`/DT/NODA/CST`） | 与三维爆破共用 `third_party/opencourant` |
| Triangle / Gmsh（已有） | 二维 TRI3 与三维 TET4 网格，流体与结构在界面处共节点 | 已有组件 |

## Windows x64 独立运行

复制完整项目文件夹到可写位置，双击 `TENSORA.exe`。启动器优先使用 `browser/chrome-win64` 的 Chromium，并加载项目内的 Node.js、流体库、Triangle WASM、Gmsh 和三套求解器。计算可离线执行。Git 检出时需确保 Git LFS 已填充二进制文件。

三条求解链均以项目内的 `calculation-data/fsi/run-*/work` 为作业目录。求解进程使用相对文件名，项目路径可含中文与空格。作业中间文件默认自动清理，设置 `TENSORA_KEEP_FSI_WORK=1` 可保留排查。Gmsh 的网格工作文件写到 `tmp/solid3d-mesh` 并在请求结束后清理。

当 Intel Fortran 无法用当前 Windows 代码页打开 OpenCourant 的临时文件时，程序会把同一项目目录临时映射到空闲盘符后重试，并在任务退出时解除映射。

在项目根目录运行 `powershell -File scripts/package-solid3d.ps1` 可生成便携包，默认输出到项目内的 `output`。发布包包含流体库、SU2 及 OpenCourant 所需的随包运行库。

## 三维显式瞬态（OpenCourant SPH）

在“三维流固耦合”中把计算方法选为“显式瞬态 · OpenCourant SPH 流体 + 结构”，用于带自由液面的快速瞬态问题：溃坝冲击结构、液体射流或液块撞击、容器晃荡等。

- **建模**：用一个盒体表示容器内腔，再在其中建立初始液体和结构实体，CAD 运算会把它们融合成共享界面的体域。体域角色：液体设为“流体”，结构设为“结构”，其余空间设为“不参与计算”（流体可流入的空腔）。流体和空腔体域的外表面自动成为固定刚性壁；在视窗中把某些面设为“压力出口”或“远场”可让该面开放。结构约束在三维计算页设置。
- **离散**：每个流体四面体生成一个 SPH 粒子，位置为单元形心，质量为 ρV（流体总质量与几何体积一致），光滑长度取 1.2 倍平均粒子间距。结构为线弹性 TET4，E、ν、ρ 取自基础材料。容器壁为节点全固定的壳单元，只作为接触面。粒子与结构、粒子与容器壁通过 `/INTER/TYPE7` 接触耦合，接触刚度取流体体积模量 × 粒子间距，间隙为 1/4 粒子间距。
- **流体参数**：采用弱可压缩模型 p = ρc²(ρ/ρ₀ − 1)。数值声速可自动选择：取特征流速（初速度及按液柱高度自由下落速度）的 10 倍，至少 20 m/s，且不超过真实声速；也可手动指定。运动黏度 μ/ρ 由流体材料库计算后写入 `/MAT/HYD_VISC`。仅支持液体（不可压缩流体卡）。
- **输入**：计算时长、保存帧数、流体初速度、重力加速度、数值声速、时间步安全系数、结构质量缩放、CPU 线程。
- **质量缩放**：钢、铝等刚性结构的显式时间步可能比粒子时间步小几百倍。“自动”只在结构时间步不足粒子时间步的 1/20 时启用：程序在必要的结构节点上增加质量，使时间步不小于粒子时间步的一半，并让重力只作用于流体，避免附加质量产生虚假自重。此时结构惯性被大幅放大，结果信息会给出放大倍数和增加的质量，并注明只适合准静态评估。需要真实结构动力响应时可关闭质量缩放（计算更慢），或加粗结构网格、选用更软的结构。
- **结果**：粒子按当前位置显示为点云，可按流速大小 / 分量、压力、密度着色；结构显示位移、速度与应力；流体和空腔体域的初始外形在结果中隐藏。支持时间帧回放、剖面（结构）、测点和 JSON 导出（含全部粒子数据）。结果信息给出粒子数、间距、数值声速、两种时间步估计、质量缩放与能量误差。

示例（回归测试）：0.4 m × 0.2 m × 0.04 m 容器中，0.1 m × 0.12 m 的水柱在重力作用下溃塌并冲向 x = 0.25 m 处根部固定的橡胶板（E = 5 MPa）。在 0.2 s 内，液体前锋从 x = 0.097 m 推进到 0.249 m 并被板挡住，板的 von Mises 应力在冲击时明显上升；粒子不穿入结构。铝板在同一工况下需要自动质量缩放（惯性放大约 9×10⁴ 倍），结果被标注为只适合准静态评估。SPH 压力含弱可压缩模型固有的数值波动，应结合时间平均或更细的粒子分辨率判断。

## 操作（二维）

1. **结构绘制**：画出流体域（如矩形流道）和结构（如挡板、管壁）。结构区域用右键菜单分配基础材料；**未填充材料的区域默认按流体处理**。“外部空气”孔洞在流场中是刚性障碍物（无滑移壁面）。在结构边界上设置固定支撑（双向约束 → `MARKER_CLAMPED`；单向约束 → 对称 / 滚动支座）。
2. **流体材料库**：选择或新建流体。预置水、海水、空气（可压缩 / 低速不可压）、甘油、液压油、乙二醇、水银、氮气、氦气、二氧化碳，参数与来源写在各条目中。可压缩流体用理想气体（γ、R、T），不可压缩流体用常密度。
3. **流固耦合**设置页：
   - **区域角色与流体**：每个区域选“结构 / 流体 / 不参与计算”，再选流体。
   - **流体边界**：右侧预览中单击边界线或在列表里选类型——无滑移壁面、滑移壁面 / 对称面、速度入口（流速，方向为边界内法向）、压力出口（相对参考压力的静压）、远场（流速与来流方向角）。流体与结构的公共边界自动成为流固界面。
   - **求解方法**：双向耦合（SU2 多区）或单向耦合（SU2 流场 + MFEM 结构）；稳态或瞬态；线弹性或 Neo-Hookean；平面应变或平面应力；层流、SA 或 SST。页面按流体性质、最大入口流速和模型较短边估算雷诺数，Re > 2300 且选层流时给出提示（层流稳态在该区间一般不收敛）。
   - **迭代与输出**：耦合迭代次数、流体 / 结构内迭代、界面松弛、收敛判据（log₁₀ 残差）、时间步长 / 步数 / 保存帧数、CPU 线程。
   - 右侧“网格准备”可直接生成或更新网格。
4. 点击“运行流固耦合计算”。进度条显示时间步、耦合迭代、界面残差和用时，可随时取消。
5. **流固耦合结果**：选择流体压力、流速大小 / 分量、涡量、压力系数（可压缩时另有密度、温度、马赫数）、位移、结构 von Mises 与应力分量；可只显示流体或结构，显示流速矢量和网格线，设置或自动选择变形放大倍率，滚轮缩放、拖动平移；瞬态结果可拖动时间帧或播放；下方显示界面收敛曲线和计算信息，可导出全部帧的 JSON。

## 操作（三维）

1. 开启“三维计算”，在三维结构绘制中建立流体实体（如流道盒体）和与之相接的结构实体，CAD 运算会把相邻实体融合为共享界面的体域。在“计算”页生成四面体网格，为结构体域分配材料，用 CAD 面 / 节点约束设置固定支撑。
2. 打开“三维流固耦合”：为每个体域选“流体 / 结构 / 不参与计算”，选择流体；在视窗中点选流体外表面，选择类型（入口、出口、壁面、滑移、远场）后点击“设为选中面”，未指定的流体外表面按无滑移壁面处理。求解与迭代参数同二维。
3. “三维流固耦合结果”在共享三维视窗中显示流体场（只在流体体域着色）和结构场（只在结构体域着色），支持剖面云图、测点查询、隐藏体域、时间帧回放和 JSON 导出。

## 数据流与单位

- 浏览器把共享网格转换为中性模型（节点、单元、单元角色、单元材料、边界面、节点约束）提交给 `POST /api/fsi-runs`（NDJSON 进度流）。服务端 `fsi-model.js` 把约束转换为结构边界标记，`fsi-deck.js` 拆分流体 / 结构区网格、自动识别界面、写出 SU2 网格与配置或 MFEM 输入，`fsi-runner.js` 启动求解器并读取输出。
- SU2 输出的 ASCII 重启文件提供变形后流体网格坐标与原始变量，VTK 文件提供涡量、压力系数、结构位移与节点应力。结果按项目节点编号保存为逐帧二进制（`calculation-data/fsi/run-*`，保留最近 8 个任务，含 SU2 配置与网格、`solver.log`、`summary.json`）。
- 单位：m、kg、s、N、Pa。二维为单位厚度（1 m）。不可压缩流体的压力为相对出口 / 参考压力的表压；SU2 传给结构的界面载荷为 (p − p∞) 加黏性牵引力，结构未与流体接触的一侧按参考压力处理。
- 单向耦合中，界面剪应力取 SU2 摩阻系数 × 参考动压 ½ρ∞V∞²（与 SU2 系数定义一致）。

## 适用范围与限制

- 流体为单相牛顿流体（常密度或理想气体），马赫数 < 5；不含自由液面、空化、多相流或热耦合。湍流用 SU2 的 SA / SST 模型，需要合适的近壁网格。
- 结构为线弹性或可压缩 Neo-Hookean，材料参数取自基础材料（E、ν、ρ）；结构外载荷（点载荷、重力等）不参与本模块计算，只考虑流体载荷与约束。
- 流体网格随界面位移做弹性变形，大位移时可能出现网格畸变（SU2 会报告最小体积）。强附加质量效应（轻结构 + 重流体）时分区耦合可能需要更小的松弛因子或更多耦合迭代。
- 同一服务同时只运行一个流固耦合任务，默认超时 2 小时。
- 示例与回归测试验证调用链和物理方向，不替代工程验证与网格收敛分析。

## 气动示例 / Aerodynamic examples

[NACA 0012 与三维滑翔机稳态单向耦合 / Steady one-way coupling for NACA 0012 and a 3D sailplane](FSI_AERODYNAMICS.md)

## 验证

```powershell
.\node-v24.21.0-win-x64\node.exe --test tests/fsi.test.js
```

覆盖：网格拆分与界面方向、约束转边界标记、SU2 配置（含 RANS 与理想气体）、不完整模型的报错、流体材料库校验；SPH 卡片生成（粒子数等于流体四面体数、总质量等于 ρV、容器壁与接触卡齐全、软结构不缩放而钢结构自动缩放且重力只作用于流体、气体和无约束结构被拒绝）以及一次真实的 OpenCourant 溃坝计算（水柱前锋前移、顶部下降、帧数据完整）；在柔性壁流道上分别运行 SU2 双向耦合与 SU2 + MFEM 单向耦合——小变形时两条链的最大位移相差 < 2%（实测 5.841×10⁻⁸ m 与 5.843×10⁻⁸ m，von Mises 4.3749 Pa 与 4.3765 Pa）；瞬态 Neo-Hookean 耦合按时间顺序保存帧。重新编译 MFEM 驱动：`powershell -File scripts/build-mfem-fsi.ps1`（需要 Visual Studio 2022）。

## English guide

Enable **Fluid–structure** in Specialties to add the **Fluid library**, **Fluid–structure** (setup) and **FSI results** tabs. With 3D analysis off they work on the 2D TRI3 mesh; with 3D on they become the 3D FSI stages on the tetrahedral mesh. TENSORA only splits the shared mesh, names the boundaries, writes solver inputs and reads the outputs:

- **SU2 8.6.0** (official Windows build shipped with the project) runs the multizone coupling: incompressible or ideal-gas flow (laminar, SA, SST), linear elastic or Neo-Hookean structure, fluid mesh deformation and block Gauss–Seidel coupling with Aitken or fixed relaxation; steady or transient (dual time stepping + Newmark).
- **MFEM 4.10** (built from the bundled source) solves the structure of the one-way path under the SU2 wall pressure and shear.
- **OpenCourant 20261011** (3D only) runs explicit transient FSI with a free surface: one SPH particle per fluid tetrahedron (mass ρV, weakly compressible water with an automatic or user-set numerical sound speed), a Lagrangian TET4 linear elastic structure, node-to-surface contact between particles and the structure or the fixed container walls (exterior faces of fluid and cavity volumes), gravity and an initial fluid velocity. Stiff metal structures can use automatic nodal mass scaling; the inertia factor and added mass are reported and such results are flagged as quasi-static only.

Mark regions (or volumes) as fluid or structure — regions without a material default to fluid — choose a fluid, set inlet, outlet, wall, slip and far-field boundaries, and run. Results show pressure, velocity, vorticity, displacement and structural stress with velocity vectors, deformation scaling, time playback, the interface convergence history and JSON export. The setup page estimates the Reynolds number and warns when a laminar steady solution is unlikely to converge.
