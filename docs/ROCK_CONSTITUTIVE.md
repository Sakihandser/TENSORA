# 爆破 JH2 接口

直接调用 OpenRadioss LAW79 原始 Fortran SIGEPS79，固定提交 bad6688602d770e019b75773d2d5a48b4f9bd918。源码、哈希、AGPL许可和接口见 [运行依赖](../third_party/openradioss-jh2/README.md)。缺失或版本不符时停止，无本地材料更新回退。接入材料核不等于接入完整 OpenRadioss 动力学求解器。

本页介绍 ID=3 的 JH2。其他可选固体为线弹性（ID=1）、Mohr–Coulomb（ID=6），见 [本构模型](CONSTITUTIVE_MODELS.md)。内部统一SI：kg/m³、Pa、m、s。界面GPa、MPa、mm、ms转换一次。

可选直接剪切模量G和输入体积模量K以 ELAS1 G K 后缀传输，前18项JH2数值位置不变。G>0直接进入上游，避免从通用快照六位小数的E/ν反算；G=0才用E/ν。K仅记录论文输入，不替换实际EOS的K1；K=0时诊断值由E/ν导出。预平衡与初始波速使用实际K1和G。

归一化等效应力σHEL>0直接使用；为0才按纵向HEL换算1.5(HEL−pHEL)。论文模型保留表中σHEL=4.5 GPa。青砂岩同时保留K=12.67 GPa、K1=25.7 GPa，不通过调参合并两者。

β为膨胀能量比例，论文表未列出，现有模型保留0。仅接入局部模式INLOC=0，参考长度须为0；未接入非局部场、单元删除或碎块接触。Gf不参与JH2。

桥接负责张量、工程剪切、密度和历史变量映射，上游执行应力、损伤与膨胀压力更新。静力预平衡用线性切线作预条件器，动态材料响应来自JH2；预载超过初始强度时拒绝。JH2 在小变形和有限变形下均支持平面应力及平面应变。平面应力由外层运动学适配器逐子步调整面外应变，反复传入上游材料核，直至其返回 σzz≈0；不将返回应力强行置零。

结果要求solidConstitutiveVersion=2、supportedSolidLaws=[3]、jh2IntegrationVersion=4、jh2ParameterVersion=2以及后端提交和ABI。jh2ElasticResponse分别记录输入K、实际K1、G和初始纵波速度。

2026-11-01 已重新编译，执行360步上游材料对照及气体—产物—岩石联合小算例，见 [上游调用验证](CONSTITUTIVE_UPSTREAM.md)。这些检查不能据此认定均质板、W45、W90已复现论文损伤。

## JH2 平面应力（2026-11-03）

在爆破设置中选择“二维假设 → 平面应力（薄板）”，运动学可选择“小变形”或“有限变形与旋转”。有限变形平面应力目前限于 JH2；Mohr–Coulomb 仍限于小变形平面应变。

每次试算从同一份完整历史状态开始，上游原始 SIGEPS79 负责应力、塑性、损伤、膨胀压力和声速。约束迭代只调整传入的面外应变增量，收敛后才接受历史状态；Newton 回溯失败时尝试有界括区与二分，仍不收敛则报错。应变子步的每个接受状态均满足 `|σzz| ≤ 1e−8 max(1 MPa, ||σ||)`，其过程没有本地 JH2 返回映射或损伤公式。下载的 Fortran、CB-Geo 与 Singularity-EOS 源码及 ABI 桥接文件未修改。

有限变形采用当前既有的增量共转对数应变框架。面外厚度伸长 `λz=exp(εzz)`，三维体积比 `J=det(Fxy) λz`；密度、内力积分体积和 CFL 使用此三维体积比，面内形函数梯度与长度仍由面内变形决定。围压及规定孔壁压力按相邻单元当前厚度施加。这是膜内二维运动学，不包含面外弯曲、横向惯性或壳接触。

气固耦合继续调用既有径向气体求解器。有限变形平面应力下，以每个显式时间区间冻结的壁面厚度，积分厚度加权的径向扫掠体积，使径向孔壁功与流体容积变化使用同一力/体积映射；裂隙储气几何变化单独计入 storage work。轴向端部泄流仍按用户指定的有效孔长建模，不将非均匀壁厚变化解释为三维气体流动。

结果元数据新增 `planeMode` 和 `jh2PlaneStressVersion=1`。既有应力输出保留上游实际 σzz。专项测试 `tests/jh2-plane-stress.test.js` 包含两种运动学下960步接受路径与原始 Fortran 的应力/历史对照、压力脉冲、围压预平衡与气固界面能量检查。原有360步三维材料核对照仍保留。

运动学参考：[COMSOL Plane Stress 理论文档](https://doc.comsol.com/6.3/doc/com.comsol.help.sme/sme_ug_theory.06.019.html)；材料模型参考：[Altair LAW79 / JH2](https://www.2024.help.altair.com/2024/hwsolvers/rad/topics/solvers/rad/mat_law79_john_holm_starter_r.htm)。这些数值检查不替代材料标定或试验验证。
