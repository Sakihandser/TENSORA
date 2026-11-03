function blastStrengthMaterials(){
  const materials=new Map();
  for(const region of scene.regions || []){
    const snapshot=materialSnapshotForRegion(region);if(!snapshot)continue;
    const id=snapshot.id || region.materialId;if(!id)continue;
    if(!materials.has(id))materials.set(id,snapshot);
  }
  return [...materials.values()];
}
function syncBlastFractureControls(force=false){
 const panel=document.getElementById('blastFracturePanel');if(panel)panel.hidden=true;
 if(typeof syncBlastRockControls==='function')syncBlastRockControls(force);
}
function validateBlastFractureModel(model,settings){return BlastFracture.assertValid(model,settings);}
async function ensureBlastDamageMeshReady(payload,model,settings){validateBlastFractureModel(model,settings);return {payload,model};}
function initializeBlastFractureControls(){
 if(typeof initializeBlastRockControls==='function')initializeBlastRockControls();
 document.getElementById('blastFracture').addEventListener('change',()=>syncBlastFractureControls());
}
