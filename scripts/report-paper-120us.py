"""Final damage only: 12 newly computed scenes, original thesis figure crops."""
from pathlib import Path
import json, sys, math, hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.tools/report-python'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from PIL import Image
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib import colors
PAPER=ROOT.parent/'论文复现'; DATA=PAPER/'复算-0.12ms-2026-10-28'; ASSET=DATA/'图件';ASSET.mkdir(exist_ok=True)
PDF=PAPER/'论文复现-0.12ms最终损伤对比-2026-10-28.pdf'
ORDER=['0-0','10-5','5-10','20-20'];KINDS=['均质板','W45','W90']
NAMES=[f'论文-{k}-{c}' for k in KINDS for c in ORDER]
PREVIEW='--preview' in sys.argv
if PREVIEW:
 PDF=DATA/'排版预检.pdf'
 NAMES=[n for n in NAMES if (DATA/(n+'.json')).exists()]
results={}
for name in NAMES:
 f=DATA/(name+'.json')
 if not f.exists(): raise RuntimeError('Calculation incomplete: '+name)
 r=json.loads(f.read_text(encoding='utf8'));assert abs(r['final']['time']-.00012)<1e-13
 assert r['metadata']['jh2Backend']=='OpenRadioss SIGEPS79'
 assert r['metadata']['gasBackend']=='LANL Singularity-EOS'
 assert all(r['checks'].values());results[name]=r
verdict=json.loads((DATA/'最终损伤判读.json').read_text(encoding='utf8')) if (DATA/'最终损伤判读.json').exists() else {'overall':'计算进行中。此文件仅供排版预检，不是完整复算结论。','cases':{n:'待所有工况完成后统一判读。' for n in NAMES}}
if not PREVIEW:assert (DATA/'最终损伤判读.json').exists()

blue='#3d4bbb';red='#c51c38'
cmap=LinearSegmentedColormap.from_list('D',[blue,'#1b9ccd','#58b56a','#f6d559',red])
plt.rcParams['font.family']='Microsoft YaHei';plt.rcParams['axes.unicode_minus']=False
for name in NAMES:
 d=json.loads((DATA/(name+'-cells.json')).read_text(encoding='utf8'));n=np.asarray(d['nodes']);e=np.asarray(d['elements'],dtype=float);tri=n[e[:,:3].astype(int)-1]
 for binary in [False,True]:
  fig=plt.figure(figsize=(3.5,3.5));ax=fig.add_axes([0,0,1,1])
  rgba=np.where((e[:,3]>.95)[:,None],matplotlib.colors.to_rgba(red),matplotlib.colors.to_rgba(blue)) if binary else cmap(np.clip(e[:,3],0,1))
  ax.add_collection(PolyCollection(tri,facecolors=rgba,edgecolors='none',antialiased=False))
  ax.add_patch(plt.Circle((0,0),.008,color='white'));ax.set(xlim=(-.3,.3),ylim=(-.3,.3),aspect='equal');ax.axis('off')
  fig.savefig(ASSET/(name+('-binary.png' if binary else '-D.png')),dpi=220);plt.close(fig)
fig=plt.figure(figsize=(6,.55));ax=fig.add_axes([.03,.55,.94,.32]);cb=fig.colorbar(matplotlib.cm.ScalarMappable(norm=Normalize(0,1),cmap=cmap),cax=ax,orientation='horizontal');cb.set_ticks([0,.25,.5,.75,1]);cb.ax.tick_params(labelsize=9);fig.savefig(ASSET/'D-colorbar.png',dpi=170);plt.close(fig)

# Crop numerical subpanels only; coordinates were inspected on 1.6x renders.
boxes={
 '论文-均质板-0-0':(62,(492,117,664,289)),
 '论文-均质板-5-10':(62,(492,303,664,475)),
 '论文-均质板-20-20':(62,(492,489,664,661)),
 '论文-W45-0-0':(140,(257,114,413,269)),
 '论文-W45-20-20':(140,(590,114,745,269)),
 '论文-W45-10-5':(140,(257,295,413,450)),
 '论文-W45-5-10':(140,(590,295,745,450)),
 '论文-W90-0-0':(140,(257,478,413,633)),
 '论文-W90-20-20':(140,(590,478,745,633)),
 '论文-W90-10-5':(140,(257,659,413,816)),
 '论文-W90-5-10':(140,(590,659,745,816))}
doc=pdfium.PdfDocument(next(PAPER.glob('*终稿*.pdf')));pages={};crop_records={}
for name,(p,b) in boxes.items():
 if p not in pages:pages[p]=doc[p-1].render(scale=4).to_pil()
 # Find the blue panel perimeter within a small, visually selected window.
 # This retains the full square and avoids including the neighboring experiment.
 roi=tuple(round((x+(-10 if i<2 else 10))*2.5) for i,x in enumerate(b))
 a=np.asarray(pages[p].crop(roi).convert('RGB')).astype(int)
 mask=(a[:,:,2]>a[:,:,0]+50)&(a[:,:,2]>a[:,:,1]+30)&(a[:,:,0]<180)
 yy,xx=np.where(mask);assert len(xx)>1000
 exact=(roi[0]+int(xx.min()),roi[1]+int(yy.min()),roi[0]+int(xx.max())+1,roi[1]+int(yy.max())+1)
 assert .96<(exact[2]-exact[0])/(exact[3]-exact[1])<1.04
 pages[p].crop(exact).save(ASSET/(name+'-paper.png'))
 crop_records[name]={'pdfPage':p,'renderScale':4,'cropBoxPixels':exact}
(DATA/'论文原图裁剪坐标.json').write_text(json.dumps(crop_records,ensure_ascii=False,indent=2),encoding='utf8')

pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc'));pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/msyhbd.ttc'))
pdfmetrics.registerFontFamily('CN',normal='CN',bold='CNB',italic='CN',boldItalic='CNB')
W,H=landscape(A4);M=38;CW=W-2*M;navy=colors.HexColor('#163b50');grey=colors.HexColor('#526574');line=colors.HexColor('#d3dfe7')
C=canvas.Canvas(str(PDF),pagesize=(W,H));C.setTitle('论文复现：0.12 ms 最终损伤对比');C.setAuthor('TENSORA 论文复算');page=0
def start(title):
 global page
 page+=1;C.setFillColor(navy);C.setFont('CNB',17);C.drawString(M,H-40,title);C.setStrokeColor(line);C.line(M,H-53,W-M,H-53)
 C.setFillColor(grey);C.setFont('CN',8);C.drawString(M,19,'2026-10-28 | main 工作区当前核心 | 本次终止时刻 0.120000 ms');C.drawRightString(W-M,19,f'{page} / {len(NAMES)+3}')
 return H-70
def p(text,y,size=10,leading=16,x=M,width=CW):
 q=Paragraph(text,ParagraphStyle('p',fontName='CN',fontSize=size,leading=leading,textColor=navy,wordWrap='CJK'));_,h=q.wrap(width,H);q.drawOn(C,x,y-h);return y-h-8
def table(rows,y,widths,size=9):
 s=ParagraphStyle('cell',fontName='CN',fontSize=size,leading=size+4,textColor=navy,wordWrap='CJK')
 t=Table([[Paragraph(str(x),s) for x in row] for row in rows],colWidths=widths)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f0f5')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,line),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));_,h=t.wrap(CW,H);t.drawOn(C,M,y-h);return y-h-10
def img(file,x,top,w,h):C.drawImage(str(file),x,top-h,width=w,height=h,preserveAspectRatio=True,anchor='c',mask='auto')
def stats(r):
 v=r['final']['materials'];a=sum(x['damagedArea'] for x in v.values())*1e6;integ=sum(x['integratedDamage'] for x in v.values())*1e6
 soft=next((str(m['materialNo']) for m in r['materials'] if m['density']==2340),None)
 return a,integ,1000*r['final']['damageRadius'],100*v[soft]['damagedArea']/v[soft]['area'] if soft else None

y=start('论文复现 | 0.12 ms 最终损伤对比')
y=p(('排版预检：仅包含当前已完成的 '+str(len(NAMES))+' 组，完整计算正在进行。' if PREVIEW else '均质板、W45、W90 × 0/0、10/5、5/10、20/20 MPa，共 12 组。本次均重新计算至 120 μs，仅展示最终损伤。'),y,12,19)
y=p('<b>本次结论：</b>'+verdict['overall'],y,11.5,18)
y=p('<b>判定依据</b>：比较主裂纹方向与长度、损伤区范围、弱夹层是否连续破碎，以及围压抑制趋势。论文未给出原始损伤场和相同显示阈值，不提供没有依据的像素误差或“相似度百分比”。',y,11,18)
y=p('<b>时间可比性限制</b>：本次输出严格为 0.12 ms。论文图 2.13、图 4.13 未注明该最终图的输出时刻；图 4.16、4.17 的颜色表示 0-80 μs 的破坏时刻。因此本报告是“本次 0.12 ms 对论文最终图”的形态比较，无法确认严格同一时刻复现。',y,11,18)
y=p('<b>图像口径</b>：每个工况依次列出论文原始模拟子图、本次 D&gt;0.95 区域、本次原始 D 云图。统一展示初始坐标下 600 × 600 mm 全板，未平滑、删选、延长或人工绘制裂纹。D&gt;0.95 是本报告固定的辅助显示口径，不能推定为论文原图使用的阈值。',y,11,18)
y=p('<b>参数结论</b>：现有 12 个模型的论文表列 JH2 参数与 PETN/JWL 主要参数核对通过；“材料参数相同”不能等同“完整模型一致”。现有 TRI3 网格、二维运动学、气固耦合及轴向泄流与论文 MPM 模型存在差异，见下一页。',y,11,18)
y=p('论文依据：图 2.13（印刷页 48 / PDF 第 62 页）、图 4.13（126 / 140）。均质板 10/5 MPa 未在图 2.13 中给出对应子图；本报告保留该工况复算结果，明确标记无直接参照。',y,10,16)
y=p('逐工况原始损伤、参数、后端标识、实际步长和二进制哈希保存在“复算-0.12ms-2026-10-28”资料目录。每个对比页给出对应的定性观察。',y,10,16)
C.showPage()

y=start('参数检查 | 表列数值通过，整模型存在差异')
rows=[['检查项','论文','本次输入 / 核查结果'],
 ['几何与围压','600 × 600 mm；孔径 16 mm；装药径 10 mm；四组围压','一致；W45/W90 中心弱夹层沿既有几何；按 X/Y 对应围压'],
 ['密度 ρ / K / G','花岗岩 2660 / 25.7 / 21.9；青砂岩 2340 / 12.67 / 9.98','单位 kg/m³、GPa、GPa；逐材料副本核对通过'],
 ['JH2 强度 / 归一化','A=0.76, N=0.62, B=0.25, M=0.62, C=0.005；参考应变率=1 s^-1','σHEL=4.5 GPa；pHEL=3.7 GPa；T=54 / 44 MPa；均一致'],
 ['JH2 损伤 / EOS','D1=0.005, D2=0.7, SFmax=0.25；K1=25.7, K2=-4500, K3=300000 GPa','两材料均按原表保留；青砂岩 K=12.67 与 K1=25.7 不相同，未调参合并'],
 ['PETN / JWL','ρ=1320 kg/m³, Vd=6690 m/s；A=586, B=21.60 GPa；R1=5.81, R2=1.77, ω=0.282','一致；E0=7.38×10<super>9</super> J/m³ → 5,590,909.09 J/kg；未使用补充图 TNT'],
 ['空气','c4=c5=0.4；E=250 kJ/m³ → 初压 0.1 MPa','理想气体 γ=1.4、p0=0.1 MPa；ρ=1.25 来自补充图，论文正文未单列'],
 ['离散尺寸','均质：背景网格 / 岩石离散约 2 mm；非均质：背景网格 1.5 mm','现有约 3 mm TRI3；本次沿用网格，不是论文空间离散'],
 ['厚度与气固流动','均质数值切片 2 mm；非均质三维模型 1:1','二维平面应变；径向气体 + 双端泄流，有效孔长 50 mm；不保证等价'],
 ['未列出的参数 / 算法','表中未提供 β 和非局部参考长度；MPM / GIMP / CPDI','β=0、参考长度=0 沿用；冲击黏性开启、吸收边界、先静力平衡'],
 ['真实执行后端','论文自主 MPM 程序','OpenRadioss SIGEPS79 本构核 + LANL Singularity-EOS；动力学仍为本程序']]
y=table(rows,y,[118,306,CW-424],8.4)
y=p('材料依据：表 2.4 / 2.5（PDF 第 59 页）、表 4.3（第 137 页）；模型说明：第 57-59、122、136 页。现有圆端夹层直线段为 300 mm、宽 54 mm；图 4.1 对应尺寸已目视核查。',y,8.6,13)
C.showPage()

y=start('12 组复算结果 | 0.12 ms 数值统计')
rows=[['工况 X/Y (MPa)','D>0.95 面积 (mm²)','积分损伤 ∫D dA (mm²)','最远阈值损伤半径 (mm)','软岩阈值损伤面积比']]
for name in NAMES:
 a,integ,r,s=stats(results[name]);rows.append([name.removeprefix('论文-'),f'{a:.1f}',f'{integ:.1f}',f'{r:.1f}',f'{s:.2f}%' if s is not None else '-'])
y=table(rows,y,[145,145,170,170,CW-630],8.8)
y=p('统计来自原始三角形单元面积。半径取 D>0.95 单元初始质心到炮孔中心的最远距离；它不是单条裂纹长度。软岩比例的分母为该工况青砂岩总面积。上述统计仅描述本次计算，不代表论文图像的量化误差。',y,9,14)
audit=json.loads((DATA/'参数与运行审计.json').read_text(encoding='utf8'))
y=p('可追溯性：12 组均确认最终时刻、最终损伤有限且位于 [0,1]、相对初始损伤不回退、最终各单元应力应变有限。仅保存初始和最终两帧；本报告没有验证全过程稳定性或网格收敛。原场景文件未改写。',y,9,14)
y=p('核心 SHA-256：'+audit['binaries']['TensoraCore.exe']+'<br/>上游源码校验：JH2 18 个文件、EOS 12 个文件通过；参数 / 单位接入专项 8 项测试通过。后端提交号和三个运行二进制的哈希见资料目录“参数与运行审计.json”。',y,8.2,12)
C.showPage()

for name in NAMES:
 r=results[name];a,integ,rad,soft=stats(r);kind=name.split('-')[1];case='-'.join(name.split('-')[2:]);y=start(name.removeprefix('论文-')+' | 最终损伤')
 side=(CW-32)/3;xs=[M,M+side+16,M+2*(side+16)]
 for x,t in zip(xs,['论文数值模拟原图','本次：D > 0.95','本次：原始 D（0-1）']):
  C.setFont('CNB',11);C.setFillColor(navy);C.drawString(x,y-3,t)
 top=y-18
 if name in boxes:img(ASSET/(name+'-paper.png'),xs[0],top,side,side)
 else:
  C.setFillColor(colors.HexColor('#eef2f5'));C.rect(xs[0],top-side,side,side,fill=1,stroke=0)
  p('图 2.13 未展示<br/>均质板 10/5 MPa<br/>不能以 5/10 MPa 子图替代。',top-70,12,22,x=xs[0]+22,width=side-44)
 img(ASSET/(name+'-binary.png'),xs[1],top,side,side);img(ASSET/(name+'-D.png'),xs[2],top,side,side)
 img(ASSET/'D-colorbar.png',xs[2],top-side-6,side,30)
 y=top-side-44
 y=p(('论文：图 2.13，PDF 第 62 页。' if kind=='均质板' else '论文：图 4.13，PDF 第 140 页。')+' 本次两图均为 0.120000 ms；论文最终图的时刻及损伤显示阈值未注明。整板同尺度，白色为初始炮孔。',y,9.3,15)
 y=p(f'<b>本次统计</b>：D&gt;0.95 面积 {a:.1f} mm²；积分损伤 {integ:.1f} mm²；最远阈值损伤半径 {rad:.1f} mm。'+(f'青砂岩达到阈值的面积比例 {soft:.2f}%。' if soft is not None else ''),y,10,16)
 y=p('<b>形态观察：</b>'+verdict['cases'][name],y,10,16)
 actual=r['metadata']['frames'][-1]['actualSteps']
 y=p(f'节点 / 单元：{r["nodes"]:,} / {r["elements"]:,}；实际动力步数 {int(actual):,}（含自适应缩步）；运行 {r["seconds"]:.1f} s。原始数据：复算资料目录 / {name}-cells.json。',y,8.5,14)
 C.showPage()
C.save();print(PDF)
