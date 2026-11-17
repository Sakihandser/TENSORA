// EOS registry for the 2D OpenCourant blast chain: products as /MAT/JWL or an ideal gas
// (/EOS/POLYNOMIAL), gap gas as an ideal gas. Evaluation is done by OpenCourant itself.
(function(root){
 const names={0:'理想气体',1:'JWL'},ids=[0],productIds=[1,0];
 const help={0:'常比热比理想气体（OpenCourant /EOS/POLYNOMIAL，C4 = C5 = γ − 1）。',1:'JWL 状态方程（OpenCourant /MAT/JWL），在炮孔中心点起爆，适用于爆轰产物膨胀。'};
 function card(s,prefix){return {model:s[prefix==='product'?'productEOS':'airEOS']??0,gamma:s[prefix+'Gamma']};}
 function constraints(s){const errors=[],warnings=[];if(s.sourceMode!==1)return {errors,warnings};
  for(const [prefix,scope,allowed]of [['product','爆轰产物',productIds],['air','间隙气体',ids]]){
   const c=card(s,prefix);
   if(!allowed.includes(c.model)){errors.push({scope,message:'请选择支持的状态方程（产物：JWL 或理想气体；间隙气体：理想气体）。'});continue;}
   if(c.model===0&&!(c.gamma>1&&c.gamma<=10))errors.push({scope,message:'比热比须大于1且不超过10。'});
  }return {errors,warnings};
 }
 const api={names,ids,productIds,help,card,constraints};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.GasEOS=api;
})(typeof window!=='undefined'?window:globalThis);
