# 爆破固体本构

爆破模块支持线弹性（ID=1）、JH2（ID=3）、Mohr–Coulomb（ID=6）。2026-11-01 新增 CB-Geo 的线弹性与 Mohr–Coulomb 材料类，参数、接入范围与验证见 [本构模型](CONSTITUTIVE_MODELS.md)。基础静力线弹性保持原流程。

原本地裂带、DP、J2、Johnson–Cook、Maxwell、Neo-Hookean、Cam-Clay、DP-Cap、Perzyna、正交弹性、Mooney–Rivlin 和 HJC 不在爆破运行路径中。旧 ID 不自动转换，须显式选择可用本构并填写参数。

见 [岩石本构](ROCK_CONSTITUTIVE.md) 与 [上游代码及许可](../third_party/openradioss-jh2/README.md)。
