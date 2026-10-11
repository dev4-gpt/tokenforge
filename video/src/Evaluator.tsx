import {Frame,panel,blue} from './Frame';
export const Evaluator=()=> <Frame title="Measure before promoting" kicker="02 · Test" foot="Same clang -O3 flags · Tested greedy prompts · CPU timings stay sequential">
 <div style={{display:'flex',gap:46,height:'100%'}}>
 <div style={{flex:1,background:panel,borderRadius:24,padding:44,fontSize:54,lineHeight:1.65}}>
 <div>Compile the candidate</div><div>Check generated text</div><div>Warm the model</div><div>Median of five timings</div>
 </div>
 <div style={{flex:1,border:'2px solid #4d96ff',borderRadius:24,padding:44}}>
 <div style={{fontSize:40,color:blue}}>PROMOTION GATE</div><div style={{fontSize:160,fontWeight:800,marginTop:35}}>≥5%</div><div style={{fontSize:53,lineHeight:1.3}}>development improvement<br/>+ validation win</div>
 </div></div>
 </Frame>;
