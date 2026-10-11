"""Hinglish narration with a Hindi neural voice, entirely on this device."""
from pathlib import Path
import argparse
import io
import json
import sys
import wave

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))


def load_script():
    scenes = json.loads((ROOT/'storyboard.json').read_text(encoding='utf-8-sig'))
    by_id = {int(s['id']):s for s in scenes}
    current = None
    for line in (ROOT/'hinglish-script.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        if line.startswith('@'):
            current = by_id[int(line[1:])]
            current['speech_segments'] = []
        else:
            roman, hindi = line.split('||',1)
            assert current is not None and roman.strip() and hindi.strip()
            current['speech_segments'].append({'caption':roman.strip(),'speech':hindi.strip()})
    for s in scenes:
        assert s.get('speech_segments')
        s['narration'] = ' '.join(p['caption'] for p in s['speech_segments'])
    (ROOT/'storyboard-hinglish.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding='utf-8')
    md = '# I2I — Hinglish narration\n\nHindi sentence structure with familiar English technical terms. Locally generated male narration.\n\n'
    for s in scenes:
        md += f"## {s['id']} — {s['chapter']}\n\n{s['narration']}\n\n"
    (ROOT/'narration-hinglish.md').write_text(md,encoding='utf-8')
    return scenes


def generate(test=False, script_only=False):
    scenes = load_script()
    if script_only:
        print('Validated 16 Hinglish chapters',flush=True)
        return
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(str(ROOT/'voices/hi_IN-pratham-medium.onnx'))
    config = SynthesisConfig(length_scale=1.05, noise_scale=.55, noise_w_scale=.65, normalize_audio=True)
    audio_dir = ROOT/'audio-hinglish'
    audio_dir.mkdir(exist_ok=True)
    selected = scenes[:1] if test else scenes
    for scene in selected:
        path = audio_dir/f"scene-{int(scene['id']):02d}.wav"
        cues = []
        all_frames = []
        offset = 0
        rate = voice.config.sample_rate
        for segment in scene['speech_segments']:
            buffer = io.BytesIO()
            with wave.open(buffer,'wb') as out:
                voice.synthesize_wav(segment['speech'],out,syn_config=config)
            buffer.seek(0)
            with wave.open(buffer,'rb') as source:
                assert source.getnchannels()==1 and source.getsampwidth()==2
                raw = source.readframes(source.getnframes())
                rate = source.getframerate()
                duration = len(raw)/(2*rate)
            assert duration>.2, 'Speech segment is empty'
            # A complete caption follows its separately synthesized spoken phrase.
            cues.append({'start':offset,'end':offset+duration,'text':segment['caption']})
            all_frames.extend([raw,b'\0\0'*round(rate*.18)])
            offset += duration+.18
        with wave.open(str(path),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
            out.writeframes(b''.join(all_frames))
        (audio_dir/f"segments-{int(scene['id']):02d}.json").write_text(json.dumps(cues,indent=2),encoding='utf-8')
        print(f"Hinglish scene {scene['id']}: {offset:.1f}s, {len(cues)} captions",flush=True)
    (audio_dir/'voice-metadata.json').write_text(json.dumps({
        'provider':'Piper on-device neural speech synthesis', 'voice':'hi_IN-pratham-medium',
        'language':'Hinglish', 'model_source':'https://huggingface.co/rhasspy/piper-voices',
        'cloud_upload':False,'generated_speech':True,
        'captions':'Complete phrases aligned to individually synthesized audio'},indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--test',action='store_true')
    parser.add_argument('--script-only',action='store_true')
    args=parser.parse_args()
    generate(args.test,args.script_only)
