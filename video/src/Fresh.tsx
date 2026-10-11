import {useCurrentFrame,useVideoConfig,interpolate} from 'remotion';
import {Frame,blue} from './Frame';
import evidence from './evidence.json';
export const Fresh=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const item=evidence.heldout.items[0];return <Frame title="Fresh tests. Frozen winner." kicker="Held-out result · Original artifact" foot="Untouched model and prompts · Identical generated text on tested cases · One Apple M3 Pro">
 <div style={{display:'flex',gap:65}}>
 <div style={{width:590}}><div style={{fontSize:195,fontWeight:800,color:blue,lineHeight:1.1}}>7.82×</div><div style={{fontSize:48,lineHeight:1.35,marginTop:25}}>Geometric-mean speedup<br/>across three fresh workloads</div><div style={{fontSize:36,color:'#adb9ce',marginTop:28}}>15M · 42M · unseen 110M</div></div>
 <div style={{flex:1,background:'#171e2b',borderRadius:24,padding:40}}>
 <div style={{fontSize:48,fontWeight:700}}>Unseen 110M model</div>
 <div style={{fontSize:33,color:'#adb9ce',marginTop:34}}>SCALAR BASELINE</div><div style={{fontSize:78}}>{item.baseline_tps.toFixed(1)} tokens / second</div>
 <div style={{height:28,width:Math.max(24,item.baseline_tps/120*850),background:'#7787a2',borderRadius:6,marginTop:16}}/>
 <div style={{fontSize:33,color:blue,marginTop:35}}>TOKENFORGE CHAMPION</div><div style={{fontSize:78}}>{item.champion_tps.toFixed(1)} tokens / second</div>
 <div style={{height:28,width:item.champion_tps/120*850*interpolate(f,[0,2*fps],[0,1],{extrapolateRight:'clamp'}),background:blue,borderRadius:6,marginTop:16}}/>
 </div></div>
 </Frame>};
