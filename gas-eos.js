// Registry only: EOS evaluation is performed exclusively by the upstream native runtime.
(function(root){
 const names={0:'理想气体',1:'JWL',3:'Noble–Abel',4:'Stiffened Gas'},ids=[0,3,4],productIds=[1,0,3,4],extraKeys=['Covolume','PressureOffset','EnergyShift','Attraction'];
 const help={0:'常比热比理想气体状态方程。',1:'JWL 状态方程，适用于已反应爆轰产物的膨胀。',3:'Noble–Abel 状态方程，考虑余容积；须满足 bρ < 1。',4:'Stiffened Gas 状态方程，以压力偏置描述介质刚度。'};
 function active(key,model){return key==='Covolume'&&model===3||key==='PressureOffset'&&model===4||key==='EnergyShift'&&(model===3||model===4);}
 function card(s,prefix){return {model:s[prefix==='product'?'productEOS':'airEOS']??0,gamma:s[prefix+'Gamma'],covolume:s[prefix+'Covolume']||0,pressureOffset:s[prefix+'PressureOffset']||0,energyShift:s[prefix+'EnergyShift']||0};}
 function constraints(s){const errors=[],warnings=[];if(s.sourceMode!==1)return {errors,warnings};
  for(const [prefix,scope,allowed]of [['product','爆轰产物',productIds],['air','间隙气体',ids]]){
   const c=card(s,prefix),rho=s[prefix+'Density'];
   if(!allowed.includes(c.model)){errors.push({scope,message:'请选择支持的状态方程。'});continue;}
   if(c.model!==1&&!(c.gamma>1&&c.gamma<=10))errors.push({scope,message:'比热比须大于1且不超过10。'});
   if(c.model===3&&!(Number.isFinite(c.covolume)&&c.covolume>=0&&c.covolume*rho<1))errors.push({scope,message:'余容积必须非负，且 bρ < 1。'});
   if((c.model===3||c.model===4)&&!(Number.isFinite(c.energyShift)&&c.energyShift>=0))errors.push({scope,message:'能量偏移须为非负有限值。'});
   if(c.model===4&&!(Number.isFinite(c.pressureOffset)&&c.pressureOffset>=0))errors.push({scope,message:'压力偏置须为非负有限值。'});
   if(prefix==='product'&&(c.model===3||c.model===4)&&!(s.productEnergy>c.energyShift&&(c.model!==4||rho*(s.productEnergy-c.energyShift)>c.pressureOffset)))errors.push({scope,message:'初始比内能不足以形成正温度状态，请检查能量偏移和压力偏置。'});
   if((c.model===3||c.model===4)&&s.ventEnds>0)errors.push({scope,message:'此状态方程当前要求炮孔轴向两端封堵。'});
  }return {errors,warnings};
 }
 const api={names,ids,productIds,extraKeys,help,active,card,constraints};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GasEOS=api;
})(typeof window!=='undefined'?window:globalThis);
