# TENSORA

<p align="center"><img src="assets/tensora-logo.png" alt="TENSORA" width="140" height="140" /></p>

**Computational mechanics and finite element analysis / 计算力学与有限元分析**

TENSORA is an open-source Windows desktop application for building solid mechanics models, generating finite element meshes, solving them locally, and inspecting and exporting the results. The `main` edition covers 2D and 3D linear statics, nonlinear deformation and fracture, and transient blast dynamics. The interface supports English and Simplified Chinese.

TENSORA 是一款开源 Windows 桌面软件，支持固体力学建模、有限元网格划分、本地求解、结果查看与导出。`main` 版覆盖二维和三维线弹性静力学、非线性变形与断裂、瞬态爆破动力学，界面支持英文和简体中文。

[Download v1.2.1 / 下载 v1.2.1](https://github.com/Sakihandser/TENSORA/releases/tag/v1.2.1) · [Release history / 更新日志](CHANGELOG.md) · [All releases / 全部版本](https://github.com/Sakihandser/TENSORA/releases)

## Application tour / 功能演示

The screenshots show TENSORA running local demonstration cases. 图示来自 TENSORA 实际运行的本地演示算例。

| Workspace / 工作区 | What it does / 能做什么 |
| --- | --- |
| **2D statics / 二维静力学** | Draw nodes, lines, arcs, Bézier curves and parameterized shapes. Detect closed regions and voids, assign materials, apply directional supports, and add point, distributed or body loads. Solve plane stress or plane strain on TRI3 meshes with optional ZZ adaptive refinement. / 绘制节点、线段、圆弧、贝塞尔曲线和参数化图形，识别闭合区域和空洞，设置材料、方向约束及点力、分布力和体力。以 TRI3 网格进行平面应力或平面应变求解，支持 ZZ 自适应加密。 |
| **3D analysis / 三维计算** | Import STEP or build and cut solids using OpenCASCADE. Extrude closed 2D profiles, assign materials by volume, apply loads and restraints, and solve small-strain linear elasticity on TET4 meshes. Inspect surface or interior contours. / 导入 STEP，或用 OpenCASCADE 建立和切削实体。可拉伸二维闭合轮廓、按体域赋材、设置载荷与约束，使用 TET4 求解小变形线弹性并查看表面或内部云图。 |
| **Damage and deformation / 损伤变形** | Use CalculiX for quasi-static J2 plasticity and finite deformation. Review saved converged increments and replay the loading history. With the optional PhAST environment, run separate 2D plane-strain AT2 brittle fracture cases. / 通过 CalculiX 求解准静态 J2 塑性和有限变形，查看已收敛增量并回放加载。安装可选 PhAST 环境后，可独立求解二维平面应变 AT2 脆性断裂。 |
| **Blast dynamics / 爆破动力学** | Study transient stress waves around a cavity with prescribed pressure or radial gas–solid coupling. Inspect saved time frames and export contours and histories. The active solid laws are linear elasticity, JH2 and Mohr–Coulomb. / 使用指定压力或径向气固耦合研究空腔周围的瞬态应力波，可逐帧查看并导出云图和时程。现用固体本构包括线弹性、JH2 和 Mohr–Coulomb。 |
| **Materials and exports / 材料与导出** | Maintain shared material cards and specialist libraries. Save model JSON and use the workspace-specific result exports. 2D workflows support table and figure exports. 3D results export to JSON. / 维护共享材料卡和专业库，保存模型 JSON，并按工作区导出结果。二维工作区提供表格和图形导出，三维结果以 JSON 导出。 |

### 2D statics, safety and materials / 二维静力学、安全校核与材料

| Mode I crack, opening / 一型裂纹，张开 | Mode II crack, in-plane shear / 二型裂纹，面内剪切 |
| --- | --- |
| ![Mode I stress components / 一型裂纹应力分量](assets/demo/v1.2.1/mode-i-en.png) | ![Mode II stress components / 二型裂纹应力分量](assets/demo/v1.2.1/mode-ii-en.png) |

| Strength-based safety check / 基于强度准则的安全校核 | Shared material library / 共享材料库 |
| --- | --- |
| ![Mode I safety plot / 一型裂纹安全校核图](assets/demo/v1.2.1/safety-en.png) | ![Editable material cards / 可编辑材料卡](assets/demo/v1.2.1/materials-en.png) |

### 3D CAD, tetrahedral mesh and interior contours / 三维 CAD、四面体网格与内部云图

| CAD preview / CAD 预览 | Mesh and loads / 网格与载荷 |
| --- | --- |
| ![OpenCASCADE cut preview / OpenCASCADE 切削预览](assets/demo/v1.2.1/cad-en.png) | ![Multi-volume tetrahedral mesh / 多体域四面体网格](assets/demo/v1.2.1/mesh-en.png) |

The XY mid-thickness section (z = 0.175 m) shows von Mises stress concentrating around the hole. The nearby YZ section (x = 1.22 m) shows how stress varies through the thickness. Both sections share a color scale and can be moved by coordinates or by dragging the viewport handle. / XY 中厚面（z = 0.175 m）显示孔缘的 von Mises 应力集中，附近的 YZ 横剖面（x = 1.22 m）显示应力沿厚度的变化。两个剖面共用色标，可通过输入坐标或拖动视窗手柄移动。

**Sections only / 仅显示剖面**

![XY and YZ von Mises stress contours without the outer shell / 仅显示 XY 与 YZ 剖面的 von Mises 应力云图](assets/demo/v1.2.1/sections-en.png)

**Sections and translucent shell / 剖面与透明外壳**

![XY and YZ von Mises stress contours with the translucent plate shell / 带透明外壳的 XY 与 YZ 剖面 von Mises 应力云图](assets/demo/v1.2.1/sections-shell-en.png)

### Damage and deformation / 损伤变形

| AT2 phase-field fracture / AT2 相场断裂 | J2 plastic deformation / J2 塑性变形 |
| --- | --- |
| ![Refined AT2 phase-field damage contour for a Mode I notched plate / I 型缺口板加密网格的 AT2 相场损伤云图](assets/demo/v1.2.1/deformation-at2-refined-en.png) | ![Equivalent plastic strain around a notch / 缺口附近的等效塑性应变](assets/demo/v1.2.1/plastic-en.png) |

PhAST solved the Mode I notched plate on a refined mesh of 7,020 TRI3 elements, up from 780. The longest element edge is 0.236 mm for a phase-field length of 1.0 mm. At the 40th and final converged increment, the damage band extends from the initial notch to the opposite edge. The J2 example uses 5,356 triangles to show the equivalent plastic strain near the notch. / I 型缺口板的求解网格从 780 个 TRI3 单元加密到 7,020 个，由 PhAST 重新求解。单元最长边为 0.236 mm，相场长度为 1.0 mm。第 40 个收敛增量为最终结果，损伤带从初始缺口延伸至对侧边界。J2 算例用 5,356 个三角形单元显示缺口附近的等效塑性应变。

### Blast dynamics / 爆破动力学

At 110 µs, the damage contour shows how damage is distributed around the cavity. The viewer also displays the cavity pressure history and supports frame playback. / 110 微秒时刻的损伤云图展示空腔周围的损伤分布。结果页同时显示空腔压力时程，并支持逐帧回放。

![Blast damage contour at 110 microseconds / 110 微秒时刻的爆破损伤云图](assets/demo/v1.2.1/blast-damage-110us-en.png)

## Get started on Windows / Windows 快速开始

1. Download **`TENSORA-v1.2.1-windows-x64.zip`** from the release page and extract the full folder. / 从发布页下载 **`TENSORA-v1.2.1-windows-x64.zip`** 并完整解压。
2. Double-click **`TENSORA.exe`**. Keep it beside its runtime folders. The launcher starts the local service and opens a dedicated application window. / 双击 **`TENSORA.exe`**，并保留其旁边的运行目录。启动器会开启本地服务和独立应用窗口。
3. Use **Structure → Analysis → Results** for 2D statics. Enable the relevant workspace from **Specialties** for 3D analysis, deformation or blast. / 二维静力学使用 **结构绘制 → 计算 → 计算结果**，其他模块从 **专业计算** 启用。
4. Save or export your work before closing the application. The launcher stops its local processes when its last window closes. / 关闭软件前保存或导出工作。最后一个窗口关闭后，启动器会结束本次会话的本地进程。

The Windows x64 ZIP includes the launcher, Node.js, Chromium, Gmsh, CalculiX, the native solvers and OpenMP runtime. The included workflows run locally. PhAST requires a separate Python environment, and GPU solving requires a compatible OpenCL FP64 driver. / Windows x64 ZIP 包含启动器、Node.js、Chromium、Gmsh、CalculiX、原生求解器和 OpenMP 运行库，可在本地运行。PhAST 需要单独安装 Python 环境，GPU 求解需要兼容 OpenCL FP64 的驱动。

[Launcher guide / 启动器说明](docs/WINDOWS_LAUNCHER.md) · [Deformation and PhAST setup / 损伤变形与 PhAST 安装](docs/DEFORMATION.md)

## 3D performance in v1.2.1 / v1.2.1 三维计算性能

3D meshes support up to **350,000 nodes and 1,500,000 tetrahedra**. Gmsh HXT uses up to eight CPU threads. Automatic solver selection uses native OpenMP for CPU iterations from 80,000 tetrahedra and attempts OpenCL FP64 GPU iterations from 1.2 million, with CPU fallback. Assembly and postprocessing run on the CPU.

三维网格上限为 **35 万节点、150 万四面体**。Gmsh HXT 使用最多 8 个 CPU 线程。自动求解从 8 万单元起使用原生 OpenMP CPU 迭代，从 120 万单元起尝试 OpenCL FP64 GPU 迭代，失败时回退 CPU。组装和后处理在 CPU 上执行。

The release was exercised end to end on a mesh of approximately 1.41 million tetrahedra. On an RTX 4070 Laptop GPU, the measured iteration time for a mesh of this size was 5.99 s, versus 7.73 s with the native CPU solver on the same mesh. Timings depend on hardware and model. / 发布验证覆盖约 141 万四面体的完整流程。在一组同网格对照中，RTX 4070 Laptop GPU 的迭代耗时为 5.99 秒，原生 CPU 为 7.73 秒。耗时随硬件和模型变化。

[3D workflow, options and limits / 三维操作、设置与适用范围](docs/SOLID_3D.md)

## Editions and guides / 版本与文档

- [`main`](https://github.com/Sakihandser/TENSORA/tree/main) is the desktop simulation edition described here. / 本页介绍的桌面仿真版。
- [`machine-learning`](https://github.com/Sakihandser/TENSORA/tree/machine-learning) adds dataset generation and GNN mesh-size prediction with finite element verification. / 包含数据集生成、图神经网络网格尺寸预测与有限元验证。
- [Project structure / 项目结构](docs/PROJECT_STRUCTURE.md), [Export format / 导出格式](docs/CALCULATION_EXPORT_FORMAT.md), [2D GPU scope / 二维 GPU 计算范围](docs/GPU_COMPUTE.md)
- [Blast workflow / 爆破流程](docs/BLAST_DYNAMICS.md), [Gas–solid coupling / 气固耦合](docs/GAS_COUPLING.md), [Constitutive models / 本构模型](docs/CONSTITUTIVE_MODELS.md)

For source development, start the service with Node.js 24 and open the URL it prints. / 源码开发可用 Node.js 24 启动服务，再打开终端显示的网址。

```powershell
node server.js
node --test tests/solid3d.test.js tests/deformation.test.js tests/i18n.test.js
```

## Scope and licenses / 适用范围与许可

TENSORA is intended for teaching, mechanics research and reproducible numerical experiments. Verify material data, units, boundary conditions, mesh convergence and results independently for engineering use. The 3D solver is small-strain linear elastic. The 2D plastic strain initiation indicator and the separate AT2 phase-field damage variable have different meanings.

TENSORA 面向教学、计算力学研究和可复现数值试验。工程使用时应独立核验材料、单位、边界条件、网格收敛和计算结果。三维求解采用小变形线弹性。二维塑性损伤起始指标与独立 AT2 相场损伤变量含义不同。

Original project code is distributed under [MIT](LICENSE). Bundled components retain their own licenses, including [Triangle redistribution terms](src/vendor/triangle-wasm/THIRD_PARTY_NOTICES.txt), [OpenRadioss source and AGPL terms](third_party/openradioss-jh2/README.md), and the Gmsh and CalculiX notices in their respective directories. / 原创代码采用 [MIT](LICENSE) 许可证。随附组件适用各自许可，包括 [Triangle 分发条款](src/vendor/triangle-wasm/THIRD_PARTY_NOTICES.txt)、[OpenRadioss 源码与 AGPL 条款](third_party/openradioss-jh2/README.md)，以及 Gmsh 和 CalculiX 目录中的声明。
