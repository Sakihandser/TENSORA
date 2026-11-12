/*
  自动生成的材料库镜像文件。
  数据来源是 materials/materials.json；server.js 每次保存材料库时会重写本文件。
  前端在无法访问 /api/materials 时，通过这个全局变量读取项目内置材料。
*/
window.PROJECT_MATERIAL_LIBRARY = {
  "version": 1,
  "updatedAt": "2026-11-12T10:16:46.337Z",
  "materials": [
    {
      "id": "mat-q235-steel",
      "name": "Q235钢",
      "elasticModulus": 200,
      "poissonRatio": 0.26,
      "density": 7850,
      "yieldStrength": 235,
      "tensileStrength": 370,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": {
        "law": -1,
        "jh2": {
          "G": 0,
          "K": 0
        }
      },
      "deformationMaterialId": "def-q235",
      "blastMaterialId": "blast-q235-steel-elastic",
      "color": "#475569",
      "sourceUrl": "https://www.theworldmaterial.com/q235-steel/",
      "sourceUrls": [
        "https://www.theworldmaterial.com/q235-steel/"
      ],
      "notes": "普通碳素结构钢。泊松比取0.24-0.28范围中值；抗拉强度按370-500 MPa取下限，适合做初步有限元材料卡。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-11-03T07:28:55.264Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-astm-a36-steel",
      "name": "A36钢",
      "elasticModulus": 200,
      "poissonRatio": 0.26,
      "density": 7850,
      "yieldStrength": 250,
      "tensileStrength": 400,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-a36",
      "blastMaterialId": "blast-astm-a36-steel-elastic",
      "color": "#596579",
      "sourceUrl": "https://www.theworldmaterial.com/astm-a36-steel/",
      "sourceUrls": [
        "https://www.theworldmaterial.com/astm-a36-steel/"
      ],
      "notes": "常用热轧低碳结构钢。抗拉强度按400-550 MPa取下限。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-aisi-1045-steel",
      "name": "45钢",
      "elasticModulus": 200,
      "poissonRatio": 0.29,
      "density": 7870,
      "yieldStrength": 310,
      "tensileStrength": 565,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-1045",
      "blastMaterialId": "blast-aisi-1045-steel-elastic",
      "color": "#334155",
      "sourceUrl": "https://www.azom.com/article.aspx?ArticleID=6130",
      "sourceUrls": [
        "https://www.azom.com/article.aspx?ArticleID=6130"
      ],
      "notes": "中碳钢，性能随热处理明显变化；这里采用AZoM表中的典型/基础值。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-aisi-304-stainless",
      "name": "304不锈钢",
      "elasticModulus": 193,
      "poissonRatio": 0.305,
      "density": 8000,
      "yieldStrength": 205,
      "tensileStrength": 515,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": {
        "law": -1,
        "jh2": {
          "G": 0,
          "K": 0
        }
      },
      "deformationMaterialId": "def-304",
      "blastMaterialId": "blast-aisi-304-stainless-elastic",
      "color": "#94a3b8",
      "sourceUrl": "https://www.azom.com/article.aspx?ArticleID=965",
      "sourceUrls": [
        "https://www.azom.com/article.aspx?ArticleID=965",
        "https://www.engineeringtoolbox.com/poissons-ratio-d_1224.html"
      ],
      "notes": "奥氏体不锈钢。弹性模量、密度和强度来自304典型表；泊松比参考18-8不锈钢典型值。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-11-03T07:14:55.998Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-al-6061-t6",
      "name": "6061-T6铝合金",
      "elasticModulus": 68.9,
      "poissonRatio": 0.33,
      "density": 2700,
      "yieldStrength": 276,
      "tensileStrength": 310,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": {
        "law": -1,
        "jh2": {
          "G": 0,
          "K": 0
        }
      },
      "deformationMaterialId": "def-6061-t6",
      "blastMaterialId": "blast-al-6061-t6-elastic",
      "color": "#8ecae6",
      "sourceUrl": "https://www.azom.com/article.aspx?ArticleID=6636",
      "sourceUrls": [
        "https://www.azom.com/article.aspx?ArticleID=6636"
      ],
      "notes": "常用可热处理铝合金，颜色使用浅蓝灰以区别钢材。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-11-03T07:14:55.998Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-c30-concrete",
      "name": "C30混凝土",
      "elasticModulus": 32.837,
      "poissonRatio": 0.2,
      "density": 2500,
      "yieldStrength": null,
      "tensileStrength": 2.9,
      "compressiveStrength": 30,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-c30",
      "blastMaterialId": "blast-c30-concrete-elastic",
      "color": "#9ca3af",
      "sourceUrl": "https://eurocodeapplied.com/design/en1992/concrete-design-properties",
      "sourceUrls": [
        "https://eurocodeapplied.com/design/en1992/concrete-design-properties"
      ],
      "notes": "按EN 1992 C30/37近似录入：Ecm=32.837 GPa，fck=30 MPa，fctm=2.90 MPa。普通混凝土有限元可按项目规范再调整。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-c40-concrete",
      "name": "C40混凝土",
      "elasticModulus": 35.22,
      "poissonRatio": 0.2,
      "density": 2500,
      "yieldStrength": null,
      "tensileStrength": 3.51,
      "compressiveStrength": 40,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-c40",
      "blastMaterialId": "blast-c40-concrete-elastic",
      "color": "#737b82",
      "sourceUrl": "https://eurocodeapplied.com/design/en1992/concrete-design-properties",
      "sourceUrls": [
        "https://eurocodeapplied.com/design/en1992/concrete-design-properties"
      ],
      "notes": "按EN 1992 C40/50近似录入：Ecm=35.220 GPa，fck=40 MPa，fctm=3.51 MPa。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-ht200-gray-cast-iron",
      "name": "HT200灰铸铁",
      "elasticModulus": 100,
      "poissonRatio": 0.26,
      "density": 7150,
      "yieldStrength": null,
      "tensileStrength": 200,
      "compressiveStrength": 720,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-ht200-gray-cast-iron",
      "blastMaterialId": "blast-ht200-gray-cast-iron-elastic",
      "color": "#3f4854",
      "sourceUrl": "https://www.materialhub.de/en/materials/key-to-metals-ht-200-gb",
      "sourceUrls": [
        "https://www.materialhub.de/en/materials/key-to-metals-ht-200-gb",
        "https://www.engineeringtoolbox.com/poissons-ratio-d_1224.html",
        "https://www.codeofchina.com/pdf/16699672844712ff14d35be5110df.pdf"
      ],
      "notes": "灰铸铁没有明显屈服平台，屈服强度留空；弹性模量取HT200 88-113 GPa范围内的工程近似值。 2026-10-29补充：GB/T 9439-2010资料性附录A表A.1（φ30 mm试棒）抗压强度参考值720 MPa、泊松比0.26；抗拉仍取牌号最低值200 MPa。抗压参考值不等于铸件保证值。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-qt450-10-ductile-iron",
      "name": "QT450-10球墨铸铁",
      "elasticModulus": 169,
      "poissonRatio": 0.275,
      "density": 7100,
      "yieldStrength": 310,
      "tensileStrength": 450,
      "compressiveStrength": 700,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-qt450-10-ductile-iron",
      "blastMaterialId": "blast-qt450-10-ductile-iron-elastic",
      "color": "#28313d",
      "sourceUrl": "https://www.caishuku.com/material/detail.php?mid=azhlNWIxMjgzNzU%3D",
      "sourceUrls": [
        "https://www.caishuku.com/material/detail.php?mid=azhlNWIxMjgzNzU%3D",
        "https://www.zhycasting.com/basic-parameters-of-casting-materials-for-tractor-gearbox-housing/"
      ],
      "notes": "铁素体球墨铸铁。数据采用GB/T 1348相关材料表和有限元算例常用MAT1参数。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-c11000-copper",
      "name": "C11000紫铜",
      "elasticModulus": 117,
      "poissonRatio": 0.34,
      "density": 8940,
      "yieldStrength": 69,
      "tensileStrength": 221,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-c11000-copper",
      "blastMaterialId": "blast-c11000-copper-elastic",
      "color": "#b87333",
      "sourceUrl": "https://alloys.copper.org/alloy/C11000",
      "sourceUrls": [
        "https://alloys.copper.org/alloy/C11000",
        "https://www.efunda.com/materials/alloys/copper/show_copper.cfm?ID=UNS_C11000&Page_Title=UNS+C11000&show_prop=all"
      ],
      "notes": "C11000电解韧铜。强度随冷加工状态变化很大，这里采用退火/低强度端参考值。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-c28000-brass",
      "name": "C28000黄铜",
      "elasticModulus": 117,
      "poissonRatio": 0.34,
      "density": 8390,
      "yieldStrength": 140,
      "tensileStrength": 360,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-c28000-brass",
      "blastMaterialId": "blast-c28000-brass-elastic",
      "color": "#c49a35",
      "sourceUrl": "https://www.azom.com/article.aspx?ArticleID=6380",
      "sourceUrls": [
        "https://www.azom.com/article.aspx?ArticleID=6380"
      ],
      "notes": "黄铜使用金黄色材料色，便于与紫铜和钢材区分。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-ti-6al-4v",
      "name": "Ti-6Al-4V钛合金",
      "elasticModulus": 114,
      "poissonRatio": 0.32,
      "density": 4420,
      "yieldStrength": 828,
      "tensileStrength": 897,
      "compressiveStrength": null,
      "strengthCriterion": 4,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-ti-6al-4v",
      "blastMaterialId": "blast-ti-6al-4v-elastic",
      "color": "#7c6f91",
      "sourceUrl": "https://www.azom.com/article.aspx?ArticleID=1547",
      "sourceUrls": [
        "https://www.azom.com/article.aspx?ArticleID=1547",
        "https://www.engineeringtoolbox.com/poissons-ratio-d_1224.html"
      ],
      "notes": "常用Grade 5钛合金。泊松比采用纯钛/钛合金工程典型值。 静力默认使用von Mises屈服校核；未找到同状态单轴抗压破坏数据，抗压强度留空，切换第一/第二理论前须补齐。",
      "createdAt": "2026-09-01T12:55:00.000Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "thesis43-granite",
      "name": "花岗岩（博士论文）",
      "elasticModulus": 51.166,
      "poissonRatio": 0.168,
      "density": 2660,
      "yieldStrength": null,
      "tensileStrength": 54,
      "compressiveStrength": null,
      "strengthCriterion": 1,
      "fractureEnergy": 100,
      "blastConstitutive": {
        "law": 3,
        "jh2": {
          "A": 0.76,
          "N": 0.62,
          "B": 0.25,
          "M": 0.62,
          "C": 0.005,
          "rate0": 1,
          "HEL": 4500000000,
          "pHEL": 3700000000,
          "T": 54000000,
          "D1": 0.005,
          "D2": 0.7,
          "maxStrength": 0.25,
          "K1": 25700000000,
          "K2": -4500000000000,
          "K3": 300000000000000,
          "beta": 0,
          "referenceLength": 0,
          "normalizationStress": 4500000000,
          "G": 21900000000,
          "K": 25700000000
        }
      },
      "deformationMaterialId": "def-thesis43-granite",
      "blastMaterialId": "blast-thesis43-granite-elastic",
      "color": "#92c9ca",
      "sourceUrl": "",
      "sourceUrls": [],
      "notes": "供参考 静力校核待补充同一试样的单轴抗压强度；现有抗拉值与JH2静水拉伸参数相同，来源待核实，不能直接视为实测单轴抗拉强度。保留原数据，勿用通用岩石数值替代。",
      "createdAt": "2026-10-27T10:36:35.306Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "thesis43-sandstone",
      "name": "青砂岩",
      "elasticModulus": 23.714,
      "poissonRatio": 0.188,
      "density": 2340,
      "yieldStrength": null,
      "tensileStrength": 44,
      "compressiveStrength": 0,
      "strengthCriterion": 1,
      "fractureEnergy": 100,
      "blastConstitutive": {
        "law": 3,
        "jh2": {
          "A": 0.76,
          "N": 0.62,
          "B": 0.25,
          "M": 0.62,
          "C": 0.005,
          "rate0": 1,
          "HEL": 4500000000,
          "pHEL": 3700000000,
          "T": 44000000,
          "D1": 0.005,
          "D2": 0.7,
          "maxStrength": 0.25,
          "K1": 25700000000,
          "K2": -4500000000000,
          "K3": 300000000000000,
          "beta": 0,
          "referenceLength": 0,
          "normalizationStress": 4500000000,
          "G": 9980000000,
          "K": 12670000000
        }
      },
      "deformationMaterialId": "def-thesis43-sandstone",
      "blastMaterialId": "blast-thesis43-sandstone-elastic",
      "color": "#dfeacb",
      "sourceUrl": "",
      "sourceUrls": [],
      "notes": "供参考 静力校核待补充同一试样的单轴抗压强度；现有抗拉值与JH2静水拉伸参数相同，来源待核实，不能直接视为实测单轴抗拉强度。保留原数据，勿用通用岩石数值替代。",
      "createdAt": "2026-10-27T10:36:35.306Z",
      "updatedAt": "2026-11-12T08:26:45.096Z"
    },
    {
      "id": "mat-blanco-mera",
      "name": "花岗岩（Pérez-Rey 2024）",
      "elasticModulus": 52.4,
      "poissonRatio": 0.28,
      "density": 2590,
      "yieldStrength": null,
      "tensileStrength": 5.64,
      "compressiveStrength": 110,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-blanco-mera",
      "blastMaterialId": "blast-blanco-mera-elastic",
      "color": "#82786f",
      "sourceUrl": "https://link.springer.com/article/10.1007/s00603-023-03751-z",
      "sourceUrls": [
        "https://link.springer.com/article/10.1007/s00603-023-03751-z",
        "https://doi.org/10.1016/j.jrmge.2022.11.005",
        "https://arxiv.org/html/2403.18369"
      ],
      "notes": "论文 §2.1 与 §4.1。E、ν 和抗压强度采用文中汇总的压缩试验值，抗拉强度采用四实验室直接拉伸的合并均值。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-cotta-parallel",
      "name": "砂岩",
      "elasticModulus": 10.8,
      "poissonRatio": 0.18,
      "density": 2060,
      "yieldStrength": null,
      "tensileStrength": 1.7,
      "compressiveStrength": 26.2,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-cotta-parallel",
      "blastMaterialId": "blast-cotta-parallel-elastic",
      "color": "#ba8b60",
      "sourceUrl": "https://link.springer.com/article/10.1007/s00603-023-03751-z",
      "sourceUrls": [
        "https://link.springer.com/article/10.1007/s00603-023-03751-z"
      ],
      "notes": "论文 §2.1 与 §4.1。压缩和直接拉伸的加载轴均平行层理。E、ν 采用压缩试验值，当前各向同性输入仅近似该取向。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-marble-wang2023",
      "name": "大理岩",
      "elasticModulus": 68.3,
      "poissonRatio": 0.17,
      "density": 2700,
      "yieldStrength": null,
      "tensileStrength": 5.67,
      "compressiveStrength": 55.8,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-marble-wang2023",
      "blastMaterialId": "blast-marble-wang2023-elastic",
      "color": "#a3a2ab",
      "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1",
      "sourceUrls": [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1"
      ],
      "notes": "Wang 等（2023）表 1 的静态试样均值。密度取干态值，E 与 ν 取单轴压缩试验，抗拉强度取巴西劈裂试验。 2026-11-12 修订：原表 1 弹性模量 121 GPa 与同表纵波速度不自洽（ρVp² = 73.4 GPa 为约束模量上限，E 应小于该值），改用 E = ρVp²(1+ν)(1−2ν)/(1−ν) = 68.3 GPa（干密度 2.7 g/cm³、Vp = 5214 m/s、ν = 0.17，均取表 1，https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1）。该值为波速换算的动态模量，通常略高于静态模量。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "mat-limestone-wang2023",
      "name": "石灰岩",
      "elasticModulus": 56.3,
      "poissonRatio": 0.2,
      "density": 2760,
      "yieldStrength": null,
      "tensileStrength": 5.06,
      "compressiveStrength": 28.5,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-limestone-wang2023",
      "blastMaterialId": "blast-limestone-wang2023-elastic",
      "color": "#898e78",
      "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1",
      "sourceUrls": [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1"
      ],
      "notes": "Wang 等（2023）表 1 的静态试样均值。密度取干态值，E 与 ν 取单轴压缩试验，抗拉强度取巴西劈裂试验。 2026-11-12 修订：原表 1 弹性模量 116 GPa 与同表纵波速度不自洽（ρVp² = 62.5 GPa 为约束模量上限，E 应小于该值），改用 E = ρVp²(1+ν)(1−2ν)/(1−ν) = 56.3 GPa（干密度 2.76 g/cm³、Vp = 4759 m/s、ν = 0.2，均取表 1，https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1）。该值为波速换算的动态模量，通常略高于静态模量。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "mat-reef-limestone-wang2023",
      "name": "珊瑚礁灰岩",
      "elasticModulus": 5.93,
      "poissonRatio": 0.25,
      "density": 980,
      "yieldStrength": null,
      "tensileStrength": 1.42,
      "compressiveStrength": 15,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-reef-limestone-wang2023",
      "blastMaterialId": "blast-reef-limestone-wang2023-elastic",
      "color": "#b8a682",
      "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1",
      "sourceUrls": [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1"
      ],
      "notes": "Wang 等（2023）表 1 的静态试样均值。密度取干态值，E 与 ν 取单轴压缩试验，抗拉强度取巴西劈裂试验。 2026-11-12 修订：原表 1 弹性模量 9.7 GPa 与同表纵波速度不自洽（ρVp² = 7.11 GPa 为约束模量上限，E 应小于该值），改用 E = ρVp²(1+ν)(1−2ν)/(1−ν) = 5.93 GPa（干密度 0.98 g/cm³、Vp = 2694 m/s、ν = 0.25，均取表 1，https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1）。该值为波速换算的动态模量，通常略高于静态模量。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "mat-gypsum-wang2023",
      "name": "石膏",
      "elasticModulus": 9.44,
      "poissonRatio": 0.3,
      "density": 1140,
      "yieldStrength": null,
      "tensileStrength": 1.11,
      "compressiveStrength": 3.1,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-gypsum-wang2023",
      "blastMaterialId": "blast-gypsum-wang2023-elastic",
      "color": "#a9a0a0",
      "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1",
      "sourceUrls": [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1"
      ],
      "notes": "Wang 等（2023）表 1 的静态试样均值。密度取干态值，E 与 ν 取单轴压缩试验，抗拉强度取巴西劈裂试验。 2026-11-12 修订：原表 1 弹性模量 13 GPa 与同表纵波速度不自洽（ρVp² = 12.7 GPa 为约束模量上限，E 应小于该值），改用 E = ρVp²(1+ν)(1−2ν)/(1−ν) = 9.44 GPa（干密度 1.14 g/cm³、Vp = 3338 m/s、ν = 0.3，均取表 1，https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1）。该值为波速换算的动态模量，通常略高于静态模量。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "mat-dmc-printed-gypsum",
      "name": "打印石膏",
      "elasticModulus": 0.6,
      "poissonRatio": 0.2,
      "density": 1290,
      "yieldStrength": null,
      "tensileStrength": null,
      "compressiveStrength": null,
      "strengthCriterion": 1,
      "fractureEnergy": 130,
      "blastConstitutive": null,
      "deformationMaterialId": "def-dmc-printed-gypsum",
      "blastMaterialId": "blast-dmc-printed-gypsum-elastic",
      "color": "#d0c5a9",
      "sourceUrl": "https://arxiv.org/html/2403.18369",
      "sourceUrls": [
        "https://arxiv.org/html/2403.18369",
        "https://www.mdpi.com/2076-3417/14/1/344"
      ],
      "notes": "Navidtehrani 等（2024）§2.2.3 图 5(d)。E、Gc 与 ℓ 来自 HC 三点弯曲算例的拟合，ν 为论文假设值。单轴强度留空。 密度采用同类材料参考值 1290 kg/m³，来源为表 2 的未烧结 3D 打印石膏圆柱干密度（https://www.mdpi.com/2076-3417/14/1/344）。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-notched-concrete-beam",
      "name": "混凝土",
      "elasticModulus": 35,
      "poissonRatio": 0.2,
      "density": 2400,
      "yieldStrength": null,
      "tensileStrength": null,
      "compressiveStrength": null,
      "strengthCriterion": 1,
      "fractureEnergy": 100,
      "blastConstitutive": null,
      "deformationMaterialId": "def-notched-concrete-beam",
      "blastMaterialId": "blast-notched-concrete-beam-elastic",
      "color": "#7c8c95",
      "sourceUrl": "https://www.mdpi.com/1996-1944/14/8/1913",
      "sourceUrls": [
        "https://www.mdpi.com/1996-1944/14/8/1913",
        "https://www.skb.com/publication/2493324/R-19-12.pdf"
      ],
      "notes": "Navidtehrani 等（2021）§4.2。Gc=0.1 N/mm，ℓ=2 mm。论文使用平面应变与 Miehe 谱分解。单轴强度留空。 密度采用同类材料参考值 2400 kg/m³，来源为表 6-4 的普通混凝土建模密度（https://www.skb.com/publication/2493324/R-19-12.pdf）。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-eccentric-hole-mortar",
      "name": "水泥砂浆",
      "elasticModulus": 5.982,
      "poissonRatio": 0.22,
      "density": 2140,
      "yieldStrength": null,
      "tensileStrength": null,
      "compressiveStrength": null,
      "strengthCriterion": 1,
      "fractureEnergy": 2280,
      "blastConstitutive": null,
      "deformationMaterialId": "def-eccentric-hole-mortar",
      "blastMaterialId": "blast-eccentric-hole-mortar-elastic",
      "color": "#a39482",
      "sourceUrl": "https://www.mdpi.com/1996-1944/14/8/1913",
      "sourceUrls": [
        "https://www.mdpi.com/1996-1944/14/8/1913",
        "https://doi.org/10.2298/SOS2104445T"
      ],
      "notes": "Navidtehrani 等（2021）§4.3。E=5982 MPa，Gc=2.28 N/mm，ℓ=0.25 mm。原算例采用平面应力及完整弹性能。单轴强度留空。 密度采用同类材料参考值 2140 kg/m³，来源为Terzić 等表 V 的硬化普通水泥砂浆 CM 实测密度（https://doi.org/10.2298/SOS2104445T）。",
      "createdAt": "2026-11-12T08:03:43.272Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "mat-skb-bhk-backfill",
      "name": "回填混凝土",
      "elasticModulus": 42.6,
      "poissonRatio": 0.22,
      "density": 2400,
      "yieldStrength": null,
      "tensileStrength": null,
      "compressiveStrength": null,
      "strengthCriterion": 1,
      "fractureEnergy": null,
      "blastConstitutive": null,
      "deformationMaterialId": "def-skb-bhk-backfill",
      "blastMaterialId": "blast-skb-bhk-backfill-elastic",
      "color": "#868e89",
      "sourceUrl": "https://www.skb.com/publication/2493324/R-19-12.pdf",
      "sourceUrls": [
        "https://www.skb.com/publication/2493324/R-19-12.pdf",
        "https://code-aster.org/doc/v17/manuals/man_u/u4/u4.43.01/Caract_ristiques_sp_cifiques_aux_b_tons.html"
      ],
      "notes": "SKB R-19-12 表 6-4 的 BHK 回填混凝土参数。密度与弹性常数为该算例采用值。",
      "createdAt": "2026-11-12T08:26:45.096Z",
      "updatedAt": "2026-11-12T10:08:33.552Z"
    }
  ],
  "deformationMaterials": [
    {
      "id": "def-q235",
      "name": "Q235钢-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 235000000,
        "hardening": 1430000000,
        "criticalPlasticStrain": 0.1,
        "fractureEnergy": 2700,
        "fractureLength": 0.1
      },
      "sourceUrl": "https://html.rhhz.net/jmsa/html/20240217.htm",
      "notes": "Su 等（2024）§3.2，Q235B 室温准静态拉伸拟合 B=537.4 MPa、n=0.575。按 εp=0.10 取增量割线 H=B·εp^(n−1)，初始屈服保留基础库名义值 235 MPa。PEEQ 阈值 0.10 为参考区间终点。"
    },
    {
      "id": "def-a36",
      "name": "A36钢-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 250000000,
        "hardening": 1970000000,
        "criticalPlasticStrain": 0.093,
        "fractureEnergy": 2700,
        "fractureLength": 0.1
      },
      "sourceUrl": "https://www.mdpi.com/2075-4701/15/4/458",
      "notes": "Harwell 等（2025）图 10、表 3，821449-C1 光滑圆棒。取工程应变 0.10 处约 7210 lbf，经真应力及塑性应变转换后，以试样屈服点取增量割线。初始屈服使用基础库名义值 250 MPa。PEEQ 阈值取割线终点。"
    },
    {
      "id": "def-1045",
      "name": "45钢-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 310000000,
        "hardening": 7040000000,
        "criticalPlasticStrain": 0.056,
        "fractureEnergy": 2700,
        "fractureLength": 0.1
      },
      "sourceUrl": "https://doi.org/10.3390/ma12040609",
      "notes": "Murugesan 与 Jung（2019）图 9(a)，室温圆棒。真应变 0.02、0.06 处真应力约 560、832 MPa，扣除弹性应变后计算平均硬化斜率。初始屈服使用基础库名义值 310 MPa。PEEQ 阈值取参考区间终点。热处理和供货状态需核对。"
    },
    {
      "id": "def-304",
      "name": "304不锈钢-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 205000000,
        "hardening": 2200000000,
        "criticalPlasticStrain": 0.092,
        "fractureEnergy": 2700,
        "fractureLength": 0.1
      },
      "sourceUrl": "https://www.mdpi.com/2075-4701/15/4/458",
      "notes": "Harwell 等（2025）图 10、表 3，821449-S1 光滑圆棒。取工程应变 0.10 处约 9500 lbf，经真应力及塑性应变转换后，以试样屈服点取增量割线。试样屈服显著高于基础库名义值 205 MPa，本卡采用后者，斜率仅作参考。PEEQ 阈值取割线终点。"
    },
    {
      "id": "def-6061-t6",
      "name": "6061-T6铝合金-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 276000000,
        "hardening": 910000000,
        "criticalPlasticStrain": 0.044,
        "fractureEnergy": 2700,
        "fractureLength": 0.1
      },
      "sourceUrl": "https://www.mdpi.com/2075-4701/15/4/458",
      "notes": "Harwell 等（2025）图 10、表 3，821449-A1 光滑圆棒。取工程应变 0.05 处约 4620 lbf，经真应力及塑性应变转换后，以试样屈服点取增量割线。初始屈服使用基础库名义值 276 MPa。PEEQ 阈值取割线终点。"
    },
    {
      "id": "def-c30",
      "name": "C30混凝土-Mazars",
      "card": {
        "model": "mazars",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 141,
        "fractureLength": 0.06,
        "epsd0": 0.0000883,
        "ac": 1.09,
        "at": 0.95,
        "bc": 1032.1,
        "bt": 4200,
        "k": 0.7
      },
      "sourceUrl": "https://www.skb.com/publication/2493324/R-19-12.pdf",
      "notes": "Mazars 混凝土损伤（Code_Aster，三维），替代原 AT2 相场卡（PhAST 仅支持二维平面应变，且不区分拉压）。EPSD0 = ft/E = 2.9 MPa / 32.837 GPa = 0.0000883（基础卡 EN 1992 口径）；AC = 1.09、AT = 0.95、BC = 1032.1、BT = 4200 借用 SKB R-19-12 表 6-4 的混凝土标定（https://www.skb.com/publication/2493324/R-19-12.pdf，原标定对象 fc ≈ 50–60 MPa）；K = 0.7 为 Code_Aster U4.43.01 §8.13.1 推荐值（https://code-aster.org/doc/v17/manuals/man_u/u4/u4.43.01/Caract_ristiques_sp_cifiques_aux_b_tons.html）。仅作参考，未针对 C30混凝土 标定。"
    },
    {
      "id": "def-c40",
      "name": "C40混凝土-Mazars",
      "card": {
        "model": "mazars",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 147,
        "fractureLength": 0.046,
        "epsd0": 0.0000997,
        "ac": 1.09,
        "at": 0.95,
        "bc": 1032.1,
        "bt": 4200,
        "k": 0.7
      },
      "sourceUrl": "https://www.skb.com/publication/2493324/R-19-12.pdf",
      "notes": "Mazars 混凝土损伤（Code_Aster，三维），替代原 AT2 相场卡（PhAST 仅支持二维平面应变，且不区分拉压）。EPSD0 = ft/E = 3.51 MPa / 35.22 GPa = 0.0000997（基础卡 EN 1992 口径）；AC = 1.09、AT = 0.95、BC = 1032.1、BT = 4200 借用 SKB R-19-12 表 6-4 的混凝土标定（https://www.skb.com/publication/2493324/R-19-12.pdf，原标定对象 fc ≈ 50–60 MPa）；K = 0.7 为 Code_Aster U4.43.01 §8.13.1 推荐值（https://code-aster.org/doc/v17/manuals/man_u/u4/u4.43.01/Caract_ristiques_sp_cifiques_aux_b_tons.html）。仅作参考，未针对 C40混凝土 标定。"
    },
    {
      "id": "def-ht200-gray-cast-iron",
      "name": "HT200灰铸铁-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 200000000,
        "crackBandEnergy": 6158.41
      },
      "sourceUrl": "https://doi.org/10.1016/j.jmatprotec.2006.03.082",
      "notes": "基于 HT200 基础卡抗拉下限和同类片状石墨灰铸铁 SE(B) 试验的峰载表观韧度 Kpmax=25.7 MPa·√m（表 1，缺口半径 0.2 mm）。该值随缺口和尺寸变化。 采用基础卡 E 与 ν，以 (1−ν²)K²/E 换算为等效裂带能量初值。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-qt450-10-ductile-iron",
      "name": "QT450-10球墨铸铁-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 310000000,
        "hardening": 0,
        "criticalPlasticStrain": 0.1,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "hardeningCurve": [
          [
            310000000,
            0
          ],
          [
            320757473,
            0.0005
          ],
          [
            325799065,
            0.001
          ],
          [
            333203447,
            0.002
          ],
          [
            348566502,
            0.005
          ],
          [
            366641061,
            0.01
          ],
          [
            393186435,
            0.02
          ],
          [
            432172552,
            0.04
          ],
          [
            462973516,
            0.06
          ],
          [
            489429884,
            0.08
          ],
          [
            513063272,
            0.1
          ]
        ]
      },
      "sourceUrl": "https://dergipark.org.tr/tr/download/article-file/4098398",
      "notes": "J2 多段硬化，替代原理想塑性假设（H = 0）。流动应力 σ = 310 + 728·εp^0.5545 MPa 取相近牌号 EN-GJS-400 球铁 Johnson–Cook 拉伸组的准静态部分（Özcan & Şeker 2024，https://dergipark.org.tr/tr/download/article-file/4098398），按塑性应变离散到 εp = 0.10；初始屈服 310 MPa 与基础卡 Rp0.2 一致。PEEQ 阈值取 GB/T 1348 牌号伸长率 10%。QT450-10 与 GJS-400 牌号不同，仅作参考。"
    },
    {
      "id": "def-c11000-copper",
      "name": "C11000紫铜-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 100000000,
        "hardening": 0,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "hardeningCurve": [
          [
            100000000,
            0
          ],
          [
            107671791,
            0.0005
          ],
          [
            111154573,
            0.001
          ],
          [
            116218443,
            0.002
          ],
          [
            126600926,
            0.005
          ],
          [
            138677015,
            0.01
          ],
          [
            156235317,
            0.02
          ],
          [
            181764606,
            0.04
          ],
          [
            201778168,
            0.06
          ],
          [
            234107465,
            0.1
          ],
          [
            266933013,
            0.15
          ],
          [
            294988568,
            0.2
          ]
        ]
      },
      "sourceUrl": "https://www.mdpi.com/2075-4701/7/12/572",
      "notes": "§2.1 式 (5) 和表 1：退火 C11000 的流动应力为 100+465·εp^0.54 MPa。按塑性应变离散为多段输入。弹性常数和基础静力强度仍取基础卡。PEEQ 显示阈值沿用软件默认值。"
    },
    {
      "id": "def-c28000-brass",
      "name": "C28000黄铜-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 197025000,
        "hardening": 1075757575.7575758,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1
      },
      "sourceUrl": "https://doi.org/10.1557/mrc.2017.28",
      "notes": "论文表 2 线性组 E=106.5 GPa，εy=0.185%，Ep/E=0.01。按 σy=Eεy、H=E·Ep/(E−Ep) 换算。项目弹性采用基础卡。PEEQ 显示阈值沿用软件默认值。"
    },
    {
      "id": "def-ti-6al-4v",
      "name": "Ti-6Al-4V钛合金-J2塑性",
      "card": {
        "model": "plastic",
        "yieldStress": 913216000,
        "hardening": 0,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "hardeningCurve": [
          [
            913216000,
            0
          ],
          [
            916512019,
            0.0004628946
          ],
          [
            928243754,
            0.0023664165
          ],
          [
            940125659,
            0.0047687035
          ],
          [
            949946698,
            0.0071879383
          ],
          [
            965652225,
            0.012058781
          ],
          [
            988229803,
            0.0218731102
          ],
          [
            1017427157,
            0.0416330003
          ],
          [
            1041215267,
            0.0664373744
          ],
          [
            1058429743,
            0.091295808
          ]
        ]
      },
      "sourceUrl": "https://doi.org/10.1557/mrc.2017.28",
      "notes": "论文表 2 与式 (4)：E=121.6 GPa、εy=0.751%、n=0.057。采样幂律后扣除 σ/E 得到真应力–塑性应变表。项目弹性采用基础卡。PEEQ 显示阈值沿用软件默认值。"
    },
    {
      "id": "def-thesis43-granite",
      "name": "花岗岩（博士论文）-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 5280000,
        "crackBandEnergy": 218.09
      },
      "sourceUrl": "https://doi.org/10.1016/j.heliyon.2023.e18486",
      "notes": "表 1 与表 2：用日照花岗岩的抗拉强度及 SCB 断裂功作为同类岩石参考。项目原卡中的静水拉伸参数未用于此准静态卡。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-thesis43-sandstone",
      "name": "青砂岩-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 3280000,
        "crackBandEnergy": 126.35
      },
      "sourceUrl": "https://doi.org/10.1016/j.heliyon.2023.e18486",
      "notes": "表 1 与表 2：用自贡细砂岩的抗拉强度及 SCB 断裂功作为同类岩石参考。项目原卡中的静水拉伸参数未用于此准静态卡。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-blanco-mera",
      "name": "花岗岩（Pérez-Rey 2024）-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 20.896,
        "fractureLength": 0.0039393,
        "tensileStrength": 5640000,
        "crackBandEnergy": 20.896
      },
      "sourceUrl": "https://doi.org/10.1016/j.jrmge.2022.11.005",
      "notes": "三维裂带断裂（OOFEM），替代原 AT2 相场卡（PhAST 仅支持二维），与其余岩石卡一致。抗拉强度 5.64 MPa 取四实验室直接拉伸均值（Pérez-Rey 等 2024，doi:10.1007/s00603-023-03751-z）；裂带断裂能 20.896 J/m² 由同一岩种 pCT 试样平均 KIc = 1.09 MPa·√m（doi:10.1016/j.jrmge.2022.11.005 表 5）与基础卡 E = 52.4 GPa、ν = 0.28 按平面应变 LEFM 换算。适用于 OOFEM 准静态拉伸软化，跨试样参数是初始值。"
    },
    {
      "id": "def-cotta-parallel",
      "name": "砂岩-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 1700000,
        "crackBandEnergy": 126.35
      },
      "sourceUrl": "https://doi.org/10.1016/j.heliyon.2023.e18486",
      "notes": "抗拉强度取 Cotta 平行层理直接拉伸均值（doi:10.1007/s00603-023-03751-z）。断裂能用表 2 自贡细砂岩 SCB 值作参考，未拟合层理方向的断裂能。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-marble-wang2023",
      "name": "大理岩-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 5670000,
        "crackBandEnergy": 188.87
      },
      "sourceUrl": "https://doi.org/10.1016/j.heliyon.2023.e18486",
      "notes": "抗拉强度取 Wang 等表 1 巴西劈裂试验。断裂能取 Cui 等表 2 南阳大理岩 SCB 参考值。 抗拉试验来源：https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-limestone-wang2023",
      "name": "石灰岩-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 5060000,
        "crackBandEnergy": 90.61
      },
      "sourceUrl": "https://www.mdpi.com/1996-1944/16/3/1056",
      "notes": "抗拉强度取 Wang 等表 1 巴西劈裂试验。断裂能取表 4 普通灰岩 C 组 NSCB 均值作为参考。 抗拉试验来源：https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-reef-limestone-wang2023",
      "name": "珊瑚礁灰岩-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 1420000,
        "crackBandEnergy": 102.4
      },
      "sourceUrl": "https://doi.org/10.1080/1064119X.2025.2550661",
      "notes": "抗拉强度取 Wang 等表 1 巴西劈裂试验。断裂韧度取另一组珊瑚礁灰岩表 3 的 25 °C NSCB 均值 0.805 MPa·√m，孔隙与结构差异可能影响结果。 采用基础卡 E 与 ν，以 (1−ν²)K²/E 换算为等效裂带能量初值。 抗拉试验来源：https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-gypsum-wang2023",
      "name": "石膏-裂带",
      "card": {
        "model": "crackBand",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "tensileStrength": 1110000,
        "crackBandEnergy": 33.33
      },
      "sourceUrl": "https://doi.org/10.1016/j.heliyon.2023.e18486",
      "notes": "抗拉强度取 Wang 等表 1 巴西劈裂试验。断裂能取 Cui 等表 2 的石膏 SCB 值作为参考。 抗拉试验来源：https://pmc.ncbi.nlm.nih.gov/articles/PMC10628249/#Tab1。 适用于 OOFEM 准静态拉伸软化。跨试样参数是初始值。"
    },
    {
      "id": "def-dmc-printed-gypsum",
      "name": "打印石膏-AT2相场",
      "card": {
        "model": "phaseField",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 130,
        "fractureLength": 0.0005
      },
      "sourceUrl": "https://arxiv.org/html/2403.18369",
      "notes": "Navidtehrani 等（2024）§2.2.3 图 5(d)。E、Gc 与 ℓ 来自 HC 三点弯曲算例的拟合，ν 为论文假设值。单轴强度留空。 本项目 PhAST 采用小变形平面应变和 Amor 分解，可用该卡对照论文输入。 密度采用同类材料参考值 1290 kg/m³，来源为表 2 的未烧结 3D 打印石膏圆柱干密度（https://www.mdpi.com/2076-3417/14/1/344）。"
    },
    {
      "id": "def-notched-concrete-beam",
      "name": "混凝土-AT2相场",
      "card": {
        "model": "phaseField",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 100,
        "fractureLength": 0.002
      },
      "sourceUrl": "https://www.mdpi.com/1996-1944/14/8/1913",
      "notes": "Navidtehrani 等（2021）§4.2。Gc=0.1 N/mm，ℓ=2 mm。论文使用平面应变与 Miehe 谱分解。单轴强度留空。 本项目 PhAST 采用小变形平面应变和 Amor 分解，可用该卡对照论文输入。 密度采用同类材料参考值 2400 kg/m³，来源为表 6-4 的普通混凝土建模密度（https://www.skb.com/publication/2493324/R-19-12.pdf）。"
    },
    {
      "id": "def-eccentric-hole-mortar",
      "name": "水泥砂浆-AT2相场",
      "card": {
        "model": "phaseField",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2280,
        "fractureLength": 0.00025
      },
      "sourceUrl": "https://www.mdpi.com/1996-1944/14/8/1913",
      "notes": "Navidtehrani 等（2021）§4.3。E=5982 MPa，Gc=2.28 N/mm，ℓ=0.25 mm。原算例采用平面应力及完整弹性能。单轴强度留空。 本项目 PhAST 采用小变形平面应变和 Amor 分解，可用该卡对照论文输入。 密度采用同类材料参考值 2140 kg/m³，来源为Terzić 等表 V 的硬化普通水泥砂浆 CM 实测密度（https://doi.org/10.2298/SOS2104445T）。"
    },
    {
      "id": "def-skb-bhk-backfill",
      "name": "回填混凝土-Mazars",
      "card": {
        "model": "mazars",
        "yieldStress": 250000000,
        "hardening": 1000000000,
        "criticalPlasticStrain": 0.15,
        "fractureEnergy": 2700,
        "fractureLength": 0.1,
        "epsd0": 0.00008,
        "ac": 1.09,
        "at": 0.95,
        "bc": 1032.1,
        "bt": 4200,
        "k": 0.7
      },
      "sourceUrl": "https://www.skb.com/publication/2493324/R-19-12.pdf",
      "notes": "EPSD0、AC、AT、BC、BT 取 SKB R-19-12 表 6-4。原表未列 K，采用 Code_Aster U4.43.01 推荐值 0.70。"
    }
  ],
  "blastMaterials": [
    {
      "id": "blast-q235-steel-elastic",
      "name": "Q235钢-Johnson–Cook",
      "sourceUrl": "https://html.rhhz.net/jmsa/html/20240217.htm",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 282.4 MPa、B = 537.4 MPa、n = 0.575（室温拟合）与 m = 0.757（高温拟合）取 Su 等（2024）Q235B 标定第 3.2 节（https://html.rhhz.net/jmsa/html/20240217.htm，doi:10.1007/s11804-024-00414-5）；该文仅做准静态试验未给 C，C = 0.022、Tm = 1811 K、cp = 452 J/(kg·K) 借用 Johnson & Cook（1983）1006 低碳钢（https://ia800406.us.archive.org/4/items/AConstitutiveModelAndDataForMetals/A%20constitutive%20model%20and%20data%20for%20metals_text.pdf）。εp,max = 26%（GB/T 700）。",
      "card": {
        "model": "jc",
        "a": 282400000,
        "b": 537400000,
        "n": 0.575,
        "C": 0.022,
        "rate0": 1,
        "m": 0.757,
        "tMelt": 1811,
        "tRef": 293,
        "rhoCp": 3548200,
        "epsMax": 0.26,
        "sigMax": 0,
        "tension": 370000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-astm-a36-steel-elastic",
      "name": "A36钢-Johnson–Cook",
      "sourceUrl": "https://www.dynalook.com/conferences/european-conf-2007/optional-strain-rate-forms-for-the-johnson-cook.pdf",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 41.50 ksi（286.1 MPa）、B = 72.54 ksi（500.2 MPa）、n = 0.228、C = 0.017、ε̇0 = 1 s⁻¹、m = 0.917 取 A36 热轧钢（NAVEODTECHDIV 提供，见 6th European LS-DYNA Conference 2007，https://www.dynalook.com/conferences/european-conf-2007/optional-strain-rate-forms-for-the-johnson-cook.pdf）；Tm = 1811 K、cp = 452 J/(kg·K) 借用 Johnson & Cook（1983）1006 低碳钢。εp,max = 20%（ASTM A36）。",
      "card": {
        "model": "jc",
        "a": 286100000,
        "b": 500200000,
        "n": 0.228,
        "C": 0.017,
        "rate0": 1,
        "m": 0.917,
        "tMelt": 1811,
        "tRef": 293,
        "rhoCp": 3548200,
        "epsMax": 0.2,
        "sigMax": 0,
        "tension": 400000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-aisi-1045-steel-elastic",
      "name": "45钢-Johnson–Cook",
      "sourceUrl": "https://www.azom.com/article.aspx?ArticleID=6130",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 553.1 MPa、B = 600.8 MPa、n = 0.234、C = 0.0134、m = 1.0 取 Jaspers & Dautzenberg（2002，J. Mater. Process. Technol. 122:322–330）AISI 1045 常用参数（NIST 1045 切削研究称其为最常用的 1045 JC 参数组）；Tm = 1793 K、cp = 477 J/(kg·K) 借用 Johnson & Cook（1983）4340 钢。A 高于基础卡热轧态屈服 310 MPa，反映原文试样状态。εp,max = 16%。",
      "card": {
        "model": "jc",
        "a": 553100000,
        "b": 600800000,
        "n": 0.234,
        "C": 0.0134,
        "rate0": 1,
        "m": 1,
        "tMelt": 1793,
        "tRef": 293,
        "rhoCp": 3753990,
        "epsMax": 0.16,
        "sigMax": 0,
        "tension": 565000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-aisi-304-stainless-elastic",
      "name": "304不锈钢-Johnson–Cook",
      "sourceUrl": "https://utw10945.utweb.utexas.edu/sites/default/files/2023/041%20JohnsonCookFailureModelforAdditivelyManufactured304LStainlessSteelParts.pdf",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。未检索到可读取的锻造 304 全套参数；A = 516.45 MPa、B = 812.39 MPa、n = 0.7042、C = 0.0117、m = 0.7383、ε̇0 = 0.001 s⁻¹ 借用增材制造 304L（XY 方向，UT Austin，https://utw10945.utweb.utexas.edu/sites/default/files/2023/041%20JohnsonCookFailureModelforAdditivelyManufactured304LStainlessSteelParts.pdf），A 明显高于锻造退火态屈服 205 MPa，仅作参考。Tm = 1673 K（304 熔化区间 1400–1450 °C 下限）、cp = 500 J/(kg·K)。静水拉伸截断取层裂强度 2.1 GPa（https://www.researchgate.net/publication/239293827_Measurement_of_spall_strength_of_A12024-T4_and_SS304_in_plate_impact_experiments）。εp,max = 40%。",
      "card": {
        "model": "jc",
        "a": 516450000.00000006,
        "b": 812390000,
        "n": 0.7042,
        "C": 0.0117,
        "rate0": 0.001,
        "m": 0.7383,
        "tMelt": 1673,
        "tRef": 293,
        "rhoCp": 4000000,
        "epsMax": 0.4,
        "sigMax": 0,
        "tension": 2100000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-al-6061-t6-elastic",
      "name": "6061-T6铝合金-Johnson–Cook",
      "sourceUrl": "https://scholarworks.aub.edu.lb/server/api/core/bitstreams/007508f0-6051-47fb-8cb5-998b8cb41d38/content",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 324 MPa、B = 114 MPa、n = 0.42、C = 0.002、m = 1.34 取 Seif、Hage、Hamade（2019，CIRP J. Manuf. Sci. Technol.）表中 6061-T6 参考参数组（https://scholarworks.aub.edu.lb/server/api/core/bitstreams/007508f0-6051-47fb-8cb5-998b8cb41d38/content）；Tm = 925 K（液相线 652 °C）、cp = 896 J/(kg·K)。静水拉伸截断取层裂强度 1.1 GPa（https://shock.wsu.edu/documents/2025/10/pdv_2023_portillo.pdf）。εp,max = 12%。",
      "card": {
        "model": "jc",
        "a": 324000000,
        "b": 114000000,
        "n": 0.42,
        "C": 0.002,
        "rate0": 1,
        "m": 1.34,
        "tMelt": 925,
        "tRef": 293,
        "rhoCp": 2419200,
        "epsMax": 0.12,
        "sigMax": 0,
        "tension": 1100000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-c30-concrete-elastic",
      "name": "C30混凝土-HJC",
      "sourceUrl": "https://eurocodeapplied.com/design/en1992/concrete-design-properties",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。fc = 30 MPa、T = fctm = 2.90 MPa（EN 1992 C30/37），μl = 0.1。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 30000000,
        "T": 2900000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 10000000,
        "muc": 0.0005482,
        "pl": 800000000,
        "mul": 0.1,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-c40-concrete-elastic",
      "name": "C40混凝土-HJC",
      "sourceUrl": "https://eurocodeapplied.com/design/en1992/concrete-design-properties",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。fc = 40 MPa、T = fctm = 3.51 MPa（EN 1992 C40/50），μl = 0.1。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 40000000,
        "T": 3510000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 13333333.333333334,
        "muc": 0.0006814,
        "pl": 800000000,
        "mul": 0.1,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-ht200-gray-cast-iron-elastic",
      "name": "HT200灰铸铁-Drucker–Prager",
      "sourceUrl": "https://www.materialhub.de/en/materials/key-to-metals-ht-200-gb",
      "notes": "灰铸铁拉压强度差异大、无明显屈服，属压力相关脆性材料，选 Drucker–Prager（LAW10）。由基础卡 fc = 720 MPa、ft = 200 MPa 按 Mohr–Coulomb 换算：sinφ = (fc − ft)/(fc + ft) → φ ≈ 34.4°，c = √(fc·ft)/2 ≈ 189.7 MPa；拉伸截断取 ft = 200 MPa。拉伸应变失效 ε₁ = ft/E = 0.2%，ε₂ = 0.5%（灰铸铁断后伸长率通常 < 1%，估计值）。仅作参考。",
      "card": {
        "model": "dp",
        "cohesion": 189700000,
        "friction": 34.42,
        "tension": 200000000,
        "failure": {
          "enabled": true,
          "strainStart": 0.002,
          "strainEnd": 0.005
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-qt450-10-ductile-iron-elastic",
      "name": "QT450-10球墨铸铁-Johnson–Cook",
      "sourceUrl": "https://dergipark.org.tr/tr/download/article-file/4098398",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。未检索到 QT450-10 的 JC 参数；A = 310 MPa、B = 728 MPa、n = 0.5545、C = 0.0241、m = 0.9361 借用相近牌号 EN-GJS-400 球铁（Özcan & Şeker 2024，拉伸试验组，https://dergipark.org.tr/tr/download/article-file/4098398），参考应变率取其拉伸试验速率 0.011 s⁻¹。原文未给熔点与比热，ρCp 填 0 关闭温升（Tm = 1423 K 仅为占位估计）。未检索到同牌号层裂强度，静水拉伸截断取静态抗拉强度 450 MPa（保守）。εp,max = 10%（GB/T 1348 牌号伸长率）。",
      "card": {
        "model": "jc",
        "a": 310000000,
        "b": 728000000,
        "n": 0.5545,
        "C": 0.0241,
        "rate0": 0.011,
        "m": 0.9361,
        "tMelt": 1423,
        "tRef": 293,
        "rhoCp": 0,
        "epsMax": 0.1,
        "sigMax": 0,
        "tension": 450000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-c11000-copper-elastic",
      "name": "C11000紫铜-Johnson–Cook",
      "sourceUrl": "https://ia800406.us.archive.org/4/items/AConstitutiveModelAndDataForMetals/A%20constitutive%20model%20and%20data%20for%20metals_text.pdf",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 90 MPa、B = 292 MPa、n = 0.31、C = 0.025、m = 1.09、Tm = 1356 K、cp = 383 J/(kg·K) 取 Johnson & Cook（1983）OFHC 铜（https://ia800406.us.archive.org/4/items/AConstitutiveModelAndDataForMetals/A%20constitutive%20model%20and%20data%20for%20metals_text.pdf），C11000 电解韧铜成分与之接近。未检索到同牌号层裂强度，静水拉伸截断取静态抗拉强度 221 MPa（保守）。εp,max = 45%。",
      "card": {
        "model": "jc",
        "a": 90000000,
        "b": 292000000,
        "n": 0.31,
        "C": 0.025,
        "rate0": 1,
        "m": 1.09,
        "tMelt": 1356,
        "tRef": 293,
        "rhoCp": 3424020,
        "epsMax": 0.45,
        "sigMax": 0,
        "tension": 221000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-c28000-brass-elastic",
      "name": "C28000黄铜-Johnson–Cook",
      "sourceUrl": "https://ia800406.us.archive.org/4/items/AConstitutiveModelAndDataForMetals/A%20constitutive%20model%20and%20data%20for%20metals_text.pdf",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 112 MPa、B = 505 MPa、n = 0.42、C = 0.009、m = 1.68、Tm = 1189 K 取 Johnson & Cook（1983）弹壳黄铜（70/30，https://ia800406.us.archive.org/4/items/AConstitutiveModelAndDataForMetals/A%20constitutive%20model%20and%20data%20for%20metals_text.pdf），C28000 为 60/40 Muntz 黄铜，属近似借用；cp 取 385 J/(kg·K)。未检索到同牌号层裂强度，静水拉伸截断取静态抗拉强度 360 MPa（保守）。εp,max = 40%。",
      "card": {
        "model": "jc",
        "a": 112000000,
        "b": 505000000,
        "n": 0.42,
        "C": 0.009,
        "rate0": 1,
        "m": 1.68,
        "tMelt": 1189,
        "tRef": 293,
        "rhoCp": 3230150,
        "epsMax": 0.4,
        "sigMax": 0,
        "tension": 360000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-ti-6al-4v-elastic",
      "name": "Ti-6Al-4V钛合金-Johnson–Cook",
      "sourceUrl": "https://arxiv.org/html/2209.04197v1",
      "notes": "Johnson–Cook（LAW2，/MAT/PLAS_JOHNS）：σy = (A + B·εpⁿ)(1 + C·ln ε̇*)(1 − T*ᵐ)；E、ν、ρ 取自关联基础卡，Tr = 293 K。塑性应变达到 εp,max（取断后伸长率）时删除单元。A = 867 MPa、B = 344 MPa、n = 0.361、C = 0.0145、ε̇0 = 0.002 s⁻¹ 取 Klippel 等（2022）表 6（https://arxiv.org/html/2209.04197v1）。原文未做高温试验、未给 m，因此 ρCp 填 0 关闭绝热温升（m = 1、Tm = 1878 K 不起作用）。静水拉伸截断取锻造态层裂强度约 5.0 GPa（https://pubs.aip.org/aip/jap/article/120/13/135902/143712/Spall-fracture-in-additive-manufactured-Ti-6Al-4V）。εp,max = 14%。",
      "card": {
        "model": "jc",
        "a": 867000000,
        "b": 344000000,
        "n": 0.361,
        "C": 0.0145,
        "rate0": 0.002,
        "m": 1,
        "tMelt": 1878,
        "tRef": 293,
        "rhoCp": 0,
        "epsMax": 0.14,
        "sigMax": 0,
        "tension": 5000000000,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-thesis43-granite-elastic",
      "name": "花岗岩（博士论文）-JH2",
      "sourceUrl": "",
      "notes": "JH2（LAW79），全部取自博士论文《基于物质点法的高地应力环境非均质岩石爆破响应及破岩调控》（终稿）表 2.2.5（花岗岩，§2.3.2.2 与 §4.3.1 共用）：ρ = 2.66 g/cm³（关联基础卡），K = 25.7 GPa，G = 21.9 GPa，HEL = 4.5 GPa，P_HEL = 3.7 GPa，T = 54 MPa，ε̇0 = 1 s⁻¹，SFMAX = 0.25，C = 0.005，A = 0.76，N = 0.62，B = 0.25，M = 0.62，D1 = 0.005，D2 = 0.7，K1 = 25.7 GPa，K2 = −4500 GPa，K3 = 300000 GPa。表中 HEL 符号排版不清，按 2Gμ/(1+μ) ≈ 1.2 GPa、HEL = P_HEL + ⅔σ_HEL = 4.5 GPa 核对，4.5 GPa 为纵向 HEL。论文表未给出膨胀系数 β，按 Baranowski 等（2024，https://doi.org/10.1038/s41598-023-49668-z）表 2 取 1.0。",
      "card": {
        "model": "jh2",
        "G": 21900000000,
        "A": 0.76,
        "N": 0.62,
        "B": 0.25,
        "M": 0.62,
        "C": 0.005,
        "rate0": 1,
        "maxStrength": 0.25,
        "T": 54000000,
        "HEL": 4500000000,
        "pHEL": 3700000000,
        "D1": 0.005,
        "D2": 0.7,
        "K1": 25700000000,
        "K2": -4500000000000,
        "K3": 300000000000000,
        "beta": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-thesis43-sandstone-elastic",
      "name": "青砂岩-JH2",
      "sourceUrl": "",
      "notes": "JH2（LAW79），全部取自博士论文《基于物质点法的高地应力环境非均质岩石爆破响应及破岩调控》（终稿）表 4.0.3（青砂岩）：ρ = 2.34 g/cm³（关联基础卡），K = 12.67 GPa，G = 9.98 GPa，HEL = 4.5 GPa，P_HEL = 3.7 GPa，T = 44 MPa，ε̇0 = 1 s⁻¹，SFMAX = 0.25，C = 0.005，A = 0.76，N = 0.62，B = 0.25，M = 0.62，D1 = 0.005，D2 = 0.7，K1 = 25.7 GPa，K2 = −4500 GPa，K3 = 300000 GPa。原表 K = 12.67 GPa 与 K1 = 25.7 GPa 不一致，且 HEL、P_HEL 与花岗岩相同，按原表照录未修改。论文表未给出 β，按 Baranowski 等（2024，https://doi.org/10.1038/s41598-023-49668-z）表 2 取 1.0。",
      "card": {
        "model": "jh2",
        "G": 9980000000,
        "A": 0.76,
        "N": 0.62,
        "B": 0.25,
        "M": 0.62,
        "C": 0.005,
        "rate0": 1,
        "maxStrength": 0.25,
        "T": 44000000,
        "HEL": 4500000000,
        "pHEL": 3700000000,
        "D1": 0.005,
        "D2": 0.7,
        "K1": 25700000000,
        "K2": -4500000000000,
        "K3": 300000000000000,
        "beta": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-blanco-mera-elastic",
      "name": "花岗岩（Pérez-Rey 2024）-JH2",
      "sourceUrl": "https://doi.org/10.1038/s41598-023-49668-z",
      "notes": "JH2（LAW79）。A、N、B、M、C、SFMAX、HEL、P_HEL、D1、D2、K2、K3 借用同类岩石博士论文《基于物质点法的高地应力环境非均质岩石爆破响应及破岩调控》（终稿）表 2.2.5 花岗岩值，β = 1.0 取 Baranowski 等（2024）。 G 填 0 由基础卡 E、ν 计算，EOS K1 取基础卡 E、ν 换算的体积模量；T 不直接用静态抗拉强度：JH2 的 T 是动态静水拉伸强度，按 Baranowski 等（2024，https://doi.org/10.1038/s41598-023-49668-z）表 2 T = 8.0 MPa 与表 1 静态巴西强度 2.2 MPa 之比 3.64 放大基础卡抗拉强度 5.64 MPa，得 T = 20.5 MPa（该比值随网格尺寸变化，仅作参考）。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "jh2",
        "G": 0,
        "A": 0.76,
        "N": 0.62,
        "B": 0.25,
        "M": 0.62,
        "C": 0.005,
        "rate0": 1,
        "maxStrength": 0.25,
        "T": 20510000,
        "HEL": 4500000000,
        "pHEL": 3700000000,
        "D1": 0.005,
        "D2": 0.7,
        "K1": 39700000000,
        "K2": -4500000000000,
        "K3": 300000000000000,
        "beta": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-cotta-parallel-elastic",
      "name": "砂岩-JH2",
      "sourceUrl": "https://doi.org/10.1038/s41598-023-49668-z",
      "notes": "JH2（LAW79）。A = 0.71、N = 0.55、B = 0.30、M = 0.40、C = 0.022、SFMAX = 0.25、HEL = 1982 MPa、P_HEL = 1374 MPa、D1 = 0.002、D2 = 1.20、K2 = 9000 MPa、K3 = 22000 MPa、β = 1.0 取 Baranowski 等（2024）砂岩表 2（https://doi.org/10.1038/s41598-023-49668-z）。 G 填 0 由基础卡 E、ν 计算，EOS K1 取基础卡 E、ν 换算的体积模量；T 不直接用静态抗拉强度：JH2 的 T 是动态静水拉伸强度，按 Baranowski 等（2024，https://doi.org/10.1038/s41598-023-49668-z）表 2 T = 8.0 MPa 与表 1 静态巴西强度 2.2 MPa 之比 3.64 放大基础卡抗拉强度 1.7 MPa，得 T = 6.2 MPa（该比值随网格尺寸变化，仅作参考）。原文正文给出 K3 = 28.0 GPa 与表 2 的 22000 MPa 不一致，这里取表 2。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "jh2",
        "G": 0,
        "A": 0.71,
        "N": 0.55,
        "B": 0.3,
        "M": 0.4,
        "C": 0.022,
        "rate0": 1,
        "maxStrength": 0.25,
        "T": 6182000,
        "HEL": 1982000000,
        "pHEL": 1374000000,
        "D1": 0.002,
        "D2": 1.2,
        "K1": 5625000000,
        "K2": 9000000000,
        "K3": 22000000000,
        "beta": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-marble-wang2023-elastic",
      "name": "大理岩-JH2",
      "sourceUrl": "https://doi.org/10.1038/s41598-023-49668-z",
      "notes": "JH2（LAW79）。未检索到大理岩专用 JH2 参数表；A、N、B、M、C、SFMAX、HEL、P_HEL、D1、D2、K2、K3 借用致密结晶岩博士论文《基于物质点法的高地应力环境非均质岩石爆破响应及破岩调控》（终稿）表 2.2.5 花岗岩值，β = 1.0 取 Baranowski 等（2024）。 G 填 0 由基础卡 E、ν 计算，EOS K1 取基础卡 E、ν 换算的体积模量；T 不直接用静态抗拉强度：JH2 的 T 是动态静水拉伸强度，按 Baranowski 等（2024，https://doi.org/10.1038/s41598-023-49668-z）表 2 T = 8.0 MPa 与表 1 静态巴西强度 2.2 MPa 之比 3.64 放大基础卡抗拉强度 5.67 MPa，得 T = 20.6 MPa（该比值随网格尺寸变化，仅作参考）。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "jh2",
        "G": 0,
        "A": 0.76,
        "N": 0.62,
        "B": 0.25,
        "M": 0.62,
        "C": 0.005,
        "rate0": 1,
        "maxStrength": 0.25,
        "T": 20620000,
        "HEL": 4500000000,
        "pHEL": 3700000000,
        "D1": 0.005,
        "D2": 0.7,
        "K1": 34490000000,
        "K2": -4500000000000,
        "K3": 300000000000000,
        "beta": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "blast-limestone-wang2023-elastic",
      "name": "石灰岩-JH2",
      "sourceUrl": "https://doi.org/10.1038/s41598-023-49668-z",
      "notes": "JH2（LAW79）。未检索到可读取的石灰岩 JH2 全表；A、N、B、M、C、SFMAX、HEL、P_HEL、D1、D2、K2、K3、β 借用沉积岩 Baranowski 等（2024）砂岩表 2（https://doi.org/10.1038/s41598-023-49668-z）。 G 填 0 由基础卡 E、ν 计算，EOS K1 取基础卡 E、ν 换算的体积模量；T 不直接用静态抗拉强度：JH2 的 T 是动态静水拉伸强度，按 Baranowski 等（2024，https://doi.org/10.1038/s41598-023-49668-z）表 2 T = 8.0 MPa 与表 1 静态巴西强度 2.2 MPa 之比 3.64 放大基础卡抗拉强度 5.06 MPa，得 T = 18.4 MPa（该比值随网格尺寸变化，仅作参考）。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "jh2",
        "G": 0,
        "A": 0.71,
        "N": 0.55,
        "B": 0.3,
        "M": 0.4,
        "C": 0.022,
        "rate0": 1,
        "maxStrength": 0.25,
        "T": 18400000,
        "HEL": 1982000000,
        "pHEL": 1374000000,
        "D1": 0.002,
        "D2": 1.2,
        "K1": 31280000000,
        "K2": 9000000000,
        "K3": 22000000000,
        "beta": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "blast-reef-limestone-wang2023-elastic",
      "name": "珊瑚礁灰岩-HJC",
      "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7143533/",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。高孔隙弱胶结岩体，选 HJC 以描述孔隙压溃–压实。μl = ρ_grain/ρ0 − 1（Wang 等 2020，https://pmc.ncbi.nlm.nih.gov/articles/PMC7143533/），ρ_grain 取方解石 2710 kg/m³。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 15000000,
        "T": 1420000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 5000000,
        "muc": 0.001265,
        "pl": 800000000,
        "mul": 1.765,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "blast-gypsum-wang2023-elastic",
      "name": "石膏-HJC",
      "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7143533/",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。多孔软岩，选 HJC 以描述压溃–压实。μl = ρ_grain/ρ0 − 1（Wang 等 2020，https://pmc.ncbi.nlm.nih.gov/articles/PMC7143533/），ρ_grain 取石膏矿物 2320 kg/m³。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 3100000,
        "T": 1110000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 1033333.3333333334,
        "muc": 0.0001314,
        "pl": 800000000,
        "mul": 1.035,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:16:46.337Z"
    },
    {
      "id": "blast-dmc-printed-gypsum-elastic",
      "name": "打印石膏-HJC",
      "sourceUrl": "https://researching.cn/articles/OJ492a2538a0491146",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。基础卡无强度：fc = 8.63 MPa 取粘结剂喷射打印石膏的抗压强度（https://researching.cn/articles/OJ492a2538a0491146）；T 按 fc/10 估计。μl = ρ_grain/ρ0 − 1（https://pmc.ncbi.nlm.nih.gov/articles/PMC7143533/），ρ_grain 取 2320 kg/m³。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 8630000,
        "T": 863000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 2876666.6666666665,
        "muc": 0.00863,
        "pl": 800000000,
        "mul": 0.7984,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-notched-concrete-beam-elastic",
      "name": "混凝土-HJC",
      "sourceUrl": "https://eurocodeapplied.com/design/en1992/concrete-design-properties",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。基础卡无强度：由 EN 1992 Ecm = 22(fcm/10)^0.3 与 E = 35 GPa 反算 fcm ≈ 47 MPa，T = fctm = 0.3·fck^(2/3) ≈ 3.45 MPa（fck = fcm − 8）。μl = 0.1。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 47000000,
        "T": 3450000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 15666666.666666666,
        "muc": 0.0008057,
        "pl": 800000000,
        "mul": 0.1,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-eccentric-hole-mortar-elastic",
      "name": "水泥砂浆-HJC",
      "sourceUrl": "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。基础卡无强度且未检索到可读取的砂浆 HJC 表：fc 按 GB 50003 的 M10 砂浆强度等级取 10 MPa，T 按 fc/10 取 1.0 MPa，均为假设值。μl = 0.1。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 10000000,
        "T": 1000000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 3333333.3333333335,
        "muc": 0.0009361,
        "pl": 800000000,
        "mul": 0.1,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    },
    {
      "id": "blast-skb-bhk-backfill-elastic",
      "name": "回填混凝土-HJC",
      "sourceUrl": "https://www.skb.com/publication/2493324/R-19-12.pdf",
      "notes": "HJC（LAW126）。A、B、N、C、SFMAX、EFMIN、D1、D2、Pl 与 K1–K3 取 Holmquist, Johnson & Cook (1993), Proc. 14th Int. Symp. Ballistics, pp. 591–600 的 48 MPa 混凝土原始标定值（参数含义见 https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law126_johnson_holmquist_concrete_starter_r.htm）；fc、T 取关联基础卡，Pc = fc/3，μc = Pc/K（K 由基础卡 E、ν 计算），G 填 0 由 E、ν 计算。fc、T 取 SKB R-19-12 §6.1 给出的参考值中值（抗压 ~50–60 MPa、抗拉 ~4–6 MPa，https://www.skb.com/publication/2493324/R-19-12.pdf）。μl = 0.1。 仅作参考，未针对该材料标定。",
      "card": {
        "model": "hjc",
        "G": 0,
        "A": 0.79,
        "B": 1.6,
        "N": 0.61,
        "fc": 55000000,
        "T": 5000000,
        "C": 0.007,
        "rate0": 1,
        "maxStrength": 7,
        "efMin": 0.01,
        "pc": 18333333.333333332,
        "muc": 0.000723,
        "pl": 800000000,
        "mul": 0.1,
        "K1": 85000000000,
        "K2": -171000000000,
        "K3": 208000000000,
        "D1": 0.04,
        "D2": 1,
        "failure": {
          "enabled": false,
          "strainStart": 0.0002,
          "strainEnd": 0.001
        }
      },
      "updatedAt": "2026-11-12T10:08:33.552Z"
    }
  ]
};
