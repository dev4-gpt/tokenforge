import {AbsoluteFill,interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {blue} from './Frame';
export const Intro=()=>{const f=useCurrentFrame();const {fps}=useVideoConfig();return <AbsoluteFill style={{background:'#0b1019',color:'#f2f5fb',fontFamily:'Arial',padding:100,justifyContent:'center'}}>
 <div style={{fontSize:40,color:blue,letterSpacing:5}}>C0MPILED-15 · LUMINAL CHALLENGE A</div>
 <div style={{fontSize:180,fontWeight:800,letterSpacing:-8,margin:'25px 0',opacity:interpolate(f,[0,.4*fps],[0,1],{extrapolateRight:'clamp'})}}>TokenForge</div>
 <div style={{fontSize:76,lineHeight:1.15,maxWidth:1500}}>A research team<br/>for faster local AI.</div>
 <div style={{fontSize:39,color:'#adb9ce',marginTop:60}}>Luminal proposers · MongoDB memory · Local inference</div>
 </AbsoluteFill>};
