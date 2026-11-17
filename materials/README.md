# 材料库文件夹

`materials.json` 是二维有限元程序的材料库主文件，保存材料颜色和常用力学属性。

`materials.js` 是同一份数据的浏览器备用加载文件，由 `server.js` 自动同步生成。

通过项目根目录的 `start.bat` 或 `node server.js` 打开程序后，界面中的“保存材料”和“删除材料”会直接改写 `materials.json`。

二维爆破的逐材料本构卡保存于 `blastConstitutive`，在“爆破设置”中编辑。可用的线弹性、JH2 和 Mohr–Coulomb 卡及其对应的 OpenCourant 材料卡见 [二维爆破材料](../docs/BLAST_DYNAMICS.md#材料)；其他已移除本构的旧卡片保留在文件中，但不能用于计算。
