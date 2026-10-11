import {CanvasImage,staticFile,useVideoConfig} from 'remotion';
import {Frame,blue} from './Frame';
import evidence from './evidence.json';
export const Memory=()=>{const {fps}=useVideoConfig();return <Frame title="Feedback that fixes code" kicker="03 · Learn in MongoDB Atlas" foot={`Actual vector retrieval · Source ${evidence.repair.source_id.slice(0,16)}… · Dev + validation passed`}>
 <div style={{display:'flex',gap:40,height:'100%'}}>
 <div style={{width:590,fontSize:52,lineHeight:1.5}}><div>Stored compiler failure</div><div style={{color:blue}}>↓ Atlas vector retrieval</div><div>New Luminal proposal</div><div style={{color:'#67d5a0'}}>↓ Passed evaluation</div><div style={{fontSize:36,color:'#adb9ce',marginTop:25}}>Exact prompt, context,<br/>source IDs and lineage.</div></div>
 <CanvasImage src={staticFile('memory.jpg')} premountFor={fps} style={{width:1030,height:680,objectFit:'cover',borderRadius:20,border:'1px solid #41516b'}}/>
 </div>
 </Frame>};
