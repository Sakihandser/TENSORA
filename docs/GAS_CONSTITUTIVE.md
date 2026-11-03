# 爆破产物和间隙气体本构

产物可选 JWL（ID=1）、理想气体（ID=0）、Noble–Abel（ID=3）和 Stiffened Gas（ID=4）；间隙气体可选后三种气体模型。2026-11-01 新增两种气体模型的参数和求解接口，使用下载的 LANL Singularity-EOS 原始类。新增模型的参数与接入范围见 [本构模型](CONSTITUTIVE_MODELS.md)。等效CJ、NASG、van der Waals 仍不可选。

固定提交、逐文件SHA-256、接口和许可见 [运行依赖](../third_party/singularity-eos-runtime/README.md)。压力和体积模量由上游rho-e接口计算，声速平方=体积模量/当前密度；空气初始比内能由上游rho-p接口反算，无本地EOS回退。

内部rho/rho0为kg/m³，A/B/p/体积模量为Pa，e为J/kg。界面A/B为GPa，e为MJ/kg，空气压力为MPa；R1、R2、ω无量纲。rho0固定为初始装药密度。

论文PETN：rho0=1320，A=586e9，B=21.60e9，R1=5.81，R2=1.77，ω=0.282。E0=7.38e6 kJ/m³先换成7.38e9 J/m³，再除以1320得e0=5590909.090909091 J/kg。爆速6690 m/s及CJ压力16 GPa为资料值，不是JWL初始压力或反应前沿输入。

论文空气多项式c4=c5=0.4、其余为0，与gamma=1.4的压力闭合一致；E0=250 kJ/m³对应p0=100000 Pa。论文该页未明确给出空气密度；补充图片明确给出1.25 kg/m³，模型采用该补充数值。

上游构造器Cv=1仅为占位，所调用方法不依赖Cv；没有温度或熵输出。论文式(2.52)版面重复空气多项式，与JWL文字及表不一致；采用上游标准JWL及表中参数，保留文献疑点。

径向有限体积、界面和轴向泄流仍是应用动力学代码。JWL泄流采用局部等熵指数近似。现有50 mm有效孔长、双端敞开为保留的模型假设；均质数值模型采用2 mm切片，非均质章节写按实体几何1:1建模。均未明确支持现有轴向泄流近似，不能称为完全一致。

结果要求gasConstitutiveVersion=2、gasBackend、固定gasBackendCommit与gasBackendABI=1；前端拒绝旧核心。2026-11-01 已重新编译并执行本构与联合小算例，范围和复核命令见 [上游调用验证](CONSTITUTIVE_UPSTREAM.md)。
