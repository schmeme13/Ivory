const el=id=>document.getElementById(id),jobId=new URLSearchParams(location.search).get('job');
let doc,revision,renderer,selected,history=[],dirty=false,busy=false;
const base=`/api/jobs/${encodeURIComponent(jobId)}/workshop`;
const audio=el('score-player');
const transport=new ScoreTransport(audio,el('sheet'),el('sheet-wrap'),el('playhead'),el('seek'),el('time'));
const names=['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'];
const pitchName=p=>names[p%12]+(Math.floor(p/12)-1);
const keys=['C♭ major / A♭ minor','G♭ major / E♭ minor','D♭ major / B♭ minor','A♭ major / F minor','E♭ major / C minor','B♭ major / G minor','F major / D minor','C major / A minor','G major / E minor','D major / B minor','A major / F♯ minor','E major / C♯ minor','B major / G♯ minor','F♯ major / D♯ minor','C♯ major / A♯ minor'];
keys.forEach((name,i)=>el('key').add(new Option(name,i-7)));for(let p=21;p<=108;p++)el('pitch').add(new Option(pitchName(p),p));for(let i=-12;i<=12;i++)el('transpose').add(new Option(i===0?'No shift':`${i>0?'+':''}${i} semitones`,i));el('transpose').value='0';
async function request(url,options){const r=await fetch(url,options);if(!r.ok){const d=await r.json().catch(()=>({}));throw new Error(typeof d.detail==='string'?d.detail:'Check the note values: positions and lengths use steps of 0.125 beats, and scores are limited to ten minutes.');}return r.json();}
function mark(){dirty=true;document.body.classList.add('dirty');el('save').disabled=false;el('undo').disabled=!history.length;el('saved-state').textContent='Unsaved edits · save to update playback';el('print').setAttribute('aria-disabled','true');el('xml').setAttribute('aria-disabled','true');}
function remember(){history.push(structuredClone(doc));if(history.length>60)history.shift();}
function current(){return doc.notes.find(n=>n.id===selected);}
function fillNotes(){
  const measureBeats=Number(doc.meter.split('/')[0])*4/Number(doc.meter.split('/')[1]);
  el('notes').replaceChildren(...[...doc.notes].sort((a,b)=>a.start-b.start||a.staff-b.staff||a.pitch-b.pitch).map(n=>new Option(`Bar ${Math.floor(n.start/measureBeats)+1} · ${pitchName(n.pitch)} · ${n.staff?'lower':'upper'}`,n.id)));
  if(!current())selected=el('notes').options[0]?.value;el('notes').value=selected||'';fillNote();
}
function fillNote(){const n=current();for(const id of ['pitch','start','duration','staff'])el(id).disabled=!n;el('delete').disabled=!n;if(n){el('pitch').value=n.pitch;el('start').value=n.start+1;el('duration').value=n.duration;el('staff').value=n.staff;}}
function fillPiece(){el('title').value=doc.title;el('bpm').value=doc.bpm;el('meter').value=doc.meter;el('key').value=doc.sharps;fillNotes();}
async function preview(){
  audio.pause();el('play').disabled=true;
  renderer??=new opensheetmusicdisplay.OpenSheetMusicDisplay('sheet',{autoResize:true,drawTitle:false,drawComposer:false,drawSubtitle:false,backend:'svg'});
  await renderer.load(`${base}/files/score.musicxml?v=${revision}`);renderer.render();transport.build(renderer,doc.bpm);
  audio.src=`${base}/files/score.wav?v=${revision}`;el('play').disabled=false;el('score-title').textContent=doc.title;
  el('xml').href=`${base}/files/score.musicxml`;el('print').href=`/print.html?job=${encodeURIComponent(jobId)}&edition=workshop`;for(const id of ['print','xml'])el(id).removeAttribute('aria-disabled');
}
el('notes').addEventListener('change',()=>{selected=el('notes').value;fillNote();});
el('piece').addEventListener('submit',e=>e.preventDefault());
el('piece').addEventListener('change',e=>{if(!doc||e.target.id==='transpose'||!el('piece').reportValidity())return;remember();doc.title=el('title').value.trim()||'Untitled';doc.bpm=Number(el('bpm').value);doc.meter=el('meter').value;doc.sharps=Number(el('key').value);fillNotes();mark();});
el('note-form').addEventListener('submit',e=>e.preventDefault());
el('note-form').addEventListener('change',()=>{if(!current()||!el('note-form').reportValidity())return;remember();Object.assign(current(),{pitch:Number(el('pitch').value),start:Number(el('start').value)-1,duration:Number(el('duration').value),staff:Number(el('staff').value)});fillNotes();mark();});
el('add').addEventListener('click',()=>{if(!doc||busy)return;remember();const previous=current();const n={id:crypto.randomUUID(),pitch:previous?.pitch||60,start:previous?previous.start+previous.duration:0,duration:1,staff:previous?.staff||0};doc.notes.push(n);selected=n.id;fillNotes();mark();});
el('delete').addEventListener('click',()=>{if(!current()||busy)return;remember();doc.notes=doc.notes.filter(n=>n.id!==selected);fillNotes();mark();});
el('undo').addEventListener('click',()=>{if(!history.length||busy)return;doc=history.pop();fillPiece();mark();});
el('transpose-button').addEventListener('click',()=>{if(!doc||busy)return;const delta=Number(el('transpose').value);if(!delta)return;if(doc.notes.some(n=>n.pitch+delta<21||n.pitch+delta>108)){el('status').textContent='That shift goes outside the piano range.';return;}remember();doc.notes.forEach(n=>n.pitch+=delta);const tonic=((doc.sharps*7+delta)%12+12)%12;doc.sharps=[0,-5,2,-3,4,-1,6,1,-4,3,-2,5][tonic];fillPiece();mark();});
el('save').addEventListener('click',async()=>{
  if(!doc||busy||!el('piece').reportValidity()||!el('note-form').reportValidity())return;
  busy=true;audio.pause();document.body.classList.add('workshop-busy');el('save').disabled=true;el('status').textContent='Saving edits and rebuilding playback…';
  try{doc.revision=revision;doc=await request(base,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(doc)});revision=doc.revision;dirty=false;document.body.classList.remove('dirty');fillPiece();await preview();el('saved-state').textContent='Saved score preview';el('status').textContent='Saved. Original transcription preserved.';}
  catch(error){el('status').textContent=error.message;el('save').disabled=false;}
  finally{busy=false;document.body.classList.remove('workshop-busy');}
});
el('play').addEventListener('click',async()=>{try{if(audio.paused){if(audio.ended)audio.currentTime=0;await audio.play();}else audio.pause();}catch(_){el('status').textContent='Playback unavailable. Save changes and try again.';}});
for(const event of ['play','pause','ended'])audio.addEventListener(event,()=>{el('play').textContent=audio.paused?'▶':'Ⅱ';el('play').setAttribute('aria-label',audio.paused?'Play saved score':'Pause saved score');});
addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
(async()=>{try{if(!jobId)throw new Error('Open a transcription and choose Open workshop.');doc=await request(base);revision=doc.revision;fillPiece();await preview();el('status').textContent='Editing a separate copy.';}catch(error){el('status').textContent=error.message;}})();
