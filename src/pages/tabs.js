// 当前显示的主页面。
function currentPageKey() {
  const activePage = pageViews.find((viewElement) => !viewElement.hidden);
  return activePage?.dataset.page || "home";
}

// 切换顶部页签对应的功能页；绘图页和计算页各自刷新自己的 canvas 尺寸。
function setPage(page) {
  closeShapeEditor();
  const previousPage = currentPageKey();
  if(typeof stopDeformationPlayback==='function')stopDeformationPlayback();
  let nextPage = ["calculation", "results", "materials", "blast-library", "blast", "blast-results", "deformation", "deformation-results", "deformation-library"].includes(page) ? page : "home";
  if(nextPage.startsWith('deformation')&&!isProfessionalCalculationEnabled('deformation'))nextPage='calculation';
  if (["blast-library", "blast", "blast-results"].includes(nextPage) && !isProfessionalCalculationEnabled("blast")) nextPage = "calculation";
  if(window.tensoraSolid3dSketchMode&&nextPage!=='home')window.tensoraSolid3dSketchMode=false;
  const use3d=document.getElementById('enableSolid3dModule').checked&&['home','calculation','results'].includes(nextPage)&&!(nextPage==='home'&&window.tensoraSolid3dSketchMode);
  if ((nextPage==='results'&&!use3d)||nextPage==='blast-results') activateResultWorkspace(nextPage === "results" ? baseResultSource : "blast");
  if (nextPage !== "blast-results" && typeof blastPlayback !== "undefined" && blastPlayback !== null) {
    cancelAnimationFrame(blastPlayback); blastPlayback = null;
  }
  if (previousPage === "blast-results" && nextPage !== "blast-results" && typeof blastHistory !== "undefined" && blastHistory) {
    blastHistory.displayController?.abort(); blastLoadTicket++;
  }
  hideRegionMaterialMenu();
  if (nextPage !== "calculation") {
    cancelCalculationAnimationFrame();
  }
  pageTabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.pageTab === nextPage);
  });
  document.getElementById('solid3dPage').dataset.page=use3d?nextPage:'solid3d';
  pageViews.forEach((viewElement) => {
    const isActive = viewElement.id==='solid3dPage' ? use3d : viewElement.dataset.page === nextPage&&!use3d;
    viewElement.hidden = !isActive;
    viewElement.classList.toggle("active", isActive);
  });
  document.getElementById('solid3dSketchReturn').hidden=!(nextPage==='home'&&!use3d&&window.tensoraSolid3dSketchMode);
  if (nextPage === "home"&&!use3d) {
    requestAnimationFrame(resizeCanvas);
  }
  if (nextPage === "calculation"&&!use3d) {
    requestAnimationFrame(() => {
      resizeCalculationCanvas();
      renderCalculationView();
    });
  }
  if (nextPage === "results"&&!use3d) {
    requestAnimationFrame(() => {
      resizeResultCanvas();
      if(activeResultChannel==='deformation'&&resultChannels.deformation?.needsFit){fitResultViewToData();resultChannels.deformation.needsFit=false;}
      loadCalculationResultsFromProjectFolder({ quietMissing: true });
    });
  }
  if (nextPage === "blast") {
    document.getElementById("blastMaxAnalysisNodes").value = maxAnalysisNodes.value;
    requestAnimationFrame(renderBlastSetup);
  }
  if (nextPage === "blast-results") {
    requestAnimationFrame(() => { resizeResultCanvas(); renderResultView(); });
  }
  if (nextPage === "blast-library") renderBlastLibrary();
  if(nextPage==='deformation'){restoreDeformationControls();}
  if(nextPage==='deformation-results')requestAnimationFrame(renderDeformation);
  if(nextPage==='deformation-library'){
    renderDeformationLibraryList();
    renderDeformationAssociations();
    renderDeformationLibraryStorage();
  }
  if (nextPage === "materials") {
    renderMaterialLibrary();
  }
  if(use3d)window.dispatchEvent(new CustomEvent('tensora-solid3d-show',{detail:{page:nextPage}}));
}
