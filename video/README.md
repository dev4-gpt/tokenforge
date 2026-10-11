# TokenForge submission video

90-second, 1920×1080, 30 fps visual demo with ElevenLabs narration.

## Reproduce

From the repository root, export validated evidence:

```sh
python scripts/prepare_video.py
cd video
npm ci
npm run lint
npx remotion render src/index.ts TokenForge out/tokenforge-90s.mp4 --codec h264
ffmpeg -i out/tokenforge-90s.mp4 -t 89 -c copy -movflags +faststart out/tokenforge-submission.mp4
```

`npm run dev` opens the editable scene timeline. The eight scenes cover the baseline, agent strategies, evaluator, actual Atlas repair trace, development progression, matched parallelism probe, original held-out result, and working dashboard.

The charts use the validated run bundle through `src/evidence.json`. Dashboard images are actual UI captures. This is an animated explanation of recorded experiments, not a recording of a newly running optimization session. Original champion and held-out artifacts remain unchanged.

Narration was generated through ElevenLabs with the selected CEO-grade, enterprise version voice and Eleven v4. The original 104.20-second generation was paced with FFmpeg `atempo=1.18` and loudness normalized to produce 88.31 seconds, without changing pitch. The composition has a short closing hold and is 90 seconds long. The submission file trims only this hold to 89.07 seconds, avoiding encoder padding that YouTube rounds up to 1:31. The complete narration is retained.

`public/narration.mp3` and UI captures are included. The original generation and rendered output are local, ignored artifacts.
