const assert=require('node:assert/strict');
const test=require('node:test');
global.ResizeObserver=class{observe(){}};
global.cancelAnimationFrame=()=>{};
global.requestAnimationFrame=()=>1;
require('../dist/score-transport.js');
function element(extra={}){return {style:{},handlers:{},addEventListener(name,fn){this.handlers[name]=fn;},setAttribute(){},getBoundingClientRect(){return {left:10,top:20};},scrollIntoView(){},...extra};}
function setup(){
  const audio=element({currentTime:0,duration:8,paused:true});
  const sheet=element({scrollLeft:0});
  const marker=element();
  const range=element();
  const transport=new ScoreTransport(audio,sheet,element(),marker,range,element());
  let i=0;
  const data=[{t:0,x:30,y:40},{t:.25,x:130,y:40},{t:.5,x:30,y:240}];
  const cursor={reset(){i=0;},show(){},hide(){},update(){},next(){i++;},get Iterator(){return {EndReached:i>=data.length,CurrentSourceTimestamp:{RealValue:data[i]?.t}};},cursorElement:{getBoundingClientRect(){return {left:data[i].x,top:data[i].y,width:4,height:100};}}};
  transport.build({cursor},60);
  return {transport,audio,sheet,marker,range};
}
test('score timestamp conversion and interpolation follow WAV seconds',()=>{
  const {transport,audio,marker}=setup();
  assert.deepEqual(transport.points.map(p=>p.t),[0,1,2]);
  audio.currentTime=.5;transport.update();
  assert.equal(marker.style.left,'72px');
  assert.equal(marker.style.top,'20px');
});
test('sheet seek chooses the correct system and clamps transport seeks',()=>{
  const {transport,audio}=setup();transport.seekAt(31,260);assert.equal(audio.currentTime,2);
  transport.seek(-4);assert.equal(audio.currentTime,0);transport.seek(40);assert.equal(audio.currentTime,8);
});
test('marker keyboard and range both update audio position',()=>{
  const {marker,audio,range}=setup();
  marker.handlers.keydown({key:'ArrowRight',preventDefault(){}});assert.equal(audio.currentTime,1);
  range.value='4.2';range.handlers.input();assert.equal(audio.currentTime,4.2);
});
