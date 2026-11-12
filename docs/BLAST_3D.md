# 三维爆破模拟 / 3D blast simulation

[English guide](#english-guide) · [二维爆破](BLAST_DYNAMICS.md) · [三维建模](SOLID_3D.md)

爆破模块现在包含二维与三维两条计算链，共用顶部“爆破库 / 爆破设置 / 爆破结果”页签：

- 关闭“专业计算 → 三维计算”时，页签打开原有二维 TRI3 爆破工作区（TensoraCore，见 [BLAST_DYNAMICS.md](BLAST_DYNAMICS.md)），功能不变。
- 开启“三维计算”后，页签显示为“三维爆破设置 / 三维爆破结果”，在三维工作区中使用三维 CAD、Gmsh 四面体网格、体域材料、约束和载荷，计算由外部开源求解器完成。

三维链参照“损伤变形”模块的结构建立：程序只生成求解器输入、启动随包可执行程序、读取原生输出，不自行实现显式积分、本构或爆轰模型。三维链不是由二维爆破核心扩展而来，两条链互不调用，结果分别保存。

## 调用的开源组件

| 组件 | 作用 | 来源 |
| --- | --- | --- |
| Gmsh（已有） | OpenCASCADE 建模、布尔运算、TET4 网格 | `third_party/gmsh` |
| MFEM 4.10 | 起爆前外载荷 / 围压的静力平衡：`ElasticityIntegrator`、`CGSolver`、`ComputeElementFlux` | 根目录 `mfem-4.10` 源码编译，`third_party/mfem` |
| OpenCourant 20261011 | Starter 检查模型、Engine 显式动力学（`/MAT/ELAST`、`/MAT/JOHN_HOLM` JH2、`/MAT/JWL`、`/DFS/DETPOINT`、`/PLOAD`、`/DAMP`、`/INIBRI`） | 官方 Windows 包，`third_party/opencourant` |
| OpenCourant anim_to_vtk | 把动画帧转为 VTK，再整理为节点场 | 同上 |

OpenCourant 是 OpenRadioss 的社区延续版本，代码结构与根目录 `OpenRadioss-main` 相同。由于本机没有 Intel oneAPI Fortran，使用了与 `OpenCourant-main` 源码同一仓库的官方预编译包，SHA-256 记录在 `third_party/opencourant/README.md`。

## 操作

1. 开启“专业计算 → 三维计算”和“爆破模拟”。在“结构绘制”建立岩体，用圆柱切削出炮孔；JWL 装药时在孔内添加同尺寸圆柱作为装药体域（Gmsh 会生成共节点的两个体域）。
2. 在“计算”页生成四面体网格，给岩体体域分配材料，按需设置约束和外载荷（围压可用法向压力，重力可用体载荷）。
3. 在“爆破库 → 参数类别：岩体材料卡（三维爆破）”中新建材料卡，并在同页“基础材料关联”（或材料库页的“关联爆破材料卡”）把卡绑定到基础材料。所有使用该基础材料的三维岩体体域都按此卡计算；E、ν、ρ 仍取自基础材料。材料卡保存在 `materials/materials.json` 的 `blastMaterials`，关联保存在各材料的 `blastMaterialId`，做法与损伤变形材料库相同。未关联的材料沿用其二维爆破本构（线弹性或 JH2），Mohr–Coulomb 需改为关联 Drucker–Prager 卡。

   | 材料卡 | OpenCourant 卡片 | 损伤输出 |
   | --- | --- | --- |
   | 线弹性 | `/MAT/ELAST`（LAW1） | 无（可叠加失效） |
   | JH2 岩石 | `/MAT/JOHN_HOLM`（LAW79） | 本构损伤 D |
   | HJC 混凝土 | `/MAT/JOHNSON_HOLMQUIST_CONCRETE`（LAW126） | 本构损伤 D |
   | Drucker–Prager | `/MAT/DPRAG1`（LAW10），由 c、φ 按与 Mohr–Coulomb 受压子午线外接的锥面换算 √J2 = k + αp，拉伸截断写入 P_min | 无（可叠加失效） |
   | Johnson–Cook 金属 | `/MAT/PLAS_JOHNS`（LAW2，Iflag = 0）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)，n ≤ 1；ρCp > 0 时计绝热温升，静水拉伸截断写入 Pmin | 塑性应变；εp,max > 0 时删除单元（失效单元比例） |
   | 任一卡 + 拉伸应变失效 | `/FAIL/TENSSTRAIN`：主拉应变 ε₁ 起损伤，ε₂ 时单元失效删除 | 失效准则损伤、失效单元比例 |

   预置两张未关联的模板卡：花岗岩 JH2（与基础材料“花岗岩”的二维 JH2 参数相同）和 C48 混凝土 HJC（Holmquist、Johnson、Cook 1993）。实际岩石需按试验标定。
4. 打开“三维爆破设置”：
   - **体域角色**：岩体 / 装药（JWL）/ 不参与计算。
   - **孔壁压力时程**：在视窗点选孔壁面后点击“把选中面设为孔壁”，输入峰值压力和脉冲时长，可选半正弦或“线性上升 + 指数衰减”。压力由 `/PLOAD` 垂直作用于孔壁并指向岩体。
   - **JWL 装药起爆**：选择爆破库中的炸药，起爆点默认为装药体积中心，也可指定坐标和起爆时间。库中比内能 J/kg 乘以装药密度换算为 OpenCourant 需要的体积能量 E0；CJ 压力缺省时按 ρD²/(γ+1) 估算。
   - **外载荷**：“先静力平衡（MFEM）”先用 MFEM 求解外载荷下的弹性平衡，把单元应力写入 `/INIBRI/STRS_FGLO`，并用初始密度承载静水压力部分，再以 `/CLOAD` 保持外载荷；“突然施加”从零应力开始；“不施加”忽略外载荷。
   - **吸收边界**：点选外边界面加入吸收边界。程序在这些面内侧生成分级 Rayleigh 质量阻尼层（Caughey 吸收层，`/DAMP`，8 层，α 自边界向内二次递减，按往返振幅 1% 设定 α_max = 3·ln(100)·c_p/L）。厚度 0 时自动取 max(2 倍平均边长, 10% 最短模型尺寸)。层厚宜不小于主要波长的一半。
   - 设置计算时长、保存帧数（2–201）、时间步安全系数（`/DT/NODA/CST`）和 CPU 线程数，点击“运行三维爆破模拟”。进度条显示当前阶段、物理时间和 OpenCourant 时间步。
5. “三维爆破结果”页可拖动时间帧、播放，查看：
   - 位移、速度分量及其大小；
   - 六个应力分量、von Mises、压力（压为正）、最大主应力 σ1；
   - 六个应变分量（`/ANIM/BRICK/TENS/STRAIN`，剪切为张量分量 εij = γij/2）、等效应变、最大主应变 ε1、等效塑性应变；
   - 本构损伤 D（JH2/HJC，`/ANIM/ELEM/DAMG`）、拉伸失效损伤（`/ANIM/BRICK/DAMA`）、失效单元体积比例（OpenCourant 删除单元的状态）。

   损伤与失效比例使用固定 0–1 色标。支持外表面与剖面云图、变形放大，并可导出全部帧的 JSON。

## 结果与诊断

- 单元量（应力、压力、损伤、塑性应变）按相邻单元体积加权平均到节点后着色；剖面显示插值后的节点量。
- OpenCourant 在单元严重畸变时也会报告 NORMAL TERMINATION，程序按实际到达的物理时间和场量有限性判断是否完成，提前停止或发散时只保留之前的帧并明确提示。
- 任务目录 `calculation-data/blast3d/run-*` 保存 `model_0000.rad`、`model_0001.rad`、Starter/Engine 列表文件、`solver.log`、`summary.json` 和逐帧二进制场；保留最近 6 个任务。求解在英文临时目录中进行，因此项目可以放在中文路径下。
- 同一服务同时只运行一个三维爆破任务；默认超时 60 分钟，可随时取消（终止子进程）。

## 适用范围与限制

- 拉格朗日四面体（`/TETRA4`，1 积分点）显式动力学，小到中等变形。装药产物用拉格朗日 JWL 单元，大膨胀后可能畸变；炮孔不离散空气，不耦合装药请用孔壁压力模式。拉格朗日空气单元在爆轰载荷下会在数个循环内翻转，因此未提供空气体域。
- 单元删除只来自 `/FAIL/TENSSTRAIN` 和 Johnson–Cook 的 εp,max；没有碎块接触或 ALE/SPH 流固耦合；岩石裂纹以 JH2/HJC 连续损伤表示。
- OpenCourant 20261011 的 `/BCS/NRF` 在四面体三角面上存在越界（详见 `third_party/opencourant/README.md`），所以吸收边界使用阻尼层而非 Lysmer–Kuhlemeyer 黏性边界。阻尼层为近似吸收，需保证边界远离关注区域并做边界距离检查。
- 规模上限 30 万节点 / 120 万四面体，保存帧 ≤ 201。

## 验证

```powershell
.\node-v24.21.0-win-x64\node.exe --test tests/blast3d.test.js
```

回归覆盖：设置校验与卡片格式；200 MPa 孔壁压力下孔壁节点全部向外运动、损伤与应力帧完整；10 MPa 侧向围压经 MFEM 预平衡后节点速度 < 1e-5 m/s（突然施加时 > 1e-2 m/s），初始 σxx 为压应力；耦合 JWL 装药起爆后岩体压力超过 100 MPa；Johnson–Cook 卡被 Starter 接受，孔壁附近产生塑性应变并输出失效单元比例。重新编译 MFEM 驱动：`powershell -File scripts/build-mfem-prestress.ps1`（需要 Visual Studio 2022）。这些算例验证调用链和物理方向，不代替实验标定或网格收敛研究。

## English guide

With **Specialties → 3D analysis** and **Blast** enabled, the Blast setup and Blast results tabs open the 3D blast stages; with 3D off they keep the original 2D TRI3 blast workspace. The 3D chain reuses the 3D CAD model, Gmsh tetrahedral mesh, volume materials, restraints and loads, and only prepares input files, launches bundled solvers and reads their output:

- **MFEM 4.10** (built from the bundled `mfem-4.10` source) solves the static equilibrium under external loads before detonation; the element stresses enter OpenCourant through `/INIBRI/STRS_FGLO` and the initial density.
- **OpenCourant 20261011** (OpenRadioss continuation, official Windows package) runs the Starter and the explicit Engine with linear elastic (`/MAT/ELAST`) or JH2 (`/MAT/JOHN_HOLM`) rock, borehole pressure (`/PLOAD`) or a coupled JWL charge (`/MAT/JWL` + `/DFS/DETPOINT`), and a graded Rayleigh-damping absorbing layer (`/DAMP`). `anim_to_vtk` converts the animation frames.

Rock behavior comes from **rock material cards** in the Blast library (category *Rock material cards (3D blast)*): linear elastic, JH2 (LAW79), HJC concrete (LAW126), Drucker–Prager (LAW10, entered as cohesion and friction angle) or Johnson–Cook metal (LAW2 `/MAT/PLAS_JOHNS`, with optional adiabatic heating, a hydrostatic tension cutoff and element deletion at εp,max), each optionally with tensile strain failure (`/FAIL/TENSSTRAIN`). Link a card to a base material on the same page or on the Materials page; E, ν and ρ come from the base material. Unlinked materials keep their 2D blast law.

Pick borehole wall and absorbing faces in the viewport, choose volume roles (rock, JWL charge, excluded), and run. Results include displacement, velocity, stress and strain components, von Mises stress, pressure, principal stress and strain, equivalent and plastic strain, constitutive damage, tensile failure damage and the failed element fraction on surfaces and sections, with frame playback and JSON export. Lagrangian air volumes are not offered because they invert under detonation loading; use the wall-pressure mode for decoupled charges. `/BCS/NRF` is not used because of an upstream defect with triangular faces.
