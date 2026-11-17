(function(){
  const ids=new WeakMap();

  window.fetchSpecialtyRun=async function(controller,url,options){
    const response=await fetch(url,{...options,signal:controller.signal});
    const id=response.headers.get('X-Specialty-Run-Id');
    if(id)ids.set(controller,id);
    return response;
  };

  window.cancelSpecialtyRun=async function(controller,button,report){
    if(!controller)return;
    const id=ids.get(controller);
    if(!id){controller.abort();return;}
    button.disabled=true;
    try{
      const response=await fetch(`./api/specialty-runs/${id}/cancel`,{method:'POST',signal:controller.signal});
      if(!response.ok)throw Error(response.statusText);
    }catch(error){
      if(!controller.signal.aborted&&button.disabled){
        button.disabled=false;
        report(error.message);
      }
    }
  };
})();
