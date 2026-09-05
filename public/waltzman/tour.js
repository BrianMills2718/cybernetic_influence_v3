// Spotlight tour: highlight one real control, one line about it, Next.
//
// Standalone and dependency-free so it can be dropped into another project:
// include this file, define steps as [{sel, title, body}], call startTour(key)
// or maybeStartTour(key) to run it once per browser. Steps whose selector
// matches nothing are skipped, so a tour degrades rather than breaking when a
// control is conditional or has been removed.
//
// Define window.TOURS = { key: [step, ...] } before calling.
const tour={steps:[],i:0,key:null,onEnd:null};
if(typeof window!=='undefined')window.startTour=startTour;
function tourSeen(key){try{return localStorage.getItem('fl_tour_'+key)==='1';}catch(_){return false;}}
function markTourSeen(key){try{localStorage.setItem('fl_tour_'+key,'1');}catch(_){}}

function startTour(key){
  const steps=((window.TOURS||{})[key]||[]).filter(st=>document.querySelector(st.sel));
  if(!steps.length)return;
  tour.steps=steps; tour.i=0; tour.key=key;
  if(!document.getElementById('tourLayer')){
    const layer=document.createElement('div');
    layer.id='tourLayer';
    layer.innerHTML='<div id="tourSpot"></div><div id="tourPop" role="dialog" aria-modal="true" aria-labelledby="tourTitle" tabindex="-1">'+
      '<button class="tour-x" id="tourClose" type="button" aria-label="Close the tour">&times;</button>'+
      '<div class="tour-step" id="tourCount"></div><strong id="tourTitle"></strong><p id="tourBody"></p>'+
      '<div class="tour-actions"><button class="btn small tour-skip" id="tourSkip" type="button">Skip tour</button><span class="tour-nav">'+
      '<button class="btn small" id="tourBack">Back</button><button class="btn primary small" id="tourNext">Next</button></span></div></div>';
    document.body.appendChild(layer);
    document.getElementById('tourSkip').addEventListener('click',endTour);
    document.getElementById('tourClose').addEventListener('click',endTour);
    document.getElementById('tourBack').addEventListener('click',()=>showStep(tour.i-1));
    document.getElementById('tourNext').addEventListener('click',()=>tour.i>=tour.steps.length-1?endTour():showStep(tour.i+1));
    layer.addEventListener('click',e=>{if(e.target===layer)endTour();});
    document.addEventListener('keydown',tourKeys);
    window.addEventListener('resize',positionTour);
    window.addEventListener('scroll',positionTour,{passive:true});
  }
  document.getElementById('tourLayer').hidden=false;
  showStep(0);
}
function tourKeys(e){
  const layer=document.getElementById('tourLayer');
  if(!layer||layer.hidden)return;
  if(e.key==='Escape'){e.preventDefault();endTour();}
  else if(e.key==='ArrowRight'){e.preventDefault();tour.i>=tour.steps.length-1?endTour():showStep(tour.i+1);}
  else if(e.key==='ArrowLeft'){e.preventDefault();showStep(tour.i-1);}
}
function showStep(i){
  if(i<0||i>=tour.steps.length)return;
  tour.i=i;
  const st=tour.steps[i];
  const el=document.querySelector(st.sel);
  if(!el)return tour.i>=tour.steps.length-1?endTour():showStep(i+1);
  el.scrollIntoView({block:'center',behavior:'auto'});
  document.getElementById('tourCount').textContent=`${i+1} of ${tour.steps.length}`;
  document.getElementById('tourTitle').textContent=st.title;
  document.getElementById('tourBody').textContent=st.body;
  document.getElementById('tourBack').disabled=i===0;
  document.getElementById('tourNext').textContent=i===tour.steps.length-1?'Done':'Next';
  positionTour();
  document.getElementById('tourPop').focus();
}
function positionTour(){
  const layer=document.getElementById('tourLayer');
  if(!layer||layer.hidden)return;
  const st=tour.steps[tour.i]; const el=st&&document.querySelector(st.sel);
  if(!el)return;
  const r=el.getBoundingClientRect(), pad=6;
  const spot=document.getElementById('tourSpot');
  spot.style.cssText=`top:${r.top-pad}px;left:${r.left-pad}px;width:${r.width+pad*2}px;height:${r.height+pad*2}px`;
  const pop=document.getElementById('tourPop');
  const pw=Math.min(320,window.innerWidth-24);
  pop.style.width=pw+'px';
  // Measure the popover rather than assuming a height. A short viewport - a
  // laptop with the browser chrome open, or a phone in landscape - has room for
  // neither side, so the last case clamps it on screen and accepts the overlap.
  const h=pop.offsetHeight, gap=14, edge=12, vh=window.innerHeight;
  let top;
  if(vh-r.bottom>=h+gap+edge) top=r.bottom+gap;
  else if(r.top>=h+gap+edge) top=r.top-h-gap;
  else top=Math.max(edge,Math.min(vh-h-edge,r.bottom+gap));
  pop.style.top=top+'px';
  pop.style.left=Math.min(Math.max(edge,r.left+r.width/2-pw/2),window.innerWidth-pw-edge)+'px';
}
function endTour(){
  const layer=document.getElementById('tourLayer');
  if(layer)layer.hidden=true;
  if(tour.key)markTourSeen(tour.key);
  if(typeof tour.onEnd==='function')tour.onEnd();
}
// Runs once per browser, then only on request.
function maybeStartTour(key){
  if(tourSeen(key))return;
  setTimeout(()=>startTour(key),350);
}

