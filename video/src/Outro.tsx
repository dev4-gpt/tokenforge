import {CanvasImage,staticFile,useVideoConfig} from 'remotion';
import {Frame,blue} from './Frame';
import evidence from './evidence.json';
export const Outro=()=>{const {fps}=useVideoConfig();return <Frame title="Reproduce every claim" kicker="Working UI · Saved evidence · Public code" foot="github.com/dev4-gpt/tokenforge · ElevenLabs narration · C0MPILED-15">
 <div style={{display:'flex',gap:44,height:'100%'}}>
 <div style={{width:640}}><div style={{fontSize:59,lineHeight:1.45}}>Propose.<br/>Test.<br/>Retrieve.<br/>Learn.</div><div style={{fontSize:37,color:'#adb9ce',marginTop:25}}>Offline report · Recorded attempts<br/>Tests · Frozen champion hashes</div><div style={{fontSize:31,color:blue,marginTop:30}}>SHA-256 {evidence.kernel_sha256.slice(0,18)}…</div></div>
 <CanvasImage src={staticFile('dashboard.jpg')} premountFor={fps} style={{width:980,height:690,objectFit:'contain',borderRadius:20,border:'1px solid #41516b'}}/>
 </div>
 </Frame>};
