/* Cursor timestamps are whole-note units; WAV timestamps are seconds. */
class ScoreTransport {
  constructor(audio, sheet, wrapper, marker, range, clock) {
    Object.assign(this,{audio,sheet,wrapper,marker,range,clock,points:[],bpm:120});
    this.frame=0; this.dragging=false;
    audio.addEventListener('timeupdate',()=>this.update());
    audio.addEventListener('seeked',()=>this.update());
    audio.addEventListener('loadedmetadata',()=>this.update());
    audio.addEventListener('play',()=>this.tick());
    audio.addEventListener('pause',()=>{cancelAnimationFrame(this.frame);this.update();});
    audio.addEventListener('ended',()=>this.update());
    range.addEventListener('input',()=>this.seek(Number(range.value)));
    sheet.addEventListener('click',event=>this.seekAt(event.clientX,event.clientY));
    marker.addEventListener('pointerdown',event=>{this.dragging=true;marker.setPointerCapture(event.pointerId);event.preventDefault();});
    marker.addEventListener('pointermove',event=>{if(this.dragging)this.seekAt(event.clientX,event.clientY);});
    for(const name of ['pointerup','pointercancel']) marker.addEventListener(name,()=>{this.dragging=false;});
    marker.addEventListener('keydown',event=>{
      if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
        event.preventDefault();this.seek(event.key==='Home'?0:event.key==='End'?audio.duration:audio.currentTime+(event.key==='ArrowLeft'?-1:1)*60/this.bpm);
      }
    });
    let width=0;
    new ResizeObserver(entries=>{const next=entries[0].contentRect.width;if(Math.abs(next-width)>1){width=next;clearTimeout(this.resizeTimer);this.resizeTimer=setTimeout(()=>{if(this.renderer)this.build(this.renderer,this.bpm);},600);}}).observe(wrapper);
    sheet.addEventListener('scroll',()=>this.update());
  }
  build(renderer,bpm){
    this.renderer=renderer;this.bpm=bpm;this.points=[];
    const cursor=renderer.cursor;
    if(!cursor)return;
    cursor.reset();cursor.show();
    const origin=this.wrapper.getBoundingClientRect();
    for(let count=0;count<10000&&!cursor.Iterator.EndReached;count++){
      cursor.update();
      const r=cursor.cursorElement.getBoundingClientRect();
      const seconds=cursor.Iterator.CurrentSourceTimestamp.RealValue*4*60/bpm;
      if(Number.isFinite(seconds)&&r.height>0)this.points.push({t:seconds,x:r.left-origin.left+r.width/2+this.sheet.scrollLeft,y:r.top-origin.top,h:r.height});
      cursor.next();
    }
    cursor.reset();cursor.hide();
    this.points.sort((a,b)=>a.t-b.t);
    this.marker.hidden=!this.points.length;this.update();
  }
  seek(seconds){if(Number.isFinite(this.audio.duration)){this.audio.currentTime=Math.max(0,Math.min(seconds,this.audio.duration));this.update();}}
  seekAt(x,y){
    if(!this.points.length)return;
    const r=this.wrapper.getBoundingClientRect();x=x-r.left+this.sheet.scrollLeft;y-=r.top;
    const distance=p=>Math.abs(x-p.x)+5*Math.max(p.y-y,y-p.y-p.h,0);
    const nearest=this.points.reduce((a,b)=>distance(a)<distance(b)?a:b);
    this.seek(nearest.t);
  }
  tick(){cancelAnimationFrame(this.frame);this.update();if(!this.audio.paused)this.frame=requestAnimationFrame(()=>this.tick());}
  update(){
    const t=this.audio.currentTime||0,duration=this.audio.duration;
    const format=value=>`${Math.floor(value/60)}:${String(Math.floor(value%60)).padStart(2,'0')}`;
    this.clock.textContent=`${format(t)} / ${format(Number.isFinite(duration)?duration:0)}`;
    this.range.max=Number.isFinite(duration)?duration:1;this.range.value=t;this.range.disabled=!Number.isFinite(duration);
    this.marker.setAttribute('aria-valuemax',Number.isFinite(duration)?duration:1);this.marker.setAttribute('aria-valuenow',t.toFixed(2));this.marker.setAttribute('aria-valuetext',format(t));
    if(!this.points.length)return;
    let index=0;while(index+1<this.points.length&&this.points[index+1].t<=t)index++;
    const p=this.points[index],next=this.points[index+1];let x=p.x;
    if(next&&next.t>p.t&&Math.abs(next.y-p.y)<5)x+=(next.x-p.x)*Math.max(0,Math.min(1,(t-p.t)/(next.t-p.t)));
    this.marker.style.left=`${x-this.sheet.scrollLeft}px`;this.marker.style.top=`${p.y}px`;this.marker.style.height=`${p.h}px`;
    if(this.lastY!==p.y&&!this.audio.paused&&!this.dragging)this.marker.scrollIntoView({block:'nearest',inline:'nearest'});
    this.lastY=p.y;
  }
}
globalThis.ScoreTransport=ScoreTransport;
