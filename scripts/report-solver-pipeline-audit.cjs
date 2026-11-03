const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=path.resolve('..'),cache=path.resolve('tmp/paper-plane-stress');
const audit=JSON.parse(fs.readFileSync(path.join(root,'论文平面应力模型-参数与验证清单.json')));
const close=(a,b)=>Math.abs(a-b)<=2e-14*Math.max(1,Math.abs(b));
const records=audit.records.map(r=>{
 const t=JSON.parse(fs.readFileSync(path.join(cache,'revision-20us',r.name+'.json'))),meta=t.metadata;
 if(meta.geometryDiagnosticsVersion!==1)throw Error('Missing geometry diagnostics: '+r.name);
 for(const {material:m} of r.materials){const j=m.blastConstitutive.jh2,p=meta.jh2KernelInputs.find(p=>p.materialNo===m.materialNo);
  const G=j.G||m.elasticModulus/(2*(1+m.poissonRatio));
  const values=[G,2*G,j.A,j.B,j.M,j.N,j.C,j.rate0,j.maxStrength,j.T/j.pHEL,j.pHEL,j.normalizationStress||1.5*(j.HEL-j.pHEL),j.D1,j.D2,j.K1,j.K2,j.K3,j.beta,0,1e30];
  if(!p||p.density!==m.density||p.parameters.some((v,i)=>!close(v,values[i])))throw Error('Native material receipt differs: '+r.name);
 }
 for(const [field,setting] of Object.entries({productEOS:'productEOS',airEOS:'airEOS',referenceDensity:'productDensity',specificEnergy:'productEnergy',A:'jwlA',B:'jwlB',R1:'jwlR1',R2:'jwlR2',omega:'jwlOmega',airDensity:'airDensity',airPressure:'airPressure',airGamma:'airGamma'}))if(!close(meta.gasKernelInputs[field],r.settings[setting]))throw Error('Native gas receipt differs: '+field);
 const max=fn=>Math.max(...t.frames.map(fn));
 return {name:r.name,ok:t.ok,lastSavedTime:t.lastSavedTime,error:t.error,parameterReceiptMatches:true,
  peakSavedWallPressure:max(f=>f.pressure),maximumPlaneStressResidual:max(f=>f.maximumPlaneStressResidual),
  maximumGasEnergyRelativeError:max(f=>Math.abs(f.gasInternalEnergy+f.gasKineticEnergy+f.gasWallWork-meta.initialGasEnergy)/meta.initialGasEnergy),
  maximumCflRatio:max(f=>f.maximumCflRatio),lastFrame:t.frames.at(-1),jh2KernelInputs:meta.jh2KernelInputs,gasKernelInputs:meta.gasKernelInputs};
});
const sourceChecks=['openradioss-jh2','cbgeo-materials','singularity-eos-runtime'].map(name=>{
 const dir=path.resolve('third_party',name),manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
 for(const f of manifest.files)if(crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,f.file))).digest('hex')!==f.sha256)throw Error('Modified upstream source '+f.file);
 return {name,commit:manifest.commit,unchangedFiles:manifest.files.length};
});
const log=fs.readFileSync('tmp/solver-pipeline-acceptance.log','utf8'),count=key=>Number(log.match(new RegExp('(?:ℹ |info )?'+key+' (\\d+)'))?.[1]??-1);
const tests={tests:count('tests'),pass:count('pass'),fail:count('fail'),log:path.resolve('tmp/solver-pipeline-acceptance.log')};
if(tests.tests<1||tests.fail!==0||tests.tests!==tests.pass)throw Error('Acceptance tests have not finished successfully.');
const extraLog=fs.readFileSync('tmp/solver-audit-extreme-flow.log','utf8');
if(!extraLog.includes('✔ extreme transverse flow')||!extraLog.includes('ℹ fail 0'))throw Error('Extreme material-point test has not passed.');
tests.additionalUniqueTests=1;tests.totalUniquePassed=tests.pass+1;tests.additionalLog=path.resolve('tmp/solver-audit-extreme-flow.log');
const flowRun=require('child_process').spawnSync('tests/native/x64/Release/rock-verification.exe',['failed-plane-flow'],{encoding:'utf8',windowsHide:true,timeout:30000});
if(flowRun.status!==0)throw Error(flowRun.stderr);const isolatedFlow=JSON.parse(flowRun.stdout);
const report={date:'2026-11-03',status:'Audit completed; four reproduction models still fail the 20 us acceptance test',tests,sourceChecks,records,isolatedFlow,
 fixes:['Stable small-strain EOS energy diagnostic integral; no constitutive stress/damage changes','Separate in-plane Jacobian, thickness stretch and plane-stress residual diagnostics; legacy frame decoding retained','Native input receipts share the actual JH2 parameter packer; export solver-inputs.json','Failed-cell log includes time, element, in-plane deformation, thickness, damage and stress'],
 unresolved:['No demonstrated correction of the experimental damage morphology','20 us tests remain failed','Full strong-shock finite-plane-stress solution is not validated by elastic/ABI tests'],
 uncertainties:audit.uncertainties,
 nativeSha256:crypto.createHash('sha256').update(fs.readFileSync('TensoraCore/x64/Release/TensoraCore.exe')).digest('hex')};
fs.writeFileSync(path.join(root,'求解链核查-2026-11-03.json'),JSON.stringify(report,null,2));
const us=v=>(v*1e6).toFixed(6),lines=[
 '# 求解器、参数传输、单位与显式积分核查（2026-11-03）','',
 '结论：已完成下面列明范围的计算链核查并修复诊断缺陷；没有证据证明四个模型的异常已经解决。四个20 μs验收仍失败，不保存为完成的实验复现版本。',
 '',`综合自动校验 ${tests.tests} 项通过，另增加1项极端材料点隔离检查通过，共${tests.totalUniquePassed}项不同检查。它们验证本构调用、参数与单位、解析动力响应、气体守恒和接口功；不能代替四工况强冲击破坏验证。`,'',
 '## 确认的缺陷及修订','',
 '1. JH2储能诊断在极小压缩应变下直接计算近似相等的数之差，发生浮点相消。新解析振子测试曾出现储能1.6563853e-8、解析值1.9297583e-8 J/m；改为稳定的积分级数后通过。该函数只统计能量，不更新应力、损伤、速度或位移；它不是损伤形态的已证实原因。','',
 '2. 旧诊断只记录三维体积比 J3D。平面应力的 J3D=Jxy×厚度伸长比，可在面内面积严重塌缩时仍接近1。新增最小Jxy、厚度伸长比范围和σzz相对残差；结果页和CSV均保存，旧版结果布局仍可读取。','',
 '3. 新增核心实际输入回执。JH2回执与真实本构调用共用同一个20槽参数打包函数；逐材料比对密度、G/2G、A/B/M/N、T/pHEL、pHEL、σHEL、K1/K2/K3、β与损伤系数。气体回执核对初始密度、比内能、JWL和空气参数。结果导出增加solver-inputs.json。','',
 '4. 塌缩异常不再笼统建议换求解方法，记录失败时间、单元编号、Fxy、Jxy、上一状态厚度、损伤、应力和时间步。没有修改上游材料源码，没有重开黏性、增加质量阻尼或削减载荷。','',
 '## 核查范围与证据','',
 '| 环节 | 已执行的独立核查 |','| --- | --- |',
 '| 基础静力学及安全校核 | TRI3拉伸/剪切解析解、节点顺序反转、平面应力/平面应变、三维应力安全准则、CPU/GPU一致性 |',
 '| OpenRadioss JH2 | 360步三维路径和960步平面应力路径，绕过C++桥接直接调用原始Fortran；强度、损伤起点、持载和膨胀历史的独立参考核对 |',
 '| CB-Geo固体 | 线弹性及Mohr–Coulomb原始实现，多轴应变、工程剪切和软化历史核对 |',
 '| LANL气体EOS | 100组状态、SI/CGS缩放、压力反算、声速热力学导数；IdealGas/JWL/Noble-Abel/StiffenedGas |',
 '| 显式动力学 | 在生产网格中保留一个自由度，独立组装质量与刚度，与受恒定阶跃力的解析振子位移、速度及能量对照；覆盖两种平面模式和JH2小/有限变形，步长减半呈二阶收敛 |',
 '| 气体积分及耦合 | Sod解析解与加密收敛、静止接触、移动壁功、质量/能量守恒、空气间隙传播延迟、气压冲量不重复平均、界面功一致、预应力静平衡 |','',
 '采用m、kg、s、Pa和J/kg；界面的GPa/MPa/MJ/kg只换算一次。工程剪切增量γxy=2εxy，密度与JWL参考密度分开传入。2D网格质量和能量按单位初始厚度统计，能量单位J/m；50 mm厚度的总量应乘0.05。当前四模型没有节点外力，不存在总力与单位厚度力混用的数值来源。','',
 '乳化炸药参考文献表2确实把E0列为MJ/kg，3.99 MJ/kg→3.99e6 J/kg没有误作J/m³。[原始文献表2](https://onlinelibrary.wiley.com/doi/10.1155/2020/8194801)。JH2应力/模量单位及归一化规则参照[Altair LAW79官方说明](https://2024.help.altair.com/2024.1/hwsolvers/rad/topics/solvers/rad/mat_law79_john_holm_starter_r.htm)。','',
 `上游原始文件共${sourceChecks.reduce((s,x)=>s+x.unchangedFiles,0)}个，SHA-256全部与固定提交清单相符。仅材料点本构是这些原始库；网格内力、显式积分和气固耦合仍属于本程序，所以原始本构库正确不等于整体自动正确。`,'',
 '## 四工况20 μs重测','',
 '| 工况 | 最后正常保存 | 结果 | 核心参数回执 | 最大σzz相对残差 |','| --- | ---: | --- | --- | ---: |',
 ...records.map(r=>`| ${r.name} | ${us(r.lastSavedTime)} μs | ${r.error.includes('inverted/collapsed')?'面内单元塌缩':'60秒诊断执行限时'} | 全部匹配 | ${r.maximumPlaneStressResidual.toExponential(3)} |`),'',
 '三个明确塌缩的工况发生在3.223653、3.241973和3.243351 μs附近；均质板20–20在最后保存3 μs后推进极慢，触发的是墙钟限时，没有完成20 μs。60秒诊断限时未写入用户模型；原文件仍保留7200秒执行上限。','',
 'W45-0–0的失败单元3811：Jxy约9.84e-5，上一状态厚度伸长比约10036，damage=1，时间步约1.31e-11 s。最后保存3 μs时，J3D仍为0.9882，而最小Jxy已为0.1775，最大厚度伸长比5.7868。旧J3D诊断确实会掩盖该过程。','',
 '气体能量相对误差（全部已保存帧）均小于2e-15；这只证明气体能量收支，不能证明破坏形态或整个固体非线性求解正确。新平面应力σzz相对残差均小于1e-8，未发现直接把σzz清零来冒充求解。最大CFL诊断是dt与含0.45安全系数的建议步长之比，个别帧约1.23，对应dt*c/h约0.55；不能把该诊断直接称为无条件稳定证明。此前将步长缩小为1/4仍出现相同塌缩路径。','',
 '## 对异常机制的当前判断及未闭合项','',
 '观测到孔壁压力约0.6–1.1 GPa、近孔单元完全损伤，随后面内压缩与厚度增长。按当前破碎强度关系、σzz=0及该卡的归一化系数估算，完全破坏材料的面内主压应力承载上界仅约0.09–0.11 GPa（应变率1–1e6/s范围，忽略有限步更新中的膨胀滞后）。这支持“完全损伤后的平面应力流动导致面积塌缩”这一解释；它不是模型已验证的结论，也不能由此排除其它强冲击耦合/有限变形问题。','',
 `另用一个初始damage=1的JH2点做隔离测试，不使用网格、气体或显式运动积分。累计施加面内对数压缩应变-9，平面应力约束给出Jxy=${isolatedFlow.planarJacobian.toExponential(6)}、厚度伸长比=${isolatedFlow.thicknessStretch.toFixed(3)}、J3D=${isolatedFlow.volumeJacobian.toFixed(8)}。最终应力绕过C++桥接直接调用原始Fortran也一致。它证明同类极端横向流动可出现在这张材料卡的平面应力响应中，而非必须由网格或气体程序制造；该规定应变路径本身不是对爆破位移历程的独立验证。`,'',
 '通用材料卡的实测E/ν与JH2使用的G/K1不一致：花岗岩实际JH2切线E≈51.166 GPa、ν≈0.16818；砂岩≈26.509 GPa、ν≈0.32809。论文砂岩K=12.67 GPa而K1=25.7 GPa、HEL符号含义及实验乳化炸药牌号/EOS标定仍有不确定性，不能宣布模型本身没有问题。当前按论文/已注明来源保留，未自行调参。','',
 '本次保持用户暂缓的两项机制不变，不把它们当作已经证实的本次异常原因。Gf不参与当前上游JH2更新。全部未确定数值仍统一列于[参数核对与不确定项](论文平面应力模型-参数核对与不确定项.md)；本报告JSON保留完整参数回执和失败状态。','',
 '没有达到“20 μs无异常即可保存完成”的条件。四个根目录JSON继续标注为排查版本。',''
];
fs.writeFileSync(path.join(root,'求解链核查-2026-11-03.md'),lines.join('\n'));
console.log(JSON.stringify({tests,models:records.map(r=>({name:r.name,ok:r.ok,lastSavedTime:r.lastSavedTime})),unchangedUpstreamFiles:sourceChecks.reduce((s,x)=>s+x.unchangedFiles,0)}));
