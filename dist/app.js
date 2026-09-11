const el=id=>document.getElementById(id);
let jobId,sourceUrl,renderer,modelReady=false,busy=false;
const transport=new ScoreTransport(el('score-player'),el('sheet'),el('sheet-wrap'),el('playhead'),el('seek'),el('time'));
async function request(url,options){const response=await fetch(url,options);if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(typeof data.detail==='string'?data.detail:'The request failed. Please try again.');}return response.json();}
function options(){return {bpm:el('bpm').value?Number(el('bpm').value):null,meter:el('meter').value,split:el('split').value?Number(el('split').value):null,feel:el('feel').value};}
function pauseAll(){for(const id of ['player','detected-player','score-player'])el(id).pause();}
function setBusy(value){busy=value;el('submit').disabled=value||!modelReady||!el('audio').files.length;el('rescore').disabled=true;for(const id of ['feel','bpm','meter','split','audio'])el(id).disabled=value;}
async function show(job){
  pauseAll();jobId=job.id;
  el('bpm').value=job.details.bpm;el('meter').value=job.details.meter;el('feel').value=job.details.feel||'expressive';el('split').placeholder=`Auto (${job.details.staff_split??60})`;
  for(const [id,file] of [['detected-player','performance.wav'],['score-player','score.wav']])el(id).src=`/api/jobs/${job.id}/files/${file}?v=${Date.now()}`;
  el('empty').hidden=true;el('results').hidden=false;el('downloads').hidden=false;
  el('summary').textContent=`${job.details.bpm} BPM · ${job.details.meter}`;
  for(const [id,file] of [['xml','score.musicxml'],['midi','performance.mid'],['events','events.json']]){el(id).href=`/api/jobs/${job.id}/files/${file}`;el(id).download=file;}
  el('warnings').replaceChildren(...job.details.warnings.map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
  if(!window.opensheetmusicdisplay)throw new Error('Score renderer unavailable. You can still download your files.');
  renderer??=new opensheetmusicdisplay.OpenSheetMusicDisplay('sheet',{autoResize:true,drawTitle:false,drawSubtitle:false,drawComposer:false,backend:'svg'});
  el('play').disabled=true;
  await renderer.load(`/api/jobs/${job.id}/files/score.musicxml?v=${Date.now()}`);renderer.render();
  transport.build(renderer,job.details.bpm);el('play').disabled=false;el('rescore').disabled=true;
}
el('audio').addEventListener('change',()=>{
  pauseAll();if(sourceUrl)URL.revokeObjectURL(sourceUrl);
  const file=el('audio').files[0];el('original-play').hidden=!file;el('filename').textContent=file?file.name:'Add piano audio';el('filehint').textContent=file?'Click to replace':'Drop a file or browse';
  if(file){sourceUrl=URL.createObjectURL(file);el('player').src=sourceUrl;}el('submit').disabled=busy||!modelReady||!file;
});
for(const event of ['dragenter','dragover'])el('drop').addEventListener(event,e=>{e.preventDefault();if(!busy)el('drop').classList.add('dragging');});
el('drop').addEventListener('dragleave',()=>el('drop').classList.remove('dragging'));
el('drop').addEventListener('drop',e=>{e.preventDefault();el('drop').classList.remove('dragging');if(!busy&&e.dataTransfer.files.length){const transfer=new DataTransfer();transfer.items.add(e.dataTransfer.files[0]);el('audio').files=transfer.files;el('audio').dispatchEvent(new Event('change'));}});
el('upload').addEventListener('submit',async event=>{
  event.preventDefault();if(!el('settings').reportValidity())return;
  const file=el('audio').files[0];if(!file)return;
  pauseAll();setBusy(true);
  try{
    if(file.size>40*1024*1024)throw new Error('Choose a file smaller than 40 MB.');
    const data=new FormData();data.append('file',file);data.append('signature',options().meter);data.append('feel',options().feel);if(options().bpm)data.append('bpm',options().bpm);if(options().split)data.append('split',options().split);
    el('status').textContent='Uploading…';let job=await request('/api/jobs',{method:'POST',body:data});
    while(!['done','error'].includes(job.status)){el('status').textContent=job.message;await new Promise(resolve=>setTimeout(resolve,1500));job=await request(`/api/jobs/${job.id}`);}
    if(job.status==='error')throw new Error(job.message);
    await show(job);el('status').textContent='Sheet music ready.';
  }catch(error){el('status').textContent=error.message;}finally{setBusy(false);}
});
el('settings').addEventListener('input',()=>{el('rescore').disabled=!jobId||busy;});
el('settings').addEventListener('change',()=>{el('rescore').disabled=!jobId||busy;});
el('settings').addEventListener('submit',async event=>{
  event.preventDefault();if(!jobId||busy)return;
  const settings=options();pauseAll();setBusy(true);el('status').textContent='Updating sheet music…';
  try{await show(await request(`/api/jobs/${jobId}/score`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)}));el('status').textContent='Sheet music updated.';}
  catch(error){el('status').textContent=error.message;}finally{setBusy(false);}
});
async function toggle(id){try{const audio=el(id);if(audio.paused){if(audio.ended)audio.currentTime=0;await audio.play();}else audio.pause();}catch(_){el('status').textContent='Playback could not start. Update the sheet and try again.';}}
el('play').addEventListener('click',()=>toggle('score-player'));el('original-play').addEventListener('click',()=>toggle('player'));el('detected-play').addEventListener('click',()=>toggle('detected-player'));
for(const [id,button,label] of [['score-player','play','written score'],['player','original-play','Original'],['detected-player','detected-play','Detected performance']]){
  function update(){const playing=!el(id).paused;el(button).setAttribute('aria-label',`${playing?'Pause':'Play'} ${label}`);if(id==='score-player')el(button).textContent=playing?'Ⅱ':'▶';else if(id==='player')el(button).textContent=`${playing?'Ⅱ':'▶'} Original`;else el(button).firstChild.textContent=`${playing?'Ⅱ':'▶'} Detected performance`;}
  el(id).addEventListener('play',()=>{for(const other of ['player','detected-player','score-player'])if(other!==id)el(other).pause();update();});for(const event of ['pause','ended'])el(id).addEventListener(event,update);
  el(id).addEventListener('error',()=>{el('status').textContent='Audio unavailable. Update sheet music to regenerate playback.';});
}
el('print').addEventListener('click',()=>{el('downloads').open=false;window.print();});
document.addEventListener('click',event=>{for(const menu of document.querySelectorAll('.menu[open]'))if(!menu.contains(event.target))menu.open=false;});
document.addEventListener('keydown',event=>{if(event.key==='Escape')for(const menu of document.querySelectorAll('.menu[open]'))menu.open=false;});
(async()=>{try{const health=await request('/api/health');modelReady=health.model_ready;setBusy(false);el('status').textContent=modelReady?'':'Run setup.ps1 to install the model.';const job=await request('/api/latest');if(job)await show(job);}catch(error){el('status').textContent=error.message;}})();
if(document.modelContext?.registerTool){const lifecycle=new AbortController();addEventListener('pagehide',()=>lifecycle.abort(),{once:true});try{Promise.resolve(document.modelContext.registerTool({name:'read_transcription_status',description:'Read the currently displayed transcription status.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute:async()=>jobId?request(`/api/jobs/${jobId}`):{status:'no_recording'}},{signal:lifecycle.signal})).catch(()=>{});}catch(_){}}
