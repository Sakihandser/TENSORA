// Fluid material library for the fluid–structure interaction workspace.
// Records are plain property sets passed to SU2 (density, viscosity and, for
// gases, the ideal-gas constants); the library itself evaluates nothing.
(function(root,factory){
  if(typeof module==="object"&&module.exports)module.exports=factory();
  else root.FluidLibrary=factory();
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  const MODELS=["incompressible","idealgas"];
  const CATEGORIES=["liquid","gas"];
  // Field: [unit label, min, max, required for]
  const FIELDS={
    density:["kg/m³",1e-6,1e6,"all"],
    viscosity:["Pa·s",0,1e6,"all"],
    bulkModulus:["Pa",1,1e13,"optional"],
    soundSpeed:["m/s",1,1e5,"optional"],
    gamma:["1",1.0001,3,"idealgas"],
    gasConstant:["J/(kg·K)",1,1e6,"idealgas"],
    temperature:["K",1,1e5,"idealgas"]
  };
  function number(raw,key,required){
    const value=raw[key];
    if(value===null||value===undefined||value===""){
      if(required)throw new Error(`Invalid fluid parameter: ${key}`);
      return null;
    }
    const v=Number(value),[,min,max]=FIELDS[key];
    if(!Number.isFinite(v)||v<min||v>max)throw new Error(`Invalid fluid parameter: ${key}`);
    return v;
  }
  function entry(raw){
    if(!raw||typeof raw!=="object")throw new Error("Invalid fluid record.");
    const id=String(raw.id||""),name=String(raw.name||"").trim();
    if(!/^[a-zA-Z0-9_-]{1,100}$/.test(id)||!name||name.length>160)throw new Error("Invalid fluid ID/name.");
    const model=MODELS.includes(raw.model)?raw.model:"incompressible";
    const category=CATEGORIES.includes(raw.category)?raw.category:(model==="idealgas"?"gas":"liquid");
    const gas=model==="idealgas";
    const color=/^#[0-9a-fA-F]{6}$/.test(String(raw.color||""))?String(raw.color):(category==="gas"?"#cfe8f3":"#7fb8d8");
    return {id,name,category,model,
      density:number(raw,"density",true),viscosity:number(raw,"viscosity",true),
      bulkModulus:number(raw,"bulkModulus",false),soundSpeed:number(raw,"soundSpeed",false),
      gamma:gas?number(raw,"gamma",true):null,gasConstant:gas?number(raw,"gasConstant",true):null,temperature:gas?number(raw,"temperature",true):null,
      color,notes:String(raw.notes||"").slice(0,12000),source:String(raw.source||"").slice(0,2000)};
  }
  function normalize(payload){
    if(!payload||!Array.isArray(payload.fluids)||payload.fluids.length>500||!Number.isInteger(payload.revision)||payload.revision<0)throw new Error("Invalid fluid library.");
    const fluids=payload.fluids.map(entry);
    if(new Set(fluids.map(e=>e.id)).size!==fluids.length)throw new Error("Duplicate fluid IDs.");
    return {version:1,revision:payload.revision,fluids};
  }
  // One-line summary of the stored properties for lists and run reports.
  function describe(f){
    const parts=[f.model==="idealgas"?"理想气体（可压缩）":"不可压缩",`ρ ${f.density} kg/m³`,`μ ${Number(f.viscosity).toExponential(3)} Pa·s`];
    if(f.model==="idealgas")parts.push(`γ ${f.gamma}`,`R ${f.gasConstant} J/(kg·K)`,`T ${f.temperature} K`);
    return parts.join(" · ");
  }
  function forModel(records,fluid){
    return fluid?[fluid,...records.filter(record=>record.id!==fluid.id)]:records;
  }
  return {MODELS,CATEGORIES,FIELDS,entry,normalize,describe,forModel};
});
