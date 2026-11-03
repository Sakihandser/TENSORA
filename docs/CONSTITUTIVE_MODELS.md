# 爆破本构模型

2026-11-01 新增 Noble–Abel、Stiffened Gas、线弹性与 Mohr–Coulomb。保留 JWL、理想气体与 JH2。界面选项及说明使用本构名称；代码来源与许可在技术文件中保留。

| 位置 | 可选模型 | 本次新增 |
| --- | --- | --- |
| 产物状态方程 | JWL、理想气体、Noble–Abel、Stiffened Gas | Noble–Abel、Stiffened Gas |
| 间隙气体状态方程 | 理想气体、Noble–Abel、Stiffened Gas | Noble–Abel、Stiffened Gas |
| 固体本构 | 线弹性、JH2、Mohr–Coulomb | 线弹性、Mohr–Coulomb |

Noble–Abel 和 Stiffened Gas 来自 [LANL Singularity-EOS](https://github.com/lanl/singularity-eos/tree/b4f71a7748770dfa6ce4d678754c463c09262fb7)，固定提交不变，新增两个原始头文件并在现有 EOS DLL 中实例化。两个模型在该版本缺少密度—压力到比内能的反算方法，因此以其压力接口数值求根，不复制状态方程公式。每次计算拒绝余容积奇点、非正温度域和被库截断的非正压力状态。

线弹性和 Mohr–Coulomb 来自 [CB-Geo MPM](https://github.com/cb-geo/mpm/tree/53fcb7609375fd44bf3481d24ee18bfdf0393adb)，下载固定提交的材料类、工具和依赖，原始文件保持不变。仅使用材料接口，不引入其网格或 MPM 动力学程序。JH2 的固定版本及参数保持不变。

## 参数、单位与保存

| 参数 | 界面单位 | 本构输入 |
| --- | --- | --- |
| 余容积 b | m³/kg | 原值；Noble–Abel 要求 bρ < 1 |
| 压力偏置 p∞ | MPa | Pa，乘 10⁶ |
| 参考能量 q | MJ/kg | J/kg，乘 10⁶；当前界面接受非负值 |
| 比内能 e、密度 ρ | MJ/kg、kg/m³ | J/kg、kg/m³ |
| 摩擦角、剪胀角及残余角度 | 度 | 按度传入，材料库内部转弧度 |
| 黏聚力、残余黏聚力、拉伸截断 | MPa | Pa，乘 10⁶ |
| 软化开关、塑性应变 | 0/1、无量纲 | 原值 |
| 工程剪切 | 无量纲 | 张量剪切乘 2，顺序 xx、yy、zz、xy、yz、xz |

参数通过原有爆破设置和逐材料卡传到核心，可保存到材料库、气体/炸药库及模型。界面只显示当前模型使用的额外参数。线弹性使用材料库的 E、ν、ρ，无需额外塑性参数。Mohr–Coulomb 的逐材料参数完整校验后才允许运行，示例测试参数不写入用户材料库。

## 当前接入范围

JH2 支持小变形/有限变形的平面应力和平面应变，平面应力约束由外层运动学调用原始3D材料核求解，详见 [JH2接口](ROCK_CONSTITUTIVE.md)。Mohr–Coulomb 支持小变形平面应变，包括拉伸截断和可选线性应变软化。它输出塑性偏应变，不输出 JH2 式损伤：损伤值保留 0，不以塑性应变伪造裂隙损伤。因此其裂隙储气反馈不激活，塑性功诊断目前不提供。软化由材料卡的软化开关控制。线弹性不产生塑性或损伤。

两种新增 EOS 当前要求轴向两端封堵；径向流动和孔壁功耦合可用。强稀疏波仍沿用现有局部等熵指数近似。JWL 参考密度保持初始密度。温度、熵未作为输出，EOS 构造器热容占位值不用于这些热学输出。

## 复核

Release x64 主程序和 EOS DLL 已构建。新增 EOS 的 32 组状态核对压力、声速、内能反算与 SI/CGS 缩放，并检查余容积奇点、非正温度和压力截断。新增固体的 400 步多轴加载核对原始材料类应力、工程剪切与软化历史；另有四组新增固体/气体/产物的联合爆破算例检查气体能量平衡。现有 JH2、JWL 和理想气体对照也保留。

以下专项检查实际执行结果为 41 项通过、0 项失败；浏览器回归通过，覆盖下拉名称、参数显隐、材料卡保存、单位转换与场景重新载入，无页面异常。浏览器验证拦截了材料库写入，没有把测试参数保存到用户材料库。

```powershell
node --test --test-concurrency=1 tests/new-constitutive.test.js tests/eos-upstream.test.js tests/jh2-upstream.test.js tests/upstream-constitutive-data.test.js tests/constitutive-coupling.test.js tests/blast-compatibility.test.js tests/explosive-library.test.js tests/blast-library-page.test.js tests/i18n.test.js
node tests/new-constitutive-ui.cjs
```

源码下载清单见各组件 manifest.json；重新获取命令为 `node scripts/download-constitutive-sources.cjs`。材料试验和工程参数标定仍需独立完成，这些数值检查不代表特定岩石或爆破试验的实验验证。
