const el = id => document.getElementById(id);
let jobId, sourceUrl, renderer;
async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === 'string' ? data.detail : 'The request failed. Please try again.'); }
  return response.json();
}
function options() { return {bpm: el('bpm').value ? Number(el('bpm').value) : null, meter: el('meter').value, split: el('split').value ? Number(el('split').value) : null, feel:el('feel').value}; }
async function show(job) {
  jobId = job.id;
  el('bpm').value = job.details.bpm;
  el('meter').value = job.details.meter;
  el('feel').value = job.details.feel || 'expressive';
  el('split').placeholder = `Automatic: ${job.details.staff_split ?? 60}`;
  for (const [id,file] of [['detected-player','performance.wav'],['score-player','score.wav']]) {
    el(id).pause(); el(id).src = `/api/jobs/${job.id}/files/${file}?v=${Date.now()}`;
  }
  el('empty').hidden = true; el('results').hidden = false;
  el('summary').textContent = `${job.note_count} notes · ${job.pedal_count} pedal events · ${job.details.bpm} BPM · Estimated key: ${job.details.key} · ${job.details.meter}`;
  for (const [id, file] of [['xml','score.musicxml'],['midi','performance.mid'],['events','events.json']]) el(id).href = `/api/jobs/${job.id}/files/${file}`;
  el('warnings').replaceChildren(...job.details.warnings.map(text => { const li = document.createElement('li'); li.textContent = text; return li; }));
  if (!window.opensheetmusicdisplay) throw new Error('Score preview library is missing. The MusicXML and MIDI downloads are still available.');
  renderer ??= new opensheetmusicdisplay.OpenSheetMusicDisplay('sheet', {autoResize:true,drawTitle:true,backend:'svg'});
  await renderer.load(`/api/jobs/${job.id}/files/score.musicxml?v=${Date.now()}`); renderer.render(); el('print').hidden = false;
}
el('audio').addEventListener('change', () => { for(const id of ['player','detected-player','score-player']) el(id).pause(); if (sourceUrl) URL.revokeObjectURL(sourceUrl); const file = el('audio').files[0]; el('original').hidden = !file; if(file){sourceUrl=URL.createObjectURL(file);el('player').src=sourceUrl;} });
el('upload').addEventListener('submit', async event => {
  event.preventDefault(); el('submit').disabled = true; el('results').hidden = true; el('print').hidden = true; el('empty').hidden = false;
  try {
    const file = el('audio').files[0]; if(file.size > 40*1024*1024) throw new Error('Choose a file smaller than 40 MB.');
    const data = new FormData(); data.append('file',file); data.append('signature',options().meter); data.append('feel',options().feel); if(options().bpm) data.append('bpm',options().bpm); if(options().split) data.append('split',options().split);
    el('status').textContent = 'Uploading your recording…'; let job = await request('/api/jobs',{method:'POST',body:data}); jobId=job.id;
    while (!['done','error'].includes(job.status)) { el('status').textContent=job.message; await new Promise(resolve => setTimeout(resolve,1500)); job=await request(`/api/jobs/${jobId}`); }
    el('status').textContent=job.message; if(job.status==='done') await show(job);
  } catch(error) { el('status').textContent=error.message; } finally {el('submit').disabled=false;}
});
el('rescore').addEventListener('click',async()=>{el('rescore').disabled=true;try{if(!el('bpm').checkValidity())throw new Error('Tempo must be between 20 and 300.');const job=await request(`/api/jobs/${jobId}/score`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(options())});await show(job);el('status').textContent='Notation updated. Original performance MIDI is unchanged.';}catch(error){el('status').textContent=error.message;}finally{el('rescore').disabled=false;}});
el('print').addEventListener('click',()=>window.print());
for (const id of ['player','detected-player','score-player']) el(id).addEventListener('play',()=>{for(const other of ['player','detected-player','score-player']) if(other!==id) el(other).pause();});
request('/api/latest').then(job=>job ? show(job) : null).catch(error=>{el('status').textContent=error.message;});
request('/api/health').then(data=>{el('submit').disabled=!data.model_ready;el('submit').textContent='Transcribe recording';el('status').textContent=data.model_ready?'Ready for a solo piano recording.':'Model not installed yet. Run setup.ps1 in the Ivory folder.';}).catch(()=>{el('status').textContent='Start Ivory using the launcher in the project folder.';});
if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  addEventListener('pagehide', () => lifecycle.abort(), {once:true});
  try {
    Promise.resolve(document.modelContext.registerTool({name:'read_transcription_status',description:'Read the status of the recording currently selected in Ivory.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute:async()=>jobId?await request(`/api/jobs/${jobId}`):{status:'no_recording'}},{signal:lifecycle.signal})).catch(()=>{});
  } catch (_) { /* Optional browser capability; the visible interface works without it. */ }
}
