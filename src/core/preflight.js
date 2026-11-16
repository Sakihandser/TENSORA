// "计算前检查" panel and run gate shared by every calculation page. Findings
// come from CalcRules (calculation-rules.js) or page-specific collectors and
// carry Chinese and English text, so the panel follows the interface language.
(function(){
  'use strict';
  const english=()=>window.femI18n?.language==='en';
  const text=finding=>english()?finding.en:finding.zh;
  const L={
    title:['计算前检查','Pre-run check'],parameters:['参数检查','Parameter check'],
    ok:['未发现问题，可以计算。','No issues found; ready to run.'],
    errors:['项必须处理','must be fixed'],warnings:['条提醒','warnings'],tips:['条建议','tips'],
    locate:['定位','Locate'],
    error:['必须处理','Must fix'],warning:['提醒','Warning'],tip:['建议','Tip'],
    blockedTitle:['暂时无法计算','Cannot run yet'],
    blockedText:['请先处理以下问题：','Fix the following first:'],
    confirmTitle:['确认继续计算？','Run anyway?'],
    confirmText:['以下提醒可能导致结果错误或难以收敛：','These warnings may make the results wrong or hard to converge:'],
    proceed:['仍然计算','Run anyway'],back:['返回修改','Go back'],close:['关闭','Close'],
    collapse:['收起建议','Hide tips'],expand:['显示建议','Show tips']
  };
  const t=key=>L[key][english()?1:0];
  const plural=(key,n)=>english()&&n===1?t(key).replace(/s$/,''):t(key);
  const panels=new Set();
  const acknowledged=new Map();

  function locate(target){
    if(!target)return;
    if(target.material&&typeof window.openMaterialForEditing==='function'){window.openMaterialForEditing(target.material);return;}
    if(target.page&&typeof window.setPage==='function'&&target.page!==window.currentPageKey?.())window.setPage(target.page);
    if(target.focus)setTimeout(()=>{
      const el=document.getElementById(target.focus);
      if(!el)return;
      el.scrollIntoView({block:'center',behavior:'smooth'});
      el.focus({preventScroll:true});
      const box=el.closest('label')||el;
      box.classList.remove('preflight-flash');void box.offsetWidth;box.classList.add('preflight-flash');
    },50);
  }

  function listItem(finding){
    const li=document.createElement('li');li.className=`preflight-item preflight-${finding.level}`;
    const badge=document.createElement('span');badge.className='preflight-badge';badge.textContent=t(finding.level);
    const body=document.createElement('span');body.className='preflight-text';body.textContent=text(finding);
    li.append(badge,body);
    if(finding.target){
      const button=document.createElement('button');button.type='button';button.className='preflight-locate';button.textContent=t('locate');
      button.addEventListener('click',()=>locate(finding.target));
      li.append(button);
    }
    return li;
  }

  // Renders findings into `host` (an element marked data-preflight). Returns the counts.
  function render(host,findings){
    if(!host)return {error:0,warning:0,tip:0};
    const list=window.CalcRules.unique(findings||[]),count=window.CalcRules.summarize(list);
    host._preflight=list;panels.add(host);
    host.replaceChildren();
    host.classList.add('preflight-panel');
    host.dataset.state=count.error?'error':count.warning?'warning':'ok';
    const head=document.createElement('div');head.className='preflight-head';
    const title=document.createElement('strong');title.textContent=t(host.dataset.kind==='parameters'?'parameters':'title');
    const summary=document.createElement('span');summary.className='preflight-summary';
    summary.textContent=!count.error&&!count.warning&&!count.tip?t('ok')
      :[count.error?`${count.error} ${t('errors')}`:'',count.warning?`${count.warning} ${plural('warnings',count.warning)}`:'',count.tip?`${count.tip} ${plural('tips',count.tip)}`:''].filter(Boolean).join(' · ');
    head.append(title,summary);
    host.append(head);
    const ordered=[...list.filter(f=>f.level==='error'),...list.filter(f=>f.level==='warning')];
    const tips=list.filter(f=>f.level==='tip');
    if(ordered.length){const ul=document.createElement('ul');ul.className='preflight-list';ul.append(...ordered.map(listItem));host.append(ul);}
    if(tips.length){
      const details=document.createElement('details');details.className='preflight-tips';details.open=host.dataset.tipsOpen!=='false';
      const summaryTips=document.createElement('summary');summaryTips.textContent=english()?`Tips (${tips.length})`:`建议（${tips.length}）`;
      details.addEventListener('toggle',()=>{host.dataset.tipsOpen=String(details.open);});
      const ul=document.createElement('ul');ul.className='preflight-list';ul.append(...tips.map(listItem));
      details.append(summaryTips,ul);host.append(details);
    }
    return count;
  }

  let dialog=null;
  function ensureDialog(){
    if(dialog)return dialog;
    dialog=document.createElement('dialog');dialog.className='preflight-dialog';dialog.id='preflightDialog';
    document.body.append(dialog);
    return dialog;
  }
  // Resolves true when the run may start. Errors always stop the run; warnings
  // ask once per distinct set (per `key`), so repeated runs are not interrupted.
  function gate(findings,key='default'){
    const list=window.CalcRules.unique(findings||[]);
    const errors=list.filter(f=>f.level==='error'),warnings=list.filter(f=>f.level==='warning');
    if(!errors.length&&!warnings.length)return Promise.resolve(true);
    const signature=warnings.map(f=>f.code+f.zh).join('|');
    if(!errors.length&&acknowledged.get(key)===signature)return Promise.resolve(true);
    const d=ensureDialog();
    if(!d.showModal){
      if(errors.length){window.alert(errors.map(text).join('\n'));return Promise.resolve(false);}
      const ok=window.confirm(warnings.map(text).join('\n'));if(ok)acknowledged.set(key,signature);return Promise.resolve(ok);
    }
    return new Promise(resolve=>{
      d.replaceChildren();
      const h=document.createElement('h2');h.textContent=errors.length?t('blockedTitle'):t('confirmTitle');
      const p=document.createElement('p');p.textContent=errors.length?t('blockedText'):t('confirmText');
      const ul=document.createElement('ul');ul.className='preflight-list';
      ul.append(...(errors.length?errors:warnings).map(f=>{
        const li=listItem(f);
        li.querySelector('.preflight-locate')?.addEventListener('click',()=>{d.close();resolve(false);});
        return li;
      }));
      const actions=document.createElement('div');actions.className='preflight-actions';
      const finish=value=>{d.close();resolve(value);};
      if(errors.length){
        const close=document.createElement('button');close.type='button';close.textContent=t('close');close.addEventListener('click',()=>finish(false));
        actions.append(close);
      }else{
        const back=document.createElement('button');back.type='button';back.textContent=t('back');back.addEventListener('click',()=>finish(false));
        const go=document.createElement('button');go.type='button';go.className='preflight-proceed';go.textContent=t('proceed');
        go.addEventListener('click',()=>{acknowledged.set(key,signature);finish(true);});
        actions.append(back,go);
      }
      d.append(h,p,ul,actions);
      d.addEventListener('cancel',()=>resolve(false),{once:true});
      d.showModal();
      (d.querySelector('.preflight-proceed')||d.querySelector('button'))?.focus();
    });
  }

  // Re-run `refresh` (debounced) when any control inside `root` changes.
  function watch(root,refresh,delay=250){
    if(!root)return;
    let timer=null;
    const schedule=()=>{clearTimeout(timer);timer=setTimeout(refresh,delay);};
    root.addEventListener('input',schedule);root.addEventListener('change',schedule);
    return schedule;
  }

  // Puts the gate in front of an existing run button without touching its handler:
  // a capture listener holds the click, and replays it once the checks allow the run.
  function guardButton(button,collect,key,host){
    if(!button)return;
    button.addEventListener('click',async event=>{
      if(button.dataset.preflightPass==='1'){delete button.dataset.preflightPass;return;}
      event.stopImmediatePropagation();event.preventDefault();
      let findings=[];
      try{findings=collect();}catch{/* the solver path validates again */}
      if(host)render(host,findings);
      if(await gate(findings,key)){button.dataset.preflightPass='1';button.click();}
    },{capture:true});
  }

  window.addEventListener('femlanguagechange',()=>{for(const host of panels)if(host.isConnected)render(host,host._preflight);});
  window.Preflight={render,gate,watch,locate,text,guardButton};
})();
