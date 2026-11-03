"""Create the verified JH2 / thesis comparison PDF from saved, unfiltered results.
Run with Python containing reportlab, numpy, matplotlib, Pillow and pypdf.
The original thesis is read only; its figure crops retain their original pixels.
"""
from pathlib import Path
import sys, json, hashlib, math
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools' / 'report-python'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

REPORT = ROOT.parent / '检查报告-2026-10-28'
DATA = REPORT / 'OpenRadioss接入复算'
ASSETS = DATA / '图件'
ASSETS.mkdir(parents=True, exist_ok=True)
OUT = ROOT / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
PDF = OUT / 'JH2上游接入与论文损伤对照-2026-10-28.pdf'
KINDS = ['homogeneous', 'W45', 'W90']
NAMES = dict(homogeneous='均质板', W45='W45', W90='W90')
COMMIT = 'bad6688602d770e019b75773d2d5a48b4f9bd918'
histories, cells = {}, {}
for kind in KINDS:
    f = DATA / f'{kind}-0-0-openradioss.json'
    if not f.exists():
        raise RuntimeError(f'Calculation has not finished: {f}')
    histories[kind] = json.loads(f.read_text(encoding='utf-8'))
    if histories[kind]['metadata'].get('jh2BackendCommit') != COMMIT:
        raise RuntimeError('Unexpected material backend')
    cells[kind] = json.loads((DATA / f'{kind}-0-0-openradioss-cells.json').read_text(encoding='utf-8'))

cmap = LinearSegmentedColormap.from_list('failure_time', ['#cfe3f4','#1685b0','#073b4c','#4c9138','#f1d68c','#9f241b'])
norm = Normalize(0,80)
plt.rcParams['font.family'] = 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False

def map_on(ax, kind, time=80, binary=False):
    d = cells[kind]; n = np.array(d['nodes']); e = np.array(d['elements'])
    tri = n[e[:,:3].astype(int)-1]
    rgba = np.tile(matplotlib.colors.to_rgba('#3d4bbb' if binary else '#d5e6f5'), (len(e),1))
    mask = (e[:,4]>=0)&(e[:,4]<=time*1e-6+1e-12)
    rgba[mask] = matplotlib.colors.to_rgba('#c61a34') if binary else cmap(norm(e[mask,4]*1e6))
    ax.add_collection(PolyCollection(tri,facecolors=rgba,edgecolors='none',antialiased=False,rasterized=True))
    if kind!='homogeneous':
        theta = -np.pi/4 if kind=='W45' else np.pi/2
        v=np.array([np.cos(theta),np.sin(theta)]); w=np.array([-v[1],v[0]])
        a=np.linspace(-np.pi/2,np.pi/2,70); b=np.linspace(np.pi/2,3*np.pi/2,70)
        q=np.concatenate([.15*v+.027*(np.cos(a)[:,None]*v+np.sin(a)[:,None]*w),-.15*v+.027*(np.cos(b)[:,None]*v+np.sin(b)[:,None]*w)])
        q=np.vstack([q,q[0]]);ax.plot(*q.T,color='#686868',lw=.5)
    ax.add_patch(plt.Circle((0,0),.008,color='white',zorder=4))
    ax.set(xlim=(-.3,.3),ylim=(-.3,.3),aspect='equal');ax.axis('off')

for kind in KINDS:
    fig=plt.figure(figsize=(3,3));ax=fig.add_axes([0,0,1,1]);map_on(ax,kind,binary=kind=='homogeneous')
    fig.savefig(ASSETS/f'{kind}-80us.png',dpi=200);plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(10,3.6),layout='constrained')
for ax,kind in zip(axs,KINDS):map_on(ax,kind);ax.set_title(f'{NAMES[kind]} | 0/0 MPa',fontsize=11)
fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),ax=axs,orientation='horizontal',shrink=.6,pad=.03,label='首次 D>0.95 时刻 (μs)')
fig.savefig(ASSETS/'三模型总览.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(2,4,figsize=(10,5.6),layout='constrained')
for row,kind in enumerate(['W45','W90']):
    for col,t in enumerate([20,40,60,80]):map_on(axs[row,col],kind,t);axs[row,col].set_title(f'{kind} | {t} μs',fontsize=10)
fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),ax=axs,orientation='horizontal',shrink=.6,pad=.02,label='首次 D>0.95 时刻 (μs)')
fig.savefig(ASSETS/'异质模型时序.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(5.8,.55));fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),cax=ax,orientation='horizontal');fig.savefig(ASSETS/'时间色标.png',dpi=160,bbox_inches='tight');plt.close(fig)

# Coordinates correspond to the already visually inspected 120 dpi pages, x2.
sources = [('homogeneous','report-homogeneous-062.png',(511,122,692,303)),('W45','report-source-145.png',(169,492,424,747)),('W90','report-source-144.png',(215,582,430,796))]
for kind,file,box in sources:
    source = ROOT/'tmp'/'pdfs'/file
    target = ASSETS/f'论文-{kind}-0-0.png'
    if source.exists():
        Image.open(source).crop(tuple(2*x for x in box)).save(target)
    elif not target.exists():
        raise RuntimeError(f'Missing inspected thesis figure: {target}')

pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc'))
pdfmetrics.registerFont(TTFont('CNBold','C:/Windows/Fonts/msyhbd.ttc'))
pdfmetrics.registerFontFamily('CN',normal='CN',bold='CNBold',italic='CN',boldItalic='CNBold')
W,H=A4; M=46; CW=W-2*M
C=canvas.Canvas(str(PDF),pagesize=A4,pageCompression=1)
C.setTitle('JH2上游接入与论文损伤结果对照');C.setAuthor('TENSORA 求解复核')
navy=colors.HexColor('#17394d');grey=colors.HexColor('#51616c');line=colors.HexColor('#d9e3e9')
page=0
def start(title):
    global page
    page+=1;C.setFillColor(navy);C.setFont('CNBold',15);C.drawString(M,H-54,title)
    C.setStrokeColor(line);C.line(M,H-68,W-M,H-68)
    C.setFillColor(grey);C.setFont('CN',8);C.drawString(M,25,'2026-10-28 | OpenRadioss SIGEPS79 / TENSORA | 论文原参数')
    C.drawRightString(W-M,25,f'{page} / 7')
    return H-88
def p(text,y,size=10.2,leading=16,x=M,width=CW,gap=9):
    style=ParagraphStyle('body',fontName='CN',fontSize=size,leading=leading,textColor=navy,wordWrap='CJK')
    q=Paragraph(text,style);_,hh=q.wrap(width,H);q.drawOn(C,x,y-hh);return y-hh-gap
def table(rows,y,widths=None):
    data=[[Paragraph(str(v),ParagraphStyle('cell',fontName='CN',fontSize=9,leading=14,wordWrap='CJK')) for v in row] for row in rows]
    t=Table(data,colWidths=widths or [CW/len(rows[0])]*len(rows[0]));t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f1f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,line),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    _,hh=t.wrap(CW,H);t.drawOn(C,M,y-hh);return y-hh-13
def image(file,x,y,w,h):C.drawImage(str(file),x,y-h,width=w,height=h,preserveAspectRatio=True,anchor='c',mask='auto')
def frame(kind,t):return min(histories[kind]['history'],key=lambda f:abs(f['time']-t*1e-6))
def area(f):return sum(v['damagedArea'] for v in f['materials'].values())*1e6
def soft(kind,t):
    mat=next(m['materialNo'] for m in cells[kind]['materials'] if '砂' in m['name']);v=frame(kind,t)['materials'][str(mat)];return 100*v['damagedArea']/v['area']

y=start('JH2 上游接入与论文损伤结果对照')
y=p('本次三组计算：均质板、W45、W90；围压均为 0/0 MPa；计算到 80 μs。',y,11,18)
y=p('<b>结论：上游本构已真实接入，论文损伤范围仍未复现。</b> 现有 JH2 分支实际调用原始 OpenRadioss Fortran 材料核；均质板保留放射状主裂纹，W45/W90 仍缺少论文中的早期大面积软岩破碎。',y,11,18)
y=table([['本次确认','结果'],['真正调用上游','源码原样编译为 DLL；缺失或版本不符时报错，无本地 JH2 更新回退。'],['直接调用对照','360 步多轴压缩、卸载转拉伸、损伤及膨胀压力路径，14 个输出/状态量逐项对照。'],['最终核心验证','全套 344 项测试通过；材料及动力学专项 33 项通过。'],['整模型验证范围','仅本次三组 0/0 MPa、80 μs；其他围压输入保留，未冒充新后端的已计算结果。']],y,[115,CW-115])
y=p('<b>统计口径</b>：损伤面积为原始 TRI3 单元中 D&gt;0.95 的面积和；图中颜色表示首次越过该阈值的时间，保存间隔为 2 μs。图采用参考坐标，未对达到阈值的单元作筛除。论文原图未明确给出相同阈值，因此不计算跨方法的逐像素误差或论文损伤面积比。',y)
y=p('<b>论文依据</b>：用户提供的博士论文《基于物质点法的高地应力环境非均质岩石爆破响应及破岩调控》。均质板参考图2.13（印刷页48 / PDF第62页）；W90参考图4.16（130 / 144）；W45参考图4.17（131 / 145）。',y)
C.showPage()

y=start('三模型：相同输入条件下的 80 μs 结果')
image(ASSETS/'三模型总览.png',M,y,CW,198);y-=211
rows=[['模型','阈值损伤面积 mm²','最大损伤半径 mm','孔壁压力 MPa']]
for kind in KINDS:
    f=frame(kind,80);rows.append([NAMES[kind],f'{area(f):.1f}',f'{1000*f["damageRadius"]:.1f}',f'{f["pressure"]/1e6:.2f}'])
y=table(rows,y,[85,150,140,CW-375])
y=p('统一输入：600 × 600 mm 板、炮孔直径16 mm、装药直径10 mm；标称3 mm网格，约9.3-9.7万个TRI3单元；有限变形、平面应变、吸收外边界、冲击黏性开启。',y)
y=p('气体采用论文 PETN/JWL 与空气参数，双端敞开、有效孔长50 mm。该径向气体加储罐泄流模型沿用现有设定，尚未证明与论文的 GIMP/CPDI 气固流动等价。',y)
rows=[['主要参数','花岗岩','青砂岩'],['密度 kg/m³','2660','2340'],['输入 K / G (GPa)','25.7 / 21.9','12.67 / 9.98'],['EOS K1 / K2 / K3 (GPa)','25.7 / -4500 / 300000','同左，按论文表保留'],['直接等效 σHEL / pHEL (GPa)','4.5 / 3.7','4.5 / 3.7'],['T (MPa) / D1 / D2','54 / 0.005 / 0.7','44 / 0.005 / 0.7']]
y=table(rows,y,[185,(CW-185)/2,(CW-185)/2])
y=p('两材料均取 A=0.76、N=0.62、B=0.25、M=0.62、C=0.005、参考应变率1 s⁻¹、SFmax=0.25。论文未列出的 β 与参考长度保持0；Gf不参与该JH2损伤分支。',y,9,14)
C.showPage()

for kind,figlabel in [('homogeneous','图2.13'),('W45','图4.17'),('W90','图4.16')]:
    y=start(f'{NAMES[kind]}：论文与本次计算并排对照')
    C.setFont('CNBold',10);C.setFillColor(navy);C.drawString(M,y,'论文原图：0/0 MPa');C.drawString(M+CW/2+8,y,'本次：0/0 MPa，80 μs')
    y-=14;side=(CW-16)/2
    image(ASSETS/f'论文-{kind}-0-0.png',M,y,side,side)
    image(ASSETS/f'{kind}-80us.png',M+side+16,y,side,side);y-=side+16
    if kind!='homogeneous':image(ASSETS/'时间色标.png',M+64,y,CW-128,35);y-=46
    y=p(f'左：{figlabel}原图中对应的0/0 MPa子图，保留原图像素。右：本次原始网格的D&gt;0.95区域。两图均展示整块600 mm平板；右图白色圆孔为初始炮孔。',y,9,14)
    if kind=='homogeneous':
        y=p('<b>定性相同</b>：均呈放射状主裂纹分布。<b>主要差距</b>：论文文字描述主裂纹贯穿或接近边界；本次80 μs的最远损伤半径为191.2 mm，尚未接近300 mm边界。',y,10.5,17)
        y=p('论文图2.13未在该图标注相同的80 μs输出时刻，且颜色不是破坏时刻色标。本页只作形态参考，不能视为严格同一时刻的误差评估。',y)
    else:
        y=table([['时刻','软岩阈值损伤面积比例','总阈值损伤面积 mm²'],['20 μs',f'{soft(kind,20):.2f}%',f'{area(frame(kind,20)):.1f}'],['80 μs',f'{soft(kind,80):.2f}%',f'{area(frame(kind,80)):.1f}']],y,[85,230,CW-315])
        y=p('<b>尚未吻合</b>：论文描述弱介质在0-20 μs阶段出现大范围破碎，原图中央软岩破坏区较连续。本次仍以裂纹带和端部损伤集中为主，软岩内部保留较大未达到阈值的区域。',y,10.5,17)
        y=p('颜色可比较破坏时序趋势；论文与本程序损伤显示阈值尚未统一，不能把颜色相同直接解释为损伤数值相同。',y)
    C.showPage()

y=start('W45 / W90：本次结果的时间演化')
image(ASSETS/'异质模型时序.png',M,y,CW,300);y-=314
y=p('各列分别为20、40、60、80 μs。每张图仅显示该时刻以前首次达到D&gt;0.95的单元；使用同一色标，未删除或挑选损伤单元。灰线表示初始材料界面。',y)
y=p('上游接入后，早期软岩粉碎区不足的问题仍存在。由此不能把剩余差距归因于此前那几处本地返回映射错误，也不能据更换本构核宣称整模型已验证。',y)
y=p('接入前的W45诊断中，时间步减半对20 μs损伤面积的影响约0.26%，两级空间网格对面积的影响约26%。这是旧后端的离散诊断；新后端仍须另做网格收敛检查，本文未将旧诊断冒充本次收敛结论。',y)
C.showPage()

y=start('实现证据、适用边界与文件位置')
y=p('<b>实际调用链</b>：RockConstitutive.h → OpenRadiossJH2.h → openradioss_jh2.dll → 原始SIGEPS79。压力、拉伸截断、强度、径向返回、损伤累积及膨胀压力在上游执行；本地保留参数/张量接口、预应力参考密度初始化、有限元动力学与能量诊断。',y)
y=p('上游固定提交：'+COMMIT+'。来源为归档的OpenRadioss镜像，不是下载完整OpenRadioss程序后运行整套模型。原始文件的Git blob为5eb7ec6ab313f51bb664694cb30df915b1de5461，SHA-256与下载清单一致。',y,9,14)
y=p('源码和构建：third_party/openradioss-jh2/；脚本 scripts/build-jh2.ps1。组件采用AGPL-3.0-or-later，保留完整许可；当前未发布或推送Git。DLL缺失与版本不符均拒绝运行。',y)
y=p('<b>剩余边界</b>：本程序仍为连续TRI3有限元与简化气体耦合，未实现论文的GIMP/CPDI空间离散、碎块分离/接触和完整裂隙流动。本次上游仅使用局部损伤INLOC=0、关闭单元删除IDEL=0；非零参考长度会明确报错。',y)
y=p('<b>最新模型</b>：main分支根目录的“论文-均质板 / W45 / W90-围压组合.json”，三类各含0/0、10/5、5/10、20/20 MPa，共12个。均保存80 μs、41帧设置。只有本报告三组0/0 MPa是在本次新后端上完成的结果。',y)
y=p('<b>原始数据</b>：工作区“检查报告-2026-10-28/OpenRadioss接入复算”保存逐材料面积时程、单元首次破坏时刻、运行核心版本和模型整理清单。重新计算使用该目录的复算清单及scripts/verify-blast-cases.cjs。',y)
proof=json.loads((DATA/'运行核心版本.json').read_text(encoding='utf-8'))
y=p('本次核心SHA-256：'+proof['exe']+'<br/>本次DLL SHA-256：'+proof['dllHash'],y,8.2,13)
y=p('论文材料表：印刷页45和123（PDF第59和137页）。原图引用：图2.13、图4.16、图4.17；本报告仅为用户提供论文的内部数值对照。',y,9,14)
C.showPage();C.save()
print(str(PDF))
