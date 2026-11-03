from pathlib import Path
import json,hashlib,copy
root=Path.cwd();dest=root.parent;c=root/'tmp/paper-plane-stress'
rev=json.loads((c/'revision-changes.json').read_text(encoding='utf-8'))
old=json.loads((Path(rev['backup'])/'论文平面应力模型-参数与验证清单.json').read_text(encoding='utf-8'))
sources=old['sources']+[{'id':'GFg','title':'Xia et al. 2020, Table 4, granite Gf=519.7 J/m²','url':'https://doi.org/10.1155/2020/8194801'},{'id':'GFs','title':'Materials 2023,16,1056, Table 4 S group sandstone NSCB mean GIc=82.51 J/m²','url':'https://doi.org/10.3390/ma16031056'}]
records=[]
for change in rev['changes']:
 p=Path(change['file']);s=json.loads(p.read_text(encoding='utf-8'));d=json.loads((c/(change['name']+'-direct.json')).read_text(encoding='utf-8'));test=json.loads((c/'revision-20us'/(change['name']+'.json')).read_text(encoding='utf-8'))
 assert s['blastSettings']['shockViscosity']==0
 assert len(d['elements']) in [43544,49816]
 s['paperModelProvenance']['validationStatus']='20 us test FAILED: not a completed reproduction model.'
 s['paperModelProvenance']['deferredByUser']=['Crack separation / post-failure fragment motion','Flow/pressure transmission into failed weak layer']
 s['paperModelProvenance']['latestTest']={'targetSeconds':20e-6,'ok':test['ok'],'lastSavedSeconds':test.get('lastSavedTime',20e-6),'error':test.get('error')}
 p.write_text(json.dumps(s,ensure_ascii=False,separators=(',',':')),encoding='utf-8');change['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
 mats=[]
 for m in d['materials']:
  j=m['blastConstitutive']['jh2'];G,K=j['G'],j['K1'];E=9*K*G/(3*K+G);nu=(3*K-2*G)/(2*(3*K+G))
  mats.append({'material':m,'activeJH2Tangent':{'bulkModulus':K,'shearModulus':G,'derivedE':E,'derivedNu':nu},'independentGfAffectsJH2':False})
 records.append({'name':change['name'],'file':str(p),'sha256':change['sha256'],'nodes':len(d['nodes']),'elements':len(d['elements']),'settings':s['blastSettings'],'materials':mats,'test20us':test})
unc=copy.deepcopy(old['uncertainties'])
for u in unc:
 if u['id']=='U11':u['adopted']['shockViscosity']=0;u['uncertainty']='当前20μs测试未通过，见test20us；不再以2μs启动测试作为交付完成依据。'
 if u['id']=='U12':u['adopted']['gf_J_m2']=519.7;u['adopted']['sandstoneReferenceGf_J_m2']=82.51;u['source']='GFg、GFs及上游JH2参数表';u['reason']='独立Gf不在当前SIGEPS79参数中，不参与本次损伤演化；用户已要求不再围绕它排查。'
probe=json.loads((c/'W45-no-viscosity-timestep-probe.json').read_text(encoding='utf-8'))
checks={
 'allFourArtificialViscosityDisabled':True,
 'planeStressRetained':all(r['settings']['planeMode']==0 for r in records),
 'meshBudgetRetained':all(30000<=r['elements']<=60000 for r in records),
 'geometryAndMaterialAssignment':'未修改几何和网格；独立解析分区核查错误数0；导入前后节点/单元/材料数据哈希一致。',
 'strainMapping':'工程剪切增量=2εxy，Voigt次序xx,yy,zz,xy,yz,xz；已有原始Fortran对照测试通过。',
 'damageMapping':'原始Fortran DMG → State.damage → Cell.damage → 单元输出第7标量(索引6) → 云图damage，未做阈值重映射。',
 'loadDefinition':'只通过confineX/confineY施加0/20MPa围压，未重复叠加分布力；气体源读取整套JWL卡。',
 'JH2Normalization':'实际SHEL显式4.5GPa；纵向HEL记录6.7GPa是导出字段，显式SHEL启用时不使用其回算值。',
 'paperMaterialConflict':'青砂岩K=12.67GPa、K1=25.7GPa按原表保留；JH2实际EOS初始体积切线是K1。实测Ed/ν不等于该JH2切线，未擅自覆盖。',
 'renderingBugFixed':'CSS flex规则覆盖hidden，导致不参与JH2的Gf仍显示；已使blast页hidden属性生效，四模型浏览器验证通过。',
 'noUnsupportedPhysicsAdded':'未重开人工黏性、未增加质量阻尼、未削减装药能量、未改JH2强度/损伤系数以拟合形态。',
 'deferredByUser':['连续网格损伤后的裂纹分离/碎块运动','破坏弱层内部气体传递']}
manifest_checks=[]
for name in ['openradioss-jh2','cbgeo-materials','singularity-eos-runtime']:
 base=root/'third_party'/name;m=json.loads((base/'manifest.json').read_text(encoding='utf-8'));good=all(hashlib.sha256((base/f['file']).read_bytes()).hexdigest()==f['sha256'] for f in m['files']);assert good;manifest_checks.append({'component':name,'files':len(m['files']),'unchanged':good,'commit':m['commit']})
audit={'date':'2026-11-03','status':'NOT COMPLETE: 20 us tests failed','backup':rev['backup'],'changes':rev['changes'],'checks':checks,'upstreamSourceChecks':manifest_checks,'sources':sources,'uncertainties':unc,'records':records,'timeStepSensitivity':[{'factor':p['factor'],'dt':p['dt'],'ok':p['ok'],'lastSavedTime':p['frames'][-1]['time'] if p['frames'] else None,'error':p.get('error')} for p in probe]}
(dest/'论文平面应力模型-参数与验证清单.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
(c/'revision-changes.json').write_text(json.dumps(rev,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 四工况修订与20μs核查：未通过完成验收','', '四个原文件已原位关闭压缩人工黏性（shockViscosity=0），保留平面应力、原JH2系数和3万—6万单元预算。原文件及原报告备份位置：'+rev['backup']+'。','', '**结论：四个工况均未到达20μs，不标记为完成版，也不宣称损伤形态已纠正。** 用户要求暂不处理的两项机制保持不变。','', '| 工况 | 节点 | 单元 | 最后保存时间 | 20μs测试结果 |','| --- | ---: | ---: | ---: | --- |']
for r in records:
 t=r['test20us'];reason='单元翻转/塌缩' if 'inverted/collapsed' in t.get('error','') else '推进停滞，触发60秒诊断执行限时'
 lines.append(f"| {r['name']} | {r['nodes']} | {r['elements']} | {t.get('lastSavedTime',20e-6)*1e6:.3f} μs | {reason} |")
lines+=['','本次测试目标20μs、保存41帧；其余物理设置与修改后的文件一致。60秒限时仅用于诊断，不是物理时间，也未改变模型中7200秒执行上限。失败后不再把部分结果当作完整结果输出。','', '## 已检查和修订','']
for key,value in checks.items():lines.append(f'**{key}**：'+(json.dumps(value,ensure_ascii=False) if not isinstance(value,str) else value)+'。\n')
lines+=['## 时间步对照','','针对W45-0-0，自动时间步与缩小为四分之一的时间步，都在最后正常保存帧3.2μs后触发单元翻转。该结果不支持将异常简单归因于时间步过大；未通过增加黏性或阻尼掩盖异常。','', '| 步长倍率 | 请求步长 | 最后正常保存 | 结果 |','| --- | ---: | ---: | --- |']
for p in probe:lines.append(f"| {p['factor']} | {p['dt']*1e6:.8f} μs | {p['frames'][-1]['time']*1e6:.3f} μs | 翻转失败 |")
lines+=['','## 材料数值核对','','通用材料卡保留论文实测Ed/ν，但JH2实际调用使用论文数值表的G/K1和显式σHEL。下列差异已明确核对，不再把界面Ed误称为JH2实际弹性切线。','', '| 岩石 | 界面实测Ed / ν | JH2 G / K1 | 推导的JH2 E / ν |','| --- | --- | --- | --- |']
for m in records[2]['materials']:
 x=m['material'];j=x['blastConstitutive']['jh2'];t=m['activeJH2Tangent'];lines.append(f"| {x['name']} | {x['elasticModulus']/1e9:.5f} GPa / {x['poissonRatio']} | {j['G']/1e9} / {j['K1']/1e9} GPa | {t['derivedE']/1e9:.6f} GPa / {t['derivedNu']:.6f} |")
lines+=['','论文青砂岩K=12.67GPa而K1=25.7GPa的差异保留，未为了得到某种图形而改写。炸药实际试验牌号仍未知，继续采用已注明来源的整套乳化炸药参考参数；它不是本文试样的精确标定。','', '## 不再作为本次调形态依据的Gf','','JH2不使用独立Gf。文件内保留文献参考记录：花岗岩519.7 J/m²，砂岩82.51 J/m²；这不是两类岩石统一公认常数。用户已要求不再围绕该字段排查。显示问题已修复。','', '## 仍未确定的数值与简化','']
for u in unc:lines += [u['id']+' '+u['parameter']+'：'+u['uncertainty'],'']
lines+=['## 资料来源','']
for src in sources:
 lines.append(src['id']+'：'+src['title']+'；'+src.get('url',src.get('path',''))+'\n')
lines+=['## 保存状态','','四个JSON是已修改、可导入的排查版本，保存在“计算力学程序”根目录。机器可读清单保存当前文件SHA-256、全部设置、材料参数、20μs失败记录、时间步对照与上游源码哈希。尚不满足“无异常即可保存完成”的条件。']
(dest/'论文平面应力模型-参数核对与不确定项.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Saved revised files and explicit failed 20us acceptance records; not marked complete')
