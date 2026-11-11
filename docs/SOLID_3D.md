# 三维计算 / 3D analysis

[English guide](#english-guide) · [功能演示 / Demonstrations](../README.md#application-tour--功能演示)

开启“专业计算 → 三维计算”后，原有“结构绘制 / 计算 / 计算结果”标签切换到三维工作流。材料继续从现有材料库读取。三维模型与结果可保存为 JSON，`window.tensoraSolid3d.snapshot()` 暴露模型状态供后续专业模块接入。

## 几何与网格

结构绘制支持盒体、圆柱体、球体、圆锥和圆台、STEP 导入，以及现有二维绘图中闭合区域的拉伸。实体特征可以复制、修改尺寸，或改为切削工具。切削可作用于全部实体或指定的建模实体。选定切削目标的操作按特征列表顺序执行，作用于全部实体的切削最后执行。

新特征可选择 XY、XZ、YZ 基准面。局部拉伸正方向分别为 +Z、−Y、+X。特征编辑卡支持绕插入点依次沿全局 X、Y、Z 轴旋转，再按全局 X、Y、Z 坐标平移。点击“二维草图拉伸 / 切除”进入原二维绘图页，刷新并选择区域，设置基准面、法向偏移和拉伸高度。二维结构区域的材料引用随拉伸传入。

绘图时，OpenCASCADE 执行布尔运算，并用表面三角化显示实际几何。STEP 和切孔可在划分四面体前检查。参数修改会自动触发重建，也可点击“重建 CAD”。右侧体域树在绘图阶段即可隐藏、独显实体，显隐只影响显示。

Gmsh OpenCASCADE 负责 CAD 布尔运算、共形体域分割和一阶四面体网格。接触或相交实体保留为可分别赋材的体域，共享界面网格节点。相交处可能产生额外体域，需在计算页检查每个体域的材料。STEP 按文件单位转换为米。右侧 CAD 树可逐体域隐藏、独显、全部显示；隐藏后可看到相邻体域的内部界面。鼠标拖动旋转、滚轮缩放，视图方向按钮提供等轴测、顶、底、前、后、左、右视图，角落坐标指示器显示 ±X/±Y/±Z。

## 材料、约束与载荷

在计算页的“约束与载荷”中选择“CAD 几何约束与载荷”，可以在网格生成前为面上单点、整面、CAD 边、面上线段和局部面设置边界条件。勾选 Ux、Uy、Uz 可固定相应方向。选择“CAD 面上点”后，在视窗点击即可定位，或在下方编辑全局坐标。曲面拾取时，划网格会将视窗选取的位置投到所选 CAD 曲面。直接输入坐标时，点须位于所选的实际 CAD 面上。

面上线段可以输入两个端点的全局坐标，也可以在选中的面上拾取端点。局部面适用于平行于 XY、XZ 或 YZ 的 CAD 平面，输入面内的坐标上下限，留空的一侧取该面的边界。软件用线段或矩形范围与所选面的相交部分构造网格边界。

例如，取半梁底面 y = 0 上 x = 0.08 m 的支承线，可输入 (0.08, 0, 0) 和 (0.08, 0, 0.02)，仅约束 Uy。跨中面 x = 0 的剩余韧带可用“局部面”输入 y 下限 0.02 m，仅约束 Ux。点击“生成四面体网格”后，Gmsh 将几何边界条件的点、线和局部面边界纳入共形网格，软件绑定相应节点和边界单元。保存三维模型会同时保留几何边界条件和已有绑定。修改几何边界条件后可重新划分网格，原先按旧网格添加的约束和载荷需要重新设置。

计算页提供“设置局部面载荷”和“设置线载荷”快捷入口。已有网格时，两个按钮会切换到 CAD 设置阶段。添加几何载荷后重新划分网格，软件会将局部面或线段纳入网格，并绑定新的边界单元。

- 面上点施加集中力（N）。
- CAD 边和面上线段支持均匀线载荷和**线线性分布载荷**（N/m）。线性载荷输入两个端点处的三个力分量。面上线段采用输入的起止顺序。开放 CAD 边从按 X、Y、Z 依次比较坐标得到的较小端点起算，沿离散边的弧长变化，可交换起止方向。长度为 0.02 m 的加载线若从 0 线性变到 −50,000 N/m，总力为 −500 N。
- 整面或局部面可设面总力（N）、均匀面力密度或法向压力（Pa），也可设**面线性分布力**和**面线性法向压力**。“单轴起止值”用一个轴上的两个参考坐标定义强度。“多轴梯度”输入参考点的强度及其对 X、Y、Z 的梯度（Pa/m）。例如，法向压力可用 p = p₀ + gₓ(x−x₀) + gᵧ(y−y₀) + g𝓏(z−z₀) 定义，三分量面力密度的每个分量都可独立指定梯度。整个选定面使用同一分布，压力以压入实体为正。
- CAD 体域可施加体力密度（N/m³）或重力加速度（m/s²），作用范围可为选定体域或整个模型。

生成网格后，为各体域分配材料。弹性模量按库中的 GPa 转为 Pa。“网格约束与载荷”仍支持直接约束整面或单个网格节点，以及面载荷、集中力和体载荷。线与面载荷按单元形函数积分为等效节点力，重力读取体域材料的密度。

勾选“载荷与约束符号”可显示已施加的线和面载荷。箭头指向当地载荷方向，同一项载荷内的箭头长度反映不同位置的相对强度。CAD 阶段和网格生成后都可查看。

## 求解与结果

求解器采用小变形各向同性线弹性 TET4、按体域材料组装稀疏刚度矩阵，并用对角预条件共轭梯度求解。结果提供 X/Y/Z 位移与位移量、六个应力分量、六个应变分量、von Mises 应力、等效应变和安全校核图。剪应变显示张量剪应变 εij=γij/2。节点云图采用相邻单元体积加权平均；安全图按表面三角形所属单元分类，沿用二维材料的 Rankine、Saint-Venant、Tresca、von Mises 准则。缺少准则需要的强度参数时标记“未完成校核”。模型、网格线、载荷、节点、坐标轴及变形可按图层显示。

## 剖面云图

结果页的“剖面云图”可同时显示多个剖面。选中剖面后，可输入平面经过的 X、Y、Z 坐标，选择坐标平面或输入自定义法向，也可以拖动视窗手柄沿法向移动。剖面使用原始网格坐标，可单独显示或与透明外壳一起显示。位移云图插值节点结果，应力、应变和安全校核直接显示相交四面体的单元值。可见剖面共用一个色标，隐藏的体域也会从剖面中移除。

## 边界与验证

当前求解范围为静态线弹性。分析网格最多 350,000 个节点和 1,500,000 个四面体。Gmsh 优先使用最多 8 线程的 HXT 算法，HXT 执行失败时重试 Delaunay。分析网格通过二进制 MSH2 读取。

计算页可选择自动、CPU 或优先 GPU。自动模式在达到 120 万四面体时尝试使用 OpenCL FP64 GPU，其余规模使用 CPU。较大模型的 CPU 迭代使用原生 OpenMP。驱动不兼容、显存不足或 GPU 结果未通过残差检查时，自动转用 CPU。刚度装配、网格划分和结果处理在 CPU 上执行。结果页显示实际后端及各阶段耗时。Windows 下可运行 `scripts/build-solid3d-pcg.ps1` 重建原生迭代器。

三维结果在界面与后台之间使用双精度二进制数组传输，导出仍使用 JSON。复杂 STEP 的布尔切削仍受 CAD 容差影响，导入的 STEP 可整体参与切削。二维曲线轮廓沿用现有二维绘图的离散轮廓。

来源：[Gmsh OpenCASCADE](https://gmsh.info/doc/texinfo/gmsh.html)、[Gmsh STEP 示例](https://github.com/gmsh-project/gmsh/blob/master/tutorials/python/t20.py)、[MFEM 线弹性示例](https://github.com/mfem/mfem/blob/master/examples/ex2.cpp)、[Three.js](https://github.com/mrdoob/three.js)。本模块调用随包 Gmsh，可独立运行；MFEM 示例用于核对弹性方程形式，三维求解器采用独立 JavaScript 实现。验证命令：`node --test tests/solid3d.test.js`、`node tests/solid3d-browser.cjs`。

## English guide

Enable **Specialties → 3D analysis** to switch the Structure, Analysis and Results tabs to the 3D workflow. Materials come from the existing library. Models and results can be exported as JSON.

### Geometry and mesh

Build boxes, cylinders, spheres, cones and frustums, import STEP, or extrude a closed 2D region. Feature cards support dimensions, duplication, rotations about the insertion point and translations along world axes. The XY, XZ and YZ base planes have positive extrusion directions +Z, −Y and +X. Cuts can target a modeling solid or all solids. Targeted cuts run in list order, followed by global cuts.

OpenCASCADE rebuilds the visible CAD surface before volume meshing. The volume tree can hide and isolate bodies. STEP units are converted to metres. Touching or intersecting solids are split into conforming volumes with shared interface nodes. Check material assignment if an intersection creates additional volumes.

### Loads, solve and results

In Analysis, choose **CAD restraints and loads** before generating the mesh. Select a face, an edge, a point on a face, or a line defined by two endpoints. For a partial face, select a plane parallel to XY, XZ or YZ and enter coordinate bounds in metres. Blank bounds use the face limits. Gmsh includes the selected geometry in the mesh. Saved models retain the CAD conditions and their bindings. Mesh again after editing a CAD condition.

Apply point forces in N, uniform or linearly varying loads along segments or open CAD edges in N/m, and surface traction or normal pressure in Pa. A linear line load uses endpoint intensities. On an open CAD edge it varies with the length along the meshed edge. Linear surface loads on whole or partial faces support a single axis with endpoint values or an intensity at a reference point and independent X, Y and Z gradients. Positive pressure acts into the solid. With **Load and restraint symbols** enabled, arrows show direction and relative intensity within each load before and after meshing. CAD volumes accept body force density or gravitational acceleration.

After meshing, assign a material to each volume. **Mesh restraints and loads** supports direct face or node restraints, face resultant forces, traction, pressure, nodal forces, volumetric force density and gravity. Gravity uses each volume's material density. Line and surface loads are integrated with the element shape functions. Set mesh-based restraints and loads again after regenerating the mesh.

The TET4 solver uses small-strain isotropic linear elasticity and preconditioned conjugate gradients. The result selector includes displacement, six stress and strain components, von Mises stress, equivalent strain and safety checks. Shear strains are tensor components. Surface contours use volume-weighted nodal recovery, except for element-based safety classifications.

### Interior sections

Add a section in Results. Enter a point and choose XY, XZ, YZ or a custom normal. Drag the viewport handle to move the selected plane along its normal. Show sections alone or with a translucent shell. Section coordinates refer to the original mesh. Displacements interpolate nodal values. Stress, strain and safety use the intersected elements. Visible sections share a scale and exclude hidden volumes.

### Performance and scope

The mesh limit is 350,000 nodes and 1.5 million tetrahedra. Gmsh tries HXT with up to eight CPU threads and falls back to Delaunay if HXT fails. The solver offers Auto, CPU and Prefer GPU. Auto uses the native OpenMP CPU iterator for larger meshes and attempts OpenCL FP64 GPU iteration at 1.2 million tetrahedra. GPU failures fall back to CPU. Meshing, assembly and postprocessing run on the CPU. Results show actual backend and stage timings. The Windows native iterator can be rebuilt with `scripts/build-solid3d-pcg.ps1`.

Three-dimensional analysis is static and linear elastic. Complex STEP Boolean operations depend on CAD tolerances. The 2D sketch bridge uses the sampled profile curves. The service transfers double-precision binary arrays to the viewer. Exports use JSON.

Run `node --test tests/solid3d.test.js` and `node tests/solid3d-browser.cjs` for numerical and workflow regressions. The module uses the Gmsh CLI, OpenCASCADE and Three.js. [Gmsh manual](https://gmsh.info/doc/texinfo/gmsh.html) · [Three.js](https://github.com/mrdoob/three.js)
