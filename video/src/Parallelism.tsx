import {useCurrentFrame,useVideoConfig,interpolate} from 'remotion';
import {Frame,blue} from './Frame';
import evidence from './evidence.json';
export const Parallelism=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();return <Frame title="Observed proposal latency" kicker="Matched three-proposal probe" foot="One batch per arm, parallel first · All six pass dev checks · Not a quality advantage claim">
 {evidence.parallelism.conditions.map((c,index)=><div key={c.name} style={{marginBottom:35}}>
 <div style={{display:'flex',justifyContent:'space-between',fontSize:52,fontWeight:700}}><span>{c.name==='parallel'?'Parallel':'Serial'}</span><span>{c.wall.toFixed(2)} seconds · {c.valid}/3 valid</span></div>
 <svg width="1720" height="185" viewBox="0 0 1720 185">{c.intervals.map((r,i)=><g key={r.agent}><text x="0" y={42+i*57} fill="#adb9ce" fontSize="29">Agent {r.agent}</text><rect x={160+r.start*135} y={13+i*57} height="40" rx="8" width={(r.end-r.start)*135*interpolate(f,[0,2*fps],[0,1],{extrapolateRight:'clamp'})} fill={index===0?blue:'#7787a2'}/></g>)}</svg>
 </div>)}
 <div style={{fontSize:52,color:blue}}>{evidence.parallelism.ratio.toFixed(2)}× shorter observed proposer wall time</div>
 </Frame>};
