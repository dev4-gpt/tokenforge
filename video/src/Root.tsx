import {Composition,Folder} from 'remotion';
import {TokenForge} from './Composition';
import {Intro} from './Intro';import {Strategies} from './Strategies';import {Evaluator} from './Evaluator';import {Memory} from './Memory';import {Progression} from './Progression';import {Parallelism} from './Parallelism';import {Fresh} from './Fresh';import {Outro} from './Outro';
export const RemotionRoot=()=> <>
 <Composition id="TokenForge" component={TokenForge} durationInFrames={2700} fps={30} width={1920} height={1080}/>
 <Folder name="Scenes">
  <Composition id="Intro" component={Intro} durationInFrames={120} fps={30} width={1920} height={1080}/>
  <Composition id="Strategies" component={Strategies} durationInFrames={420} fps={30} width={1920} height={1080}/>
  <Composition id="Evaluator" component={Evaluator} durationInFrames={390} fps={30} width={1920} height={1080}/>
  <Composition id="Memory" component={Memory} durationInFrames={450} fps={30} width={1920} height={1080}/>
  <Composition id="Progression" component={Progression} durationInFrames={270} fps={30} width={1920} height={1080}/>
  <Composition id="Parallelism" component={Parallelism} durationInFrames={390} fps={30} width={1920} height={1080}/>
  <Composition id="Fresh" component={Fresh} durationInFrames={390} fps={30} width={1920} height={1080}/>
  <Composition id="Outro" component={Outro} durationInFrames={270} fps={30} width={1920} height={1080}/>
 </Folder>
 </>;
