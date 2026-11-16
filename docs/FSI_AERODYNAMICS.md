# 稳态气动流固耦合 / Steady aerodynamic fluid–structure interaction

这两个算例通过 TENSORA 的稳态单向流固耦合工作流运行。SU2 求理想气体 Euler 外流，MFEM 用相对于来流静压的表面压力求约束结构的线弹性响应。结构位移显示倍率为 1。以均质等效铝实体示意载荷传递，材料参数为 E = 70 GPa、ν = 0.33、ρ = 2,700 kg/m³。

Both examples use the steady one-way workflow. SU2 solves the external ideal-gas Euler flow. MFEM applies the pressure relative to freestream static pressure to a restrained homogeneous aluminum solid. The deformation display scale is 1.

## 工况 / Setup

| 参数 / Parameter | NACA 0012 | 滑翔机 / Sailplane |
| --- | --- | --- |
| 来流 / Freestream | 40 m/s, 5°, Ma ≈ 0.118 | 35 m/s, 4°, Ma ≈ 0.103 |
| 温度和静压 / Temperature and pressure | 288.15 K, 101,325 Pa | 288.15 K, 101,325 Pa |
| 远场 / Far field | 半径 12 m 圆域 / Circle, radius 12 m | 半径 20 m 的球形域 / Spherical domain, radius 20 m |
| 结构支撑 / Structural fixture | 约束位于 x/c = 0.30、半径 0.02 m 的内圆孔 / Clamped internal bore, radius 0.02 m | 机身内部半径 0.09 m 的球形夹持面 / Clamped internal sphere, radius 0.09 m |
| 网格 / Mesh | 11,450 个流体三角形，2,448 个结构三角形 / 11,450 fluid TRI3, 2,448 structural TRI3 | 239,987 个流体四面体，8,007 个结构四面体 / 239,987 fluid TET4, 8,007 structural TET4 |
| 对流离散与 CFL / Convective discretization and CFL | MUSCL 与自适应 CFL / MUSCL and adaptive CFL | 一阶 Roe，固定 CFL = 12 / First-order Roe, fixed CFL = 12 |

二维外形为 1 m 弦长的闭合尾缘 NACA 0012，按 NASA Turbulence Modeling Resource 给出的闭合尾缘定义生成。二维结构采用单位厚度平面应力。 [NACA 0012 profile definition](https://tmbwg.github.io/turbmodels/naca0012_val.html)

三维几何基于 Innerscene 发布的 CC0 滑翔机模型。从机身和座舱盖、主翼、平尾和垂尾抽取截面，重建约 14.9 m 翼展的封闭简化实体，省略翼梢小翼、起落架和座舱细节。派生的 `airframe.stl` 随算例提供。原始 GLB 的 SHA-256 为 `b995f90d0e0b027f48ce113643196eaf150512947658061ebfe7e24807a741c3`。 [Innerscene Sailplane glider, CC0](https://www.innerscene.com/tools/library/3d-parts/sailplane-glider-5d42002f)

The sailplane is a closed, simplified full-span reconstruction from the CC0 model's fuselage, canopy, wing and tail sections. It spans about 14.9 m and omits the winglets, landing gear and cockpit detail.

## 结果 / Results

| 指标 / Quantity | NACA 0012 | 滑翔机 / Sailplane |
| --- | ---: | ---: |
| SU2 迭代数 / SU2 iterations | 396 | 668 |
| 最终密度残差 lg(RMS) / Final density residual | −8.005 | −8.001 |
| 全域最大节点流速 / Peak nodal speed in the flow domain | 58.1 m/s | 52.8 m/s |
| 结构最大节点米塞斯应力 / Peak nodal von Mises stress | 24.4 kPa | 0.336 MPa |
| 结构最大位移 / Peak displacement magnitude | 0.561 µm | 0.154 mm |

两例均达到 SU2 密度 RMS 残差的对数判据 −8。二维图中的箭头显示速度方向，米塞斯应力集中在内夹持孔附近。三维流速截图截取距机身中面 2.30 m 的 XZ 剖面，剖面色标按该剖面上的流速取值。三维应力截图从略高的侧前方观察，机身保持水平，可同时看到机翼根部和机体表面的应力分布。

Both cases reached the SU2 log-density RMS target of −8. The 2D velocity arrows show the flow direction, and the stress is concentrated near the internal support. The sailplane cut is an XZ section 2.30 m from the center plane. Its legend reflects values on that section.

Euler 模型适合展示加速区、压力传递与约束下的应力分布。阻力、分离、真实夹层结构强度和飞行安全评估需要独立的黏性流动及结构模型验证。

## 复算 / Reproduction

从仓库根目录执行。算例使用项目随附的 Gmsh、SU2 和 MFEM。网格写入 `tmp/fsi-aerodynamics`，作业记录和结果帧写入 `calculation-data/fsi`。

Run from the repository root with the bundled Windows x64 runtimes. The script regenerates the mesh under `tmp/fsi-aerodynamics` and runs the same TENSORA solver workflow used by the application.

```powershell
.\node-v24.21.0-win-x64\node.exe examples/fsi-aerodynamics/run.cjs airfoil
.\node-v24.21.0-win-x64\node.exe examples/fsi-aerodynamics/run.cjs sailplane
```
