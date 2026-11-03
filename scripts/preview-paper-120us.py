from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.tools/report-python'))
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
BASE=ROOT.parent/'论文复现/复算-0.12ms-2026-10-28'
plt.rcParams['font.family']='Microsoft YaHei'
fig,axs=plt.subplots(3,4,figsize=(13,10),layout='constrained')
for row,kind in enumerate(['均质板','W45','W90']):
 for col,case in enumerate(['0-0','10-5','5-10','20-20']):
  ax=axs[row,col];f=BASE/f'论文-{kind}-{case}-cells.json';ax.set_title(f'{kind} | {case} MPa',fontsize=11)
  if f.exists():
   d=json.loads(f.read_text(encoding='utf8'));n=np.array(d['nodes']);e=np.array(d['elements']);tri=n[e[:,:3].astype(int)-1]
   rgba=np.where((e[:,3]>.95)[:,None],matplotlib.colors.to_rgba('#c51c38'),matplotlib.colors.to_rgba('#3d4bbb'))
   ax.add_collection(PolyCollection(tri,facecolors=rgba,edgecolors='none',antialiased=False));ax.add_patch(plt.Circle((0,0),.008,color='white'))
  else:ax.text(0,0,'计算中',ha='center',va='center',color='gray')
  ax.set(xlim=(-.3,.3),ylim=(-.3,.3),aspect='equal');ax.axis('off')
fig.suptitle('0.12 ms | D > 0.95 | 原始网格',fontsize=16)
fig.savefig(BASE/'复算进度损伤总览.png',dpi=140);print(BASE/'复算进度损伤总览.png')
