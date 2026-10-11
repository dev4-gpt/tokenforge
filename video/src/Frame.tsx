import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {ReactNode} from 'react';
export const blue='#4d96ff';
export const panel='#171e2b';
export const Frame=({title,kicker,foot,children}:{title:string;kicker:string;foot:string;children:ReactNode})=>{
 const frame=useCurrentFrame();const {fps}=useVideoConfig();
 return <AbsoluteFill style={{background:'#0b1019',color:'#f2f5fb',fontFamily:'Arial, sans-serif',padding:96,opacity:interpolate(frame,[0,.3*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
  <div style={{fontSize:32,color:blue,letterSpacing:3,fontWeight:700}}>{kicker.toUpperCase()}</div>
  <div style={{fontSize:92,fontWeight:750,letterSpacing:-3,lineHeight:1.1,marginTop:22}}>{title}</div>
  <div style={{position:'absolute',left:96,right:96,top:258,bottom:124}}>{children}</div>
  <div style={{position:'absolute',bottom:62,left:96,right:96,fontSize:31,color:'#adb9ce',borderTop:'1px solid #2a3548',paddingTop:20}}>{foot}</div>
 </AbsoluteFill>
};
