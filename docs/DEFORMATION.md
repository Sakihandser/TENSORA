# 损伤变形专业工作区 / Damage and deformation

[English guide](#english-guide)

2026-11-03，main 分支新增独立的“损伤变形”和“变形结果”页。右上角“专业计算”启用。沿用爆破模块的卡片、配色与操作布局；共享几何、网格与载荷建模，但本构参数、任务、结果及导出独立，不调用爆破求解链或基础线弹性核心。

## 已接入的求解能力

实际调用官方 Windows CalculiX CrunchiX 2.22 静态链接程序。代码仅生成输入、启动程序和解析输出，没有实现有限元求解器、塑性积分或非线性迭代。选择它是因为已有 Windows 可执行程序、原生 J2 塑性与 NLGEOM 增量求解接口；根目录 MFEM 的示例不能直接代替完整的塑性求解应用。

1. 小变形弹性、J2 塑性及线性各向同性硬化。
2. 几何非线性与有限变形塑性。
3. 平面应力 CPS3、平面应变 CPE3 和三维 C3D4。二维采用 1 m 厚度。
4. 比例加载、自动切步、增量上限、取消、30 分钟求解超时、停止原因诊断和已保存的收敛过程。
5. 位移、三维应力张量、原生应变、等效塑性应变 PEEQ、收敛增量浏览、变形倍率与独立 JSON 导出。
6. 实时进度条：读取 CalculiX job.sta 中已成功收敛的载荷增量，显示载荷完成比例、已完成增量数、已用时间和预计剩余时间。失败尝试及切步重试不计入进度。至少两个增量收敛后，按已用时间与载荷完成比例估算剩余求解时间；该估计可能随非线性收敛速度波动，不包含未知的结果整理耗时。取消或失败会停止计时并保留最后进度；只有结果读取成功才显示完成。

各区域 E、ν 从模型材料读取。专用面板按材料显示本构、屈服应力、硬化模量和损伤起始阈值。多个区域引用同一材料 ID 时共享该卡。二维假设、有限变形开关和增量控制属于整个任务。

启用损伤变形专业计算后，打开“变形结果”旁的“损伤变形材料库”页签。左栏列出已保存的材料卡及关联的基础材料，右栏用于编辑卡片。下方“基础材料关联”可查看、更换和解除关联。也可以在基础“材料库”编辑单个材料的关联。引用该基础材料 ID 的模型默认读取关联卡。在模型面板单独编辑时形成随模型 JSON 保存的覆盖项，点击“恢复使用关联材料卡”可重新读取库值。材料库与关联存于项目的 `materials/materials.json`，`materials.js` 是静态镜像。旧版本地服务仍在运行时，页面从项目文件读取卡和关联，并提示保存当前模型后重启程序，以便写入修改。

### 可压缩超弹性材料

二维和三维共用材料库中的 Neo-Hooke 和 Mooney–Rivlin 卡。选用时启用有限变形。卡片界面使用 MPa 输入 `C10` 和 `C01`，用 MPa⁻¹ 输入 `D1`。保存和求解时，`C10`、`C01` 乘以 10⁶ 转为 Pa，`D1` 乘以 10⁻⁶ 转为 Pa⁻¹。`C10` 和 `D1` 须大于零，Mooney–Rivlin 的 `C01` 可为零。默认数值仅用于初始化输入框，实际材料请填写拟合参数。

适配器按 [CalculiX 2.22 手册](https://www.dhondt.de/ccx_2.22.pdf) 生成 `*HYPERELASTIC` 卡。Neo-Hooke 参数顺序为 `C10,D1`，Mooney–Rivlin 为 `C10,C01,D1`。材料的应力与切线刚度由 CalculiX 计算。纯超弹性工况输出位移、应力和应变。

### J2 多线性硬化

J2 卡可粘贴 2–1000 行逗号分隔的 `真应力 (MPa), 等效塑性应变`，首行塑性应变为零，后续应变严格递增且应力不下降。输入曲线时以曲线替代屈服应力和单一硬化模量，留空时沿用原来的双线性参数。程序将真应力转为 Pa，把数据行交给 CalculiX 的 `*PLASTIC` 卡。塑性应变使用无量纲小数。

### 三维 Mazars 混凝土损伤

在损伤变形材料库创建 Mazars 卡并关联基础材料，然后为三维网格的各体域分配对应材料。当前 Code_Aster 任务要求所有体域使用 Mazars 卡，可以为不同体域分配不同卡。三维设置页会自动选择 Code_Aster，使用小变形、准静态固定增量。结果页的 `损伤 D` 来自求解器 `VARI_NOEU` 的 `V1`，可在外表面、剖面和增量回放中查看。模型描述连续材料刚度退化。局部软化结果需要做网格敏感性对照。

支持等效节点力和位移控制。位移控制沿用等效节点力的作用自由度，各分量按其与最大绝对分量的比值缩放，再乘位移幅值和最终载荷系数。固定自由度与位移加载冲突时需要先修改边界条件。网格坐标和位移采用 m，等效节点力采用 N，`E` 从基础材料的 GPa 转为 Pa。Mazars 材料卡系数直接传给 Code_Aster，结果应力采用 Pa，应变和损伤无量纲。

Windows 调用项目内 `third_party/code-aster/runtime-win-x64` 的 Code_Aster 18.1.11、Python 和原生依赖。Fortran 单元目录通过 Windows 可写英文临时目录访问，以支持项目放在中文路径中。任务输入、结果和 `solver.log` 位于 `calculation-data/deformation/aster-*`。设置 `TENSORA_TEST_ASTER=1` 可启用 Mazars 测试。 [Code_Aster Mazars 理论手册](https://code-aster.org/V2/doc/v14/en/man_r/r7/r7.01.08.pdf)

### 三维裂带断裂与便携运行

在共用材料库创建「裂带断裂（三维 OOFEM）」卡，输入单轴抗拉强度和裂带断裂能，再关联基础材料并分配给各体域。三维损伤变形页会调用项目内的官方 OOFEM 3.0 Windows 求解器。当前支持准静态小变形、TET4、等效节点力和位移控制，所有体域均使用裂带材料卡，可分别设置材料参数。

抗拉强度从 MPa 转为 Pa，断裂能采用 J/m²，坐标和位移采用 m，节点力采用 N。原生 `idm1` 根据断裂能与单元特征长度计算指数软化。结果通过 OOFEM 原生 VTK 输出读取，支持表面和剖面的损伤云图与增量回放。模型描述连续裂带内的刚度退化，裂面没有单独的接触自由度。验证裂纹路径时应比较不同网格下的结果。 [OOFEM 材料手册](https://www.oofem.org/resources/doc/matlibmanual/html/node35.html)

直接从 Windows x64 项目目录启动 `TENSORA.exe` 或 `start.bat`。CalculiX、Code_Aster、OOFEM 和 PhAST 的执行文件与运行库保存在 `third_party`，按项目相对路径加载。完整的 Git 工作副本需包含 Git LFS 管理的实际文件。求解时无需系统 Python、WSL 或联网。维护时可以通过 `scripts/bundle-code-aster-runtime.ps1` 重建锁定的 Code_Aster 运行时，或通过 `scripts/setup-fracture.ps1` 和 `scripts/bundle-phast-runtime.ps1` 重建 PhAST 运行时。

| 预置卡 | 本构 | 屈服应力 / 硬化模量 / PEEQ 参考阈值，或 Gc / l₀ | 数据依据 |
| --- | --- | --- | --- |
| Q235 | J2 | 235 MPa / 1430 MPa / 0.10 | [Su 等（2024）室温准静态拟合 §3.2](https://html.rhhz.net/jmsa/html/20240217.htm) |
| ASTM A36 | J2 | 250 MPa / 1970 MPa / 0.093 | [Harwell 等（2025），图 10、表 3](https://www.mdpi.com/2075-4701/15/4/458) |
| AISI 1045 / 45 钢 | J2 | 310 MPa / 7040 MPa / 0.056 | [Murugesan 与 Jung（2019），图 9(a)](https://doi.org/10.3390/ma12040609) |
| 304 不锈钢 | J2 | 205 MPa / 2200 MPa / 0.092 | [Harwell 等（2025），图 10、表 3](https://www.mdpi.com/2075-4701/15/4/458) |
| 6061-T6 | J2 | 276 MPa / 910 MPa / 0.044 | [Harwell 等（2025），图 10、表 3](https://www.mdpi.com/2075-4701/15/4/458) |
| C30/37 | AT2 | 141 J/m² / 0.060 m | [fib MC2010 式 (5.1-9)](https://site.abece.com.br/wp-content/uploads/2023/09/fib_Bull65_NMG.pdf)、[Tanné 等（2018）式 (6)](https://doi.org/10.1016/j.jmps.2017.09.006) |
| C40/50 | AT2 | 147 J/m² / 0.046 m | [fib MC2010 式 (5.1-9)](https://site.abece.com.br/wp-content/uploads/2023/09/fib_Bull65_NMG.pdf)、[Tanné 等（2018）式 (6)](https://doi.org/10.1016/j.jmps.2017.09.006) |

J2 卡采用基础库的名义屈服应力，结合文献试样硬化斜率得到双线性参考模型。PEEQ 阈值取参考应变区间终点，适用于结果标记。AT2 卡以普通混凝土经验式估计 Gc，以均匀拉伸峰值关系估计相场长度。实际批次、热处理、几何和试验工况需要单独校准。

屈服应力及硬化模量输入 MPa，求解使用 Pa。塑性表给定真屈服应力与等效塑性应变，线性段覆盖 εp=0 到 1；超过 1 时遵循 CalculiX 的表外处理，不应据此做大塑性应变预测。硬化模量指 dσ/dεp，不是总应变切线模量。

`settings.materials` 按稳定材料 ID 保存参数；请求中的 `model.materials` 保留该 ID，单元通过 materialNo 关联。结果的 materialSettings 按 materialNo 保存实际采用的卡，损伤指标按所属单元材料的阈值计算，弹性材料的塑性与损伤指标显示为零。旧版模型的全局卡会迁移到各个材料，之后可分别修改。已有 materials 映射时，缺失的材料卡会被求解接口拒绝，不会静默套用全局参数。

节点 forceX/Y 已含点力、分布力和体力，适配器只施加一次；elementNodeLoads 是重复的单元表示，不能再次叠加。载荷为参考构形中的固定方向节点力，不是随动压力。固定约束沿用结构模型。边界上的独立几何点和点载荷锚点纳入约束剖分，静力学和损伤变形共用该网格。两条路径都会检查各网格连通体的 X/Y 平移与面内转动是否被独立约束。CalculiX 当前不提供位移控制、卸载路径、接触或多步循环加载。

## 损伤范围

CalculiX 路径的损伤输出仍是用户阈值定义的 PEEQ / εp,critical 起始指标，达到 1 表示达到该阈值。它是后处理量，不回传本构，不表示刚度退化、损伤演化、裂纹扩展或单元失效。

PhAST 路径直接调用固定版本的上游 StaggeredSolver、QuasiStaticSolver、PhaseFieldDamageSolver 和 FEMOperators。AT2 相场损伤 d∈[0,1] 参与刚度退化，历史场控制不可逆演化。源代码、MIT 许可证、版本提交及文件哈希保存在 `third_party/phast`。

### PhAST 断裂路径的操作

1. 在损伤变形面板选择“脆性断裂演化 · PhAST AT2”，选择平面应变并关闭有限变形。
2. 每个实体材料卡选择“AT2 相场脆性断裂（PhAST）”，填写断裂能 Gc（J/m²）和相场长度 l₀（m）。E 沿用区域材料。不同材料可设置各自的 E、Gc；当前必须具有相同 ν、l₀，超出该组合会拒绝运行而不是套用第一种材料参数。
3. 选择沿用节点力/等效载荷，或者位移控制。位移控制把原载荷节点、方向和相对大小转换为规定移动：uᵢ=目标幅值×Fᵢ/maxⱼ|Fⱼ|×当前载荷比例。原力不再同时施加。与已有固定分量冲突时会报错。该路径适合配置加载边上的节点力，再转换为位移控制；点力转位移仍是点约束，应评估其局部效应。
4. 初始加载增量数在 PhAST 中表示等分目标加载路径的步数，最大允许增量数不参与该路径。没有自动切步。发生上游力学/交替迭代不收敛时，仅保留此前成功步骤并明确标记未完成目标载荷。
5. 生成网格后运行。建议裂纹区 h≤l₀/2；若全局最大边长超过该值，结果页和设置页显示网格提示。网格/长度需独立收敛验证，不能靠放大 l₀ 仅为消除提示。
6. 查看相场损伤、位移、应力和应变；支持缩放、增量动画、基础结果页同步及 JSON/CSV/SVG/PNG 导出。相场损伤图固定色标 0–1。PhAST 单元应力和应变直接保留上游值，专用页使用面积加权节点投影以便显示；材料界面节点投影可能平滑不连续场，不能替代单元结果。

适用范围为小变形、平面应变、准静态脆性断裂；采用 Amor 拉压能量分裂、AT2 及残余刚度 1e-7。裂纹表现为弥散损伤带，不包含离散裂面接触、碎块碰撞、单元删除、J2 塑性耦合或有限变形断裂。几何缺口/应力集中触发裂纹，当前不提供额外的相场预损伤段输入。所有量直接以 SI 传给 Python API（不走上游 YAML 的 mm 换算），单位厚度 1 m。

当前限制为最多 1 万节点、节点数×保存帧数≤100 万、5 分钟超时。程序从 `third_party/phast/runtime-win-x64` 加载嵌入式 Python、CPU PyTorch 和 SciPy。开发者可在重建此目录时用 Python 3.12 执行 `scripts/setup-fracture.ps1`。

验证：`node --test tests/fracture.test.js`；`node tests/fracture-browser.cjs`。粗网格单边缺口板：10×10 mm、20×20 网格、E=210 GPa、ν=0.3、Gc=2700 J/m²、l₀=1 mm、底边固定、顶边规定 y 位移至 28 μm、25 个加载增量。损伤带跨越剩余韧带，节点损伤达到 1，反力从约 1.45 MN/m 峰值下降到约 18.4 kN/m；全部节点损伤保持不可逆。该算例证明调用链和退化行为，不代表完成网格收敛或文献定量复现。还验证了原力控制、异质 E/Gc、不支持组合拒绝及中英文完整交互。

有限变形应力为 Cauchy 应力；应变采用上游 E 输出定义。场值由 CalculiX 外推到原始节点；云图采用单元节点平均值着色，显示的峰值为节点峰值。材料界面上的外推平均值不宜当作积分点极值。

## 结果联动与局部查看

计算完成后，非线性结果会同步到基础“计算结果”页。在左侧“结果来源”选择“基础静力学”或“损伤变形 · CalculiX”，可保留和切换两份独立结果。专用结果页的“在基础结果页查看”按钮可直接打开对应的 CalculiX 结果。两处共享收敛增量、结果类型和变形倍率；切换结果来源不会调用另一模块的求解器，也不会把非线性结果回写到静力学场景。

基础结果页支持位移、应力、应变、等效塑性应变和损伤起始指标；非线性结果不显示静力安全校核。应力和应变为节点外推值的单元平均，专用页的峰值仍为节点峰值，因此这两种统计口径可能不同。表格、SVG 和 PNG 导出使用当前来源及当前增量；非线性 ZIP 的 source.json 记录任务、增量、载荷比例和材料卡，损伤起始指标明确标注为后处理量。

专用结果页支持以鼠标位置为中心的滚轮缩放、拖动平移、放大/缩小按钮和适应窗口；双击画布也可复位。相机缩放独立于物理位移的显示倍率。切换增量、场量和窗口大小会保留观察位置，点击适应窗口可重新完整显示当前变形。色标显示当前场量的节点范围上限及单位。

### 加载与变形过程动画

专用页和基础结果页均提供播放/暂停，专用页还提供从头回放及 0.5×、1×、2×、4× 回放速度。回放从最早的已保存收敛增量开始，按载荷比例推进，不把自适应切步后的每帧误当作等长物理时间。默认 1× 下，归一化载荷比例增加 1 对应约 8 秒播放时间；这是展示速度，不是动力分析的秒数。没有在两个增量之间求解或制造中间状态；只有一个保存增量时不启用播放。手动拖动进度、切换页面/结果来源、重新计算、清空模型或隐藏窗口均会暂停。

专用页默认使用全过程统一色标，避免逐帧自动归一化掩盖载荷变化；也可关闭以查看当前增量的细节。红色箭头表示当前比例载荷的方向和相对大小（密集载荷仅抽样显示），不表示载荷随变形转向。播放只改变显示，不重新求解，也不改变目标载荷或材料参数。

### 失败诊断和未完成结果

最大允许增量数是自动切步后的求解预算，并非预期动画帧数。`max. # of increments reached` 会明确报告增量预算耗尽；`increment size smaller than minimum` 等报告切步后仍不收敛。面板提供 40 / 400 建议设置按钮，但它不保证任意模型在任意载荷下收敛。

这两种可诊断停止如有已收敛过程，接口返回 `ok:true, completed:false, termination:{code,message,convergedFraction,runId}` 和相应 frames。`ok` 仅代表有可读取数据，必须结合 completed 判断目标载荷是否完成。只有与 job.sta 的成功收敛行匹配且场量完整的 FRD 帧才保留；失败尝试的 best solution/residuals 不能进入结果。结果页、基础同步页和导出元数据/报告均明确标记未完成目标载荷。无有效帧、未知求解器错误、取消和超时仍返回错误，完整 solver.log 与诊断记录保存在任务目录。

2026-11-03 对实际“一型裂纹”任务（2045 节点、3534 单元）复现：初始 1 / 最大 10 在载荷比例 0.545288 处耗尽预算，保留 10 个收敛增量；40 / 400 设置仍在 0.546555 附近切步后无法收敛，保留 30 个收敛增量。后一情况不能仅靠加大步数预算保证消除，也不能据此直接断言结构已真实失稳；需要进一步检查模型、工况或采用合适的后屈曲求解路径。本次修复没有降低目标载荷、改变材料或放松收敛判据来制造成功。

## 接口与文件

浏览器请求通过 `Accept: application/x-ndjson` 获取流式进度，服务端依次发送 progress 事件及最终 result 或 error 事件；未指定该请求头的调用仍返回原来的 JSON 结果。状态文件每 500 ms 增量读取一次，用户切换到英文时进度及时间提示同步切换。

独立 API 为 POST `/api/deformation-runs`，请求 `{model,settings}`。每次任务位于 `calculation-data/deformation/run-*`，保存 request.json、job.inp、CalculiX 原生文件、solver.log 和可读取的 result.json。断开请求会终止子进程。CalculiX 支持最多 20 万节点、40 万单元和 1 万增量。求解增量上限与保存帧数解耦。大网格自动设置 FRD 输出间隔，使保存的节点帧记录控制在约 150 万条以内，完整求解保存最终帧。界面显示实际收敛增量数，结果页按已保存帧浏览。中止时若还没有完整的抽样帧，只提供停止原因和日志。PhAST 使用独立的网格和保存帧数限制。

求解器来源、SHA256 与版本见 `third_party/calculix/manifest.json`；GPL 许可证、官方安装说明及对应版本源代码归档随程序保留。二进制使用官方压缩包中的 ccx_static.exe，不依赖 MKL 动态运行库。源码：https://github.com/Dhondtguido/CalculiX；发行文件：https://www.dhondt.de/calculix_2.22_4win.zip。

## 验证

运行 `node --test tests/deformation.test.js tests/i18n.test.js tests/desktop-server.test.js tests/calculation-ipc.test.js` 和 `node tests/deformation-browser.cjs`。专用面板、材料卡、结果页、状态和错误提示均支持原位中英文切换。

三材料原生回归采用相同 E、ν，材料 A 取 σy=250 MPa、H=1000 MPa，材料 B 取 σy=200 MPa、H=4000 MPa，材料 C 为弹性；同样的 300 MPa 载荷分别得到轴向应变 0.0515、0.0265 和 0.0015。浏览器验证两种材料分别配置、各自保存并传入真实求解器，以及英文面板和结果页无残留中文界面文案，切回中文保持输入值。

原生算例验证平面应力与平面应变的解析弹性解；J2 单轴加载 σ=300 MPa、σy=250 MPa、H=1000 MPa，得到 εp=0.05、总轴向应变 0.0515；有限变形路径与小变形响应不同。浏览器检查实际几何建模 → 生成网格 → 点击运行 → 外部求解 → 结果显示，以及参数保存、模块切换隔离和清空。上述检查是小型回归算例，不等于完成工程认证或大规模性能验证。

## English guide

Enable **Damage & Deformation** in Specialties. The workspace uses the geometry, mesh and restraints for the active dimension. The material library is shared between 2D and 3D.

- **CalculiX 2.22** supports elasticity, J2 plasticity with isotropic hardening, and compressible Neo-Hooke and Mooney–Rivlin hyperelasticity. Hyperelastic cards require finite deformation. The interface converts `C10` and `C01` from MPa to Pa and `D1` from MPa⁻¹ to Pa⁻¹. The adapter uses CPS3 for plane stress, CPE3 for plane strain and C3D4 for 3D solids. The 2D input uses unit thickness. The PEEQ initiation indicator is a postprocessing ratio for plasticity.
- **PhAST 0.16.2** provides small-strain plane-strain AT2 fracture with irreversible phase-field damage and stiffness degradation. The portable package includes its Python runtime. Assign fracture energy and phase-field length on each relevant material card. The adapter accepts varying elastic modulus and fracture energy with a shared Poisson ratio and phase-field length.
- **OOFEM 3.0** provides 3D small-strain crack-band fracture through its bundled Windows solver. The material card takes tensile strength in MPa and fracture energy in J/m². The result shows a continuous damage band on the surface or sections.
- **Results and playback.** Browse saved converged increments and inspect the quasi-static loading sequence. Open a snapshot in the standard Results tab or export it with its source and material settings. Runs that stop after converging only part of the load are labeled partial.

Material examples and upstream references are listed above. The notched-specimen screenshot demonstrates phase-field localization. These examples and regression tests establish workflow behavior. Calibrate materials and check mesh convergence separately.
