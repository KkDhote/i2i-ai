# I2I project explainer

The finished video is `I2I_Project_Explainer.mp4`: a detailed English explainer in the project's charcoal, red, yellow, green and light-blue palette. It covers the problem statement, aim, proposed solution, three scenarios, architecture, component selection, user control, motion, assistant, research, proposed priority scoring, limitations and next steps.

The workspace scenes are original illustrative diagrams using sample data. They are not recordings of a production customer workspace. The research references are in `research-notes.md`; narration and the editable scene data are in `narration.md` and `storyboard.json`. DTPS and usability evaluation are clearly presented as proposed work. Example B is corrected to 43.75 for the supplied inputs.

## Narration and captions

The full script is narrated locally with the Microsoft David male voice, using a lower register and a moderate documentary pace. This is synthesized speech. The complete project narration was not uploaded to a cloud speech service. SAPI word-boundary timings drive the visible captions and the separate `I2I_Project_Explainer.srt` file. The MP4 also includes an English subtitle track and sixteen chapter markers.

## Rebuild locally

Use Python with Pillow and `imageio-ffmpeg`, plus Windows System.Speech. The existing dependency bundle provides Python and Pillow; the encoder package is installed in `video/tools`.

```powershell
./video/generate_voice_local.ps1
python video/render_video.py --previews
python video/render_video.py
```

`render_visuals.py` generates original graphics. `render_video.py` normalizes narration, renders 1920×1080 at 30 frames per second, encodes H.264/AAC, and writes captions and chapters. Generated audio, preview frames, tools and intermediate chapters stay outside Git through this folder's ignore file. The final video remains on disk for playback and sharing.

## Claim boundaries

The current code supports goal-specific card plans, task APIs, assistant state continuity, refinements, clarification, reasons, native animations, reduced motion, themes and fallback rules. Sample business information is disclosed; tasks are in memory. External publications inform the design, but their study results do not establish I2I's performance. No I2I user-study results or productivity percentages are invented.

## Hinglish version

`I2I_Project_Explainer_Hinglish.mp4` keeps the sixteen chapters and original diagrams, with Hindi sentence structure and familiar English technical terms. Its captions use Roman Hinglish. `hinglish-script.txt` contains paired caption and phonetic Hindi narration text; `narration-hinglish.md` is the readable script.

The Hindi-capable neural voice runs locally through Piper (`piper-tts`, GPL-3.0) using `hi_IN-pratham-medium`. Model source: [Rhasspy Piper voices](https://huggingface.co/rhasspy/piper-voices/tree/main/hi/hi_IN/pratham/medium). Training credit: [PravalX](https://github.com/PravalX); dataset: [AI4Bharat IndicNLP corpus](https://github.com/AI4Bharat/indicnlp_corpus). The model card lists a CC BY-NC-SA 4.0 dataset license. The model card is preserved in `video/voices/MODEL_CARD`. Narration is generated on the device; no project script is uploaded. Captions align to individually synthesized spoken phrases.

```powershell
python video/generate_hinglish.py
python video/render_video.py --hinglish --previews
python video/render_video.py --hinglish
```
