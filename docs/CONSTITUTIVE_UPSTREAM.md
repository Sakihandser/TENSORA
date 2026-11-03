# 爆破本构直接调用与复核

本页保留首次接入的历史核查记录；当前模型列表、后续新增和验证范围以 [爆破本构模型](CONSTITUTIVE_MODELS.md) 为准。

2026-11-01 在 main 工作区已有的直接调用实现上复核并补齐验证。保留现有工作区改动，没有重新实现本构积分公式。

## 选用的 GitHub 实现

| 介质 | 模型和原始实现 | 调用入口 | 固定提交 |
| --- | --- | --- | --- |
| 间隙气体 | [LANL Singularity-EOS IdealGas](https://github.com/lanl/singularity-eos) | PressureFromDensityInternalEnergy、BulkModulusFromDensityInternalEnergy、InternalEnergyFromDensityPressure | b4f71a7748770dfa6ce4d678754c463c09262fb7 |
| 爆轰产物 | 同库 JWL；也可显式选择 IdealGas | 同上，JWL 的参考密度保持初始装药密度 | 同上 |
| 岩石 | [OpenRadioss LAW79 / JH2](https://github.com/gabrielrussell/OpenRadioss/tree/bad6688602d770e019b75773d2d5a48b4f9bd918) | 原始 Fortran SIGEPS79 | bad6688602d770e019b75773d2d5a48b4f9bd918 |

OpenRadioss 来源是已归档镜像的固定提交，不宣称为最新发布版本。只构建所需材料核，不下载和替换整个动力学程序。原始源码分别保存在 third_party/singularity-eos-runtime/upstream 和 third_party/openradioss-jh2/upstream；桥接层负责 ABI、参数和历史变量传递。DLL 缺失或版本错误时停止计算。

## 参数与单位边界

| 量 | 界面输入单位 | 核心及本构库输入单位/规则 |
| --- | --- | --- |
| 密度、JWL 参考密度 | kg/m³ | kg/m³，当前密度与参考密度分别传递 |
| JWL A、B | GPa | Pa，乘 10⁹ |
| 产物比内能 e | MJ/kg | J/kg，乘 10⁶；资料若给体积能量 E0，先换成 J/m³，再除初始密度 |
| 空气压力 | MPa | Pa，乘 10⁶；初始比内能通过上游反算 |
| JWL R1、R2、ω，气体 γ | 无量纲 | 原值；IdealGas 构造器接收 γ−1 |
| HEL、pHEL、σHEL、K1/K2/K3、G | GPa | Pa，乘 10⁹ |
| JH2 静水拉伸强度 T | MPa | Pa；上游 TSTAR 传 T/pHEL |
| 应变、损伤 | 无量纲 | 三维张量剪切转工程剪切后传入；G2=2G |
| 应变率 | s⁻¹ | 等效偏应变率，参考应变率同为 s⁻¹ |
| 时间、长度 | 按界面标签 ms、mm 或 m | s、m，仅在界面转换一次 |

上游 EOS 返回体积模量，声速平方用该模量除以当前密度。Cv=1 仅为构造器占位；当前调用不输出温度或熵，这些功能需要真实热容。JH2 的归一化等效应力与纵向 HEL 区分，已有显式 σHEL 优先；输入 K 仅作记录，EOS 实际使用 K1/K2/K3。JH2 历史 damage、塑性应变、膨胀压力、上一步屈服应力及 ET 在调用间保存。

## 下载与构建

在项目根目录执行（Windows、Node.js、系统 curl.exe）：

```powershell
node scripts/download-constitutive-sources.cjs
node scripts/verify-upstream-sources.cjs third_party/singularity-eos-runtime/manifest.json
node scripts/verify-upstream-sources.cjs third_party/openradioss-jh2/manifest.json
& 'C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe' TensoraCore/TensoraCore.vcxproj /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo
```

下载器按固定提交下载 30 个原始文件，逐文件核对 SHA-256，遇到本地被修改的源码会报错保留。下载记录位于 output/constitutive-source-download.json。Fortran 工具链和 DLL 发布位置见各组件 README。发布时保留 LANL BSD、Ports-of-call 和 OpenRadioss AGPL 及所链接运行库的许可；组件许可不会被项目 MIT 许可覆盖。

## 本次实际验证

```powershell
node --test --test-concurrency=1 tests/eos-upstream.test.js tests/jh2-upstream.test.js tests/upstream-constitutive-data.test.js tests/constitutive-coupling.test.js
```

Release x64 主程序及两个 DLL 已构建；以上 15 项检查全部通过：EOS 的 100 组状态与直接实例化上游头文件的结果一致，检查压力、声速平方、比内能反算以及 SI/CGS 换算；14 组 NaN/Infinity 参数被桥接层拒绝。JH2 的 360 步多轴路径与绕开桥接的原始 Fortran 调用一致。两种产物 EOS 均完成与空气、JH2 的联合小算例，检查结果有限性和气体能量平衡。另检查了界面参数转换、材料卡序列化和依赖缺失时显式报错。

这些检查验证本构调用和耦合通路，不能代替岩石参数标定及实验验证。局部 JH2 损伤、连续 TRI3 网格、径向气体输运和轴向泄流仍有原有模型限制；本次没有接入非局部损伤、碎块接触、反应化学或完整 OpenRadioss 动力学求解器。
