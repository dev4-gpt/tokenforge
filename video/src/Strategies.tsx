import {Frame,panel,blue} from './Frame';
const Card=({n,title,detail}:{n:number;title:string;detail:string})=><div style={{background:panel,borderRadius:20,padding:30,border:'1px solid #2a3548'}}><div style={{fontSize:34,color:blue}}>STRATEGY {n}</div><div style={{fontSize:52,fontWeight:700,marginTop:14}}>{title}</div><div style={{fontSize:35,color:'#adb9ce',marginTop:14}}>{detail}</div></div>;
export const Strategies=()=> <Frame title="Six agents, six strategies" kicker="01 · Propose" foot="DeepSeek on Luminal · Strategy slots rotate · Fast and reasoner modes">
 <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:24}}>
  <Card n={1} title="NEON vectors" detail="Independent accumulators"/>
  <Card n={2} title="Loop unrolling" detail="Break dependency chains"/>
  <Card n={3} title="Multithreading" detail="Split output rows with GCD"/>
  <Card n={4} title="Cache reuse" detail="Share loaded inputs"/>
  <Card n={5} title="Combine methods" detail="Threads plus SIMD"/>
  <Card n={6} title="Refine champion" detail="Target its next bottleneck"/>
 </div>
 <div style={{fontSize:56,marginTop:40,color:blue}}>Propose together → Test one at a time</div>
 </Frame>;
