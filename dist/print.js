const params=new URLSearchParams(location.search),job=params.get('job');
let renderer;
async function format(){
  const button=document.getElementById('print'),status=document.getElementById('status'),paper=document.getElementById('paper').value;
  button.disabled=true;document.getElementById('paper').disabled=true;status.textContent='Formatting pages…';
  try{
    if(!job)throw new Error('Open print from a transcription or workshop.');
    const a4=paper==='a4',width=a4?190:195.9,height=a4?277:259.4;
    document.body.classList.toggle('a4',a4);document.getElementById('paper-style').textContent=`@page{size:${a4?'A4':'letter'} portrait;margin:10mm}`;
    const holder=document.getElementById('engraving');holder.replaceChildren();holder.style.width=`${width}mm`;
    renderer=new opensheetmusicdisplay.OpenSheetMusicDisplay(holder,{autoResize:false,backend:'svg',pageFormat:a4?'A4_P':'Letter_P',drawTitle:true,drawSubtitle:false,drawComposer:false,newPageFromXML:false,newSystemFromXML:false});
    const edition=params.get('edition')==='workshop'?'/workshop':'';
    await renderer.load(`/api/jobs/${encodeURIComponent(job)}${edition}/files/score.musicxml?v=${Date.now()}`);
    await document.fonts.ready;renderer.render();
    const pages=document.getElementById('pages');pages.replaceChildren();
    for(const original of holder.querySelectorAll('svg')){
      const svg=original.cloneNode(true),box=original.getBBox();
      const w=parseFloat(original.getAttribute('width'))||original.viewBox.baseVal.width;
      const h=parseFloat(original.getAttribute('height'))||original.viewBox.baseVal.height;
      // Include all engraved content, even if a renderer element exceeds its viewport.
      const left=Math.min(0,box.x-3),top=Math.min(0,box.y-3);
      svg.setAttribute('viewBox',`${left} ${top} ${Math.max(w,box.x+box.width+3)-left} ${Math.max(h,box.y+box.height+3)-top}`);
      svg.setAttribute('preserveAspectRatio','xMidYMin meet');svg.removeAttribute('width');svg.removeAttribute('height');
      const page=document.createElement('section');page.className='print-page';page.style.width=`${width}mm`;page.style.height=`${height}mm`;page.append(svg);pages.append(page);
    }
    if(!pages.children.length)throw new Error('The score did not produce printable pages.');
    status.textContent=`${pages.children.length} page${pages.children.length===1?'':'s'} · Use matching paper size; turn off browser headers and footers.`;button.disabled=false;
  }catch(error){status.textContent=error.message;}finally{document.getElementById('paper').disabled=false;}
}
document.getElementById('paper').addEventListener('change',format);
document.getElementById('print').addEventListener('click',()=>window.print());
format();
