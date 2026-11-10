# 三维计算 / 3D analysis

[English guide](#english-guide) · [功能演示 / Demonstrations](../README.md#application-tour--功能演示)

开启“专业计算 → 三维计算”后，原有“结构绘制 / 计算 / 计算结果”标签切换到三维工作流。材料继续从现有材料库读取。三维模型与结果可保存为 JSON，`window.tensoraSolid3d.snapshot()` 暴露模型状态供后续专业模块接入。

## 几何与网格

结构绘制支持盒体、圆柱体、球体、圆锥和圆台、STEP 导入，以及现有二维绘图中闭合区域的拉伸。实体特征可以复制、修改尺寸，或改为切削工具。切削可作用于全部实体或指定的建模实体。选定切削目标的操作按特征列表顺序执行，作用于全部实体的切削最后执行。

新特征可选择 XY、XZ、YZ 基准面。局部拉伸正方向分别为 +Z、−Y、+X。特征编辑卡支持绕插入点依次沿全局 X、Y、Z 轴旋转，再按全局 X、Y、Z 坐标平移。点击“二维草图拉伸 / 切除”进入原二维绘图页，刷新并选择区域，设置基准面、法向偏移和拉伸高度。二维结构区域的材料引用随拉伸传入。

绘图时，OpenCASCADE 执行布尔运算，并用表面三角化显示实际几何。STEP 和切孔可在划分四面体前检查。参数修改会自动触发重建，也可点击“重建 CAD”。右侧体域树在绘图阶段即可隐藏、独显实体，显隐只影响显示。

Gmsh OpenCASCADE 负责 CAD 布尔运算、共形体域分割和一阶四面体网格。接触或相交实体保留为可分别赋材的体域，共享界面网格节点。相交处可能产生额外体域，需在计算页检查每个体域的材料。STEP 按文件单位转换为米。右侧 CAD 树可逐体域隐藏、独显、全部显示；隐藏后可看到相邻体域的内部界面。鼠标拖动旋转、滚轮缩放，视图方向按钮提供等轴测、顶、底、前、后、左、右视图，角落坐标指示器显示 ±X/±Y/±Z。

## 材料、约束与载荷

计算页先生成网格，再为各体域分配材料库中的材料。弹性模量按库中的 GPa 转为 Pa。支持 CAD 面或网格节点的 X/Y/Z 分方向零位移约束；支持面总力 N、面力密度 Pa、法向压力 Pa、节点集中力 N、体力密度 N/m³、重力加速度 m/s²。面总力按表面三角形面积分配到节点；面力密度和压力积分为等效节点力；体力与重力按四面体体积分配，重力读取各体域的材料密度。约束与载荷可叠加、单独删除。视图中显示载荷箭头和约束标记；选面后左侧显示面心、面积与近似法向。

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

Generate a mesh and assign a material to each volume. Restrain X, Y or Z displacement on a face or node. Loads include face resultant forces, traction, pressure, nodal forces, volumetric force density and gravity. Gravity uses each volume's material density.

The TET4 solver uses small-strain isotropic linear elasticity and preconditioned conjugate gradients. The result selector includes displacement, six stress and strain components, von Mises stress, equivalent strain and safety checks. Shear strains are tensor components. Surface contours use volume-weighted nodal recovery, except for element-based safety classifications.

### Interior sections

Add a section in Results. Enter a point and choose XY, XZ, YZ or a custom normal. Drag the viewport handle to move the selected plane along its normal. Show sections alone or with a translucent shell. Section coordinates refer to the original mesh. Displacements interpolate nodal values. Stress, strain and safety use the intersected elements. Visible sections share a scale and exclude hidden volumes.

### Performance and scope

The mesh limit is 350,000 nodes and 1.5 million tetrahedra. Gmsh tries HXT with up to eight CPU threads and falls back to Delaunay if HXT fails. The solver offers Auto, CPU and Prefer GPU. Auto uses the native OpenMP CPU iterator for larger meshes and attempts OpenCL FP64 GPU iteration at 1.2 million tetrahedra. GPU failures fall back to CPU. Meshing, assembly and postprocessing run on the CPU. Results show actual backend and stage timings. The Windows native iterator can be rebuilt with `scripts/build-solid3d-pcg.ps1`.

Three-dimensional analysis is static and linear elastic. Complex STEP Boolean operations depend on CAD tolerances. The 2D sketch bridge uses the sampled profile curves. The service transfers double-precision binary arrays to the viewer. Exports use JSON.

Run `node --test tests/solid3d.test.js` and `node tests/solid3d-browser.cjs` for numerical and workflow regressions. The module uses the Gmsh CLI, OpenCASCADE and Three.js. [Gmsh manual](https://gmsh.info/doc/texinfo/gmsh.html) · [Three.js](https://github.com/mrdoob/three.js)
