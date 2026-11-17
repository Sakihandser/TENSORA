// Materials assigned to regions, used by the rock-card and compatibility panels.
// Damage is part of the selected OpenCourant constitutive law; there is no separate damage switch.
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
 if(typeof syncBlastRockControls==='function')syncBlastRockControls(force);
}
function initializeBlastFractureControls(){
 if(typeof initializeBlastRockControls==='function')initializeBlastRockControls();
}
