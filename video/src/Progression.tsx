import {useCurrentFrame,useVideoConfig,interpolate} from 'remotion';
import {Frame,blue} from './Frame';
import evidence from './evidence.json';
export const Progression=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const points=evidence.rounds.map(r=>`${100+r.round*180},${550-r.speedup*58}`).join(' ');return <Frame title="Rounds, with honest limits" kicker="48 attempts · 3 promotions" foot="The large gain is round 1. Later gains are uncertain under repeated measurements.">
 <svg width="1720" height="620" viewBox="0 0 1720 620">
 {[1,3,5,7].map(t=><g key={t}><line x1="90" x2="1620" y1={550-t*58} y2={550-t*58} stroke="#2a3548"/><text x="30" y={560-t*58} fill="#adb9ce" fontSize="32">{t}×</text></g>)}
 <polyline points={points} fill="none" stroke={blue} strokeWidth="7" strokeDasharray="2500" strokeDashoffset={interpolate(f,[0,2*fps],[2500,0],{extrapolateRight:'clamp'})}/>
 {evidence.rounds.map(r=><g key={r.round}><circle cx={100+r.round*180} cy={550-r.speedup*58} r={r.promotion?15:9} fill={r.promotion?'#0b1019':blue} stroke={blue} strokeWidth="5"/><text x={100+r.round*180} y="595" fill="#adb9ce" textAnchor="middle" fontSize="35">{r.round}</text>{r.promotion&&<text x={100+r.round*180} y={520-r.speedup*58} fill="#f2f5fb" textAnchor="middle" fontSize="37">{r.speedup.toFixed(2)}×</text>}</g>)}
 </svg>
 <div style={{fontSize:40,color:'#adb9ce'}}>Round 0: scalar baseline · Circles: recorded promotions · Development measurements</div>
 </Frame>};
