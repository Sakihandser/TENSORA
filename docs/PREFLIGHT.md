# 计算前检查 / Pre-run checks

[English](#english)

2026-11-16 起，所有计算页面使用统一的“计算前检查”面板：二维静力（计算页右侧）、三维静力、二维与三维损伤变形、二维与三维爆破、二维与三维流固耦合。材料库和流体材料库的编辑表单下方显示“参数检查”。

面板随输入实时更新，按三个级别列出问题：

| 级别 | 含义 | 运行时 |
| --- | --- | --- |
| 必须处理 | 缺少或不可能的输入，例如没有约束、泊松比 ≥ 0.5、E 明显按 MPa 填写、PhAST 选了平面应力 | 点击运行时弹出清单，不启动计算 |
| 提醒 | 很可能出错或难以收敛，例如单位可疑、本构与材料类别不符、层流稳态在高雷诺数下、网格比相场长度粗 | 第一次运行时弹窗确认，同一组提醒确认后不再重复询问 |
| 建议 | 选择本构和参数的指导，例如推荐的本构、参数一致性换算 | 只显示，可折叠 |

每条问题带“定位”按钮：跳到对应页面并高亮输入框；材料问题直接在材料库中打开该材料。各求解器自身的参数校验保持不变，作为最后一道检查。

## 检查内容

- **材料识别**：按名称（钢、铝、混凝土、花岗岩、橡胶等）或参数（E、ρ、强度）把材料识别为金属、混凝土、岩石、玻璃 / 陶瓷、橡胶、聚合物，并给出各模块的推荐本构。
- **单位与合理性**：E 超过 1500 GPa（多为按 MPa 填写）、E 与该类材料常见范围相差 5 倍以上、密度小于 50 kg/m³（多为 g/cm³）、泊松比越界或接近 0.5（线性单元体积锁死）、屈服强度高于抗拉强度、岩石混凝土抗拉高于抗压、屈服应变过大。
- **安全校核**：所选强度理论缺少对应强度时提醒（结果显示“未完成校核”）；脆性材料选第三 / 第四理论、金属选第一 / 第二理论时给出建议。
- **静力模型**：没有材料、没有约束、某方向没有约束、只在一点约束（可能转动）、没有载荷。
- **损伤变形**：本构与材料类别是否匹配（金属 → J2 塑性；橡胶 → 超弹性；混凝土 → 二维 AT2、三维 Mazars / 裂带；岩石 → AT2 / 裂带）；超弹性须开启有限变形，C10、C01、D1 换算的小应变模量与基础材料 E 对比；J2 屈服应变、硬化模量不应超过 E；AT2 换算强度 σc = √(27EGc/256l₀) 与材料抗拉强度对比并给出建议的 l₀，网格边长应不大于 l₀/2；裂带单元尺寸不超过 2EGf/ft²；Mazars EPSD0 与 ft/E 对比；PhAST 需平面应变、小变形、≤1 万节点；三维中 Mazars / 裂带不能与其他本构混用。
- **爆破**：岩石 → JH2 / HJC / DP，混凝土 → HJC，金属 → Johnson–Cook（二维没有金属塑性时说明按线弹性计算）；需要密度；三维孔壁面、装药体域、吸收边界，以及计算时长与应力波传播时间的比较。
- **流固耦合**：入口 / 出口 / 远场是否齐全、结构约束、雷诺数与湍流模型、气体马赫数与可压缩模型、流体结构密度比与界面松弛（附加质量）、瞬态时间步与单元尺寸（每步流过的单元数）和总时长；SPH 只支持液体、无速度入口、无运动来源、缺少空腔、数值声速低于 10 倍特征速度、刚性结构的质量缩放；流体材料的密度、黏度单位和理想气体状态。

规则集中在 `calculation-rules.js`（纯函数，Node 中可测试，`tests/calculation-rules.test.js`），面板与运行拦截在 `src/core/preflight.js`，各页面的输入收集在 `src/pages/preflight-pages.js`（二维与材料库）和 `src/pages/solid3d.js`（三维）。每条结果同时带中文和英文文本，界面语言切换时即时更新。判据是工程经验范围，用于提示而非替代校核。

## English

All calculation pages share one pre-run check panel: 2D statics (right side of Analysis), 3D statics, 2D/3D deformation, 2D/3D blast and 2D/3D FSI. The material and fluid library editors show a parameter check under the form.

The panel updates as you type and lists findings at three levels: **must fix** (missing or impossible input; Run is refused with a list), **warning** (likely wrong or hard to converge; Run asks once for confirmation per set of warnings) and **tip** (model and parameter guidance). Each finding has a **Locate** button that opens the page and highlights the input, or opens the material in the library.

Checks cover material identification and recommended models per module, unit mistakes (E in MPa, density in g/cm³), Poisson's ratio limits and volumetric locking, strength consistency and strength-theory data, restraints and loads, constitutive choice versus material class, hyperelastic, J2, AT2, crack-band and Mazars parameter consistency with mesh-size limits, PhAST requirements, blast laws and sources, and FSI boundaries, Reynolds and Mach numbers, added mass, time step versus cell size, and SPH inputs. The solvers' own validation still runs as a final check. Thresholds are engineering rules of thumb that prompt a review; they do not replace verification.
