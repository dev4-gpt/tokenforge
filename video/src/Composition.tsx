import {AbsoluteFill,Series,staticFile,useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {Intro} from './Intro';
import {Strategies} from './Strategies';
import {Evaluator} from './Evaluator';
import {Memory} from './Memory';
import {Progression} from './Progression';
import {Parallelism} from './Parallelism';
import {Fresh} from './Fresh';
import {Outro} from './Outro';
export const TokenForge=()=>{const {fps}=useVideoConfig();return <AbsoluteFill>
 <Audio name="ElevenLabs narration" src={staticFile('narration.mp3')} premountFor={fps}/>
 <Series>
  <Series.Sequence name="TokenForge" durationInFrames={4*fps} premountFor={fps}><Intro/></Series.Sequence>
  <Series.Sequence name="Distinct parallel agents" durationInFrames={14*fps} premountFor={fps}><Strategies/></Series.Sequence>
  <Series.Sequence name="Fixed evaluator" durationInFrames={13*fps} premountFor={fps}><Evaluator/></Series.Sequence>
  <Series.Sequence name="Atlas repair trace" durationInFrames={15*fps} premountFor={fps}><Memory/></Series.Sequence>
  <Series.Sequence name="Measured progression" durationInFrames={9*fps} premountFor={fps}><Progression/></Series.Sequence>
  <Series.Sequence name="Parallelism probe" durationInFrames={13*fps} premountFor={fps}><Parallelism/></Series.Sequence>
  <Series.Sequence name="Fresh held-out tests" durationInFrames={13*fps} premountFor={fps}><Fresh/></Series.Sequence>
  <Series.Sequence name="Working reproducible demo" durationInFrames={9*fps} premountFor={fps}><Outro/></Series.Sequence>
 </Series>
 </AbsoluteFill>};
