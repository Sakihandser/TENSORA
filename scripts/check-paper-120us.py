"""Verify source immutability, runtime identity, and saved final damage statistics."""
from pathlib import Path
import json,hashlib,math,sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'论文复现/复算-0.12ms-2026-10-28'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
audits=[json.loads(f.read_text(encoding='utf8')) for f in BASE.glob('参数与运行审计*.json')]
binary=audits[0]['binaries']
assert all(a['binaries']==binary for a in audits)
assert {k:sha(ROOT/'TensoraCore/x64/Release'/k) for k in binary}==binary
records=[]
for kind in ['均质板','W45','W90']:
 for case in ['0-0','10-5','5-10','20-20']:
  name=f'论文-{kind}-{case}';f=BASE/(name+'.json')
  if '--partial' in sys.argv and not f.exists():continue
  r=json.loads(f.read_text(encoding='utf8'));assert sha(Path(r['source']))==r['sourceHash']
  d=json.loads((BASE/(name+'-cells.json')).read_text(encoding='utf8'));assert abs(d['time']-.00012)<1e-13
  assert len(d['nodes'])==r['nodes'] and len(d['elements'])==r['elements'];assert all(r['checks'].values())
  fr=r['metadata']['frames'][-1];assert fr['minimumJacobian']>0 and fr['actualSteps']>0 and abs(fr['time']-.00012)<1e-13
  for e in d['elements']:assert 0<=e[3]<=1 and math.isfinite(e[3])
  computed={}
  for e in d['elements']:
   a,b,c=(d['nodes'][int(i)-1] for i in e[:3]);area=((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
   assert area>0
   m=computed.setdefault(str(int(e[4])),{'area':0.,'damagedArea':0.,'integratedDamage':0.})
   m['area']+=area;m['damagedArea']+=area*(e[3]>.95);m['integratedDamage']+=area*e[3]
  for mat,v in computed.items():
   for k,value in v.items():assert math.isclose(value,r['final']['materials'][mat][k],rel_tol=1e-8,abs_tol=1e-12),(name,k,value,r['final']['materials'][mat][k])
  records.append({'case':name,'sourceHash':r['sourceHash'],'resultHash':sha(f),'damageFileHash':sha(BASE/(name+'-cells.json')),'actualSteps':fr['actualSteps'],'minimumJacobian':fr['minimumJacobian'],'passed':True})
out={'complete':len(records)==12,'cases':records,'runtimeHashes':binary,'originalScenesUnchanged':True,'recomputedAreaStatisticsAgree':True,'scope':'Final saved fields only; no assertion of full-history stability or grid convergence.'}
(BASE/('结果复核-进行中.json' if '--partial' in sys.argv else '结果复核.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('Verified',len(records),'cases; sources unchanged; runtime hashes match; final damage and area statistics agree.')
