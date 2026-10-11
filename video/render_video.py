"""Render the I2I narrated explainer locally. Pillow + bundled FFmpeg only."""
import argparse
import bisect
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
LEAD = 0.65
TAIL = 0.9
OUTPUT = ROOT / 'I2I_Project_Explainer.mp4'
AUDIO_DIR = ROOT / 'audio'
SCENES_PATH = ROOT / 'storyboard.json'
WORK_DIR = ROOT / 'render'
CAPTIONS_PATH = ROOT / 'I2I_Project_Explainer.srt'
CHAPTERS_PATH = ROOT / 'chapters.json'
LANGUAGE = 'eng'


def run(args, log=None):
    result = subprocess.run([FFMPEG, '-hide_banner', '-y', *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if log:
        Path(log).write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-2200:])
    return result


def seconds(path):
    with wave.open(str(path), 'rb') as stream:
        return stream.getnframes() / stream.getframerate()


def prepare_audio(scene):
    sid = int(scene['id'])
    original = AUDIO_DIR / f'scene-{sid:02d}.wav'
    prepared = AUDIO_DIR / f'prepared-{sid:02d}.wav'
    # Gentle register adjustment preserves the duration and the SAPI word timings.
    with wave.open(str(original), 'rb') as stream:
        rate = stream.getframerate()
    filters = (f'asetrate={rate * .94:.3f},aresample=48000,atempo={1 / .94:.9f},'
               'highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=11,'
               f'adelay={int(LEAD * 1000)}:all=1,apad=pad_dur={TAIL}')
    run(['-i', str(original), '-af', filters, '-ar', '48000', '-c:a', 'pcm_s16le', str(prepared)])
    return prepared, seconds(prepared)


def caption_cues(scene, original_duration):
    segments_path = AUDIO_DIR / f"segments-{int(scene['id']):02d}.json"
    if LANGUAGE == 'hin':
        segments = json.loads(segments_path.read_text(encoding='utf-8'))
        # Keep a complete spoken phrase together; long phrases fit two caption lines.
        # This prevents a short trailing word from flashing as a separate caption.
        merged = []
        for s in segments:
            if merged and abs(s['start']-merged[-1]['end']) < .01:
                merged[-1]['text'] += ' '+s['text']
                merged[-1]['end'] = s['end']
            else:
                merged.append(dict(s))
        cues = [{'start': s['start']+LEAD, 'end': s['end']+LEAD-.025, 'text': s['text']} for s in merged]
        assert all(c['start'] < c['end'] <= original_duration+LEAD for c in cues)
        return cues
    words = []
    text = scene['narration']
    cursor = 0
    rows = (AUDIO_DIR / f"words-{int(scene['id']):02d}.tsv").read_text(encoding='utf-8-sig').splitlines()
    for row in rows:
        stamp, word = row.split('\t', 1)
        at = text.find(word, cursor)
        if at < 0:
            at = text.lower().find(word.lower(), cursor)
        if at < 0:
            raise RuntimeError(f'Cannot align speech word {word!r} in scene {scene["id"]}')
        words.append({'t': float(stamp) + LEAD, 'at': at, 'end': at + len(word)})
        cursor = at + len(word)
    assert words and words[-1]['end'] >= len(text.rstrip('.!?')) - 2, 'Narration timing is incomplete'
    assert words[-1]['t'] < original_duration + LEAD, 'Speech engine timing exceeds the actual WAV duration'
    assert all(a['t'] <= b['t'] for a,b in zip(words, words[1:])), 'Speech timing must increase'
    cues = []
    start = 0
    for i, word in enumerate(words):
        end_at = words[i+1]['at'] if i+1 < len(words) else len(text)
        tail = text[word['end']:end_at]
        width = len(text[words[start]['at']:end_at].strip())
        phrase_end = any(p in tail for p in '.!?;')
        next_width = len(text[words[start]['at']:words[i+1]['end']]) if i+1 < len(words) else 0
        if phrase_end or i - start >= 10 or next_width > 105 or i == len(words)-1:
            phrase = text[words[start]['at']:end_at].strip()
            phrase = phrase.replace('I two I', 'I2I').replace('A I', 'AI').replace('J S O N', 'JSON').replace('Fast A P I', 'FastAPI')
            end = words[i+1]['t'] if i+1 < len(words) else original_duration + LEAD
            cues.append({'start': words[start]['t'], 'end': max(end - .025, words[start]['t']+.3), 'text': phrase})
            start = i+1
    assert all(c['start'] < c['end'] <= original_duration+LEAD+.01 for c in cues), 'Invalid caption duration'
    return cues


CAPTION_FONT = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 32)


def wrap(text, font, max_width, draw):
    lines = ['']
    for word in text.split():
        test = f'{lines[-1]} {word}'.strip()
        if draw.textlength(test, font=font) > max_width and lines[-1]:
            lines.append(word)
        else:
            lines[-1] = test
    return lines


def add_caption(base, cue):
    frame = base.copy()
    draw = ImageDraw.Draw(frame)
    if cue:
        lines = wrap(cue, CAPTION_FONT, 1560, draw)
        if len(lines) > 2:
            raise RuntimeError('Caption exceeds two lines: ' + cue)
        height = 44*len(lines)+26
        y = 1050-height
        draw.rounded_rectangle((140, y, 1780, 1054), radius=16, fill='#161a1d', outline='#41494f', width=1)
        for i, line in enumerate(lines):
            x = (1920-draw.textlength(line, font=CAPTION_FONT))/2
            draw.text((x, y+11+i*44), line, font=CAPTION_FONT, fill='#f3f4f3')
    return frame


def timestamp(value):
    millis = round(value*1000)
    h, millis = divmod(millis, 3600000)
    m, millis = divmod(millis, 60000)
    s, ms = divmod(millis, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def render(preview_only=False):
    from render_visuals import render_scene
    try:
        from render_visuals import motion_windows
    except ImportError:
        motion_windows = lambda scene, duration: [(0, 4), (duration*.45, duration*.45+5)] if scene['visual'] in {'motion', 'workspace', 'meeting', 'usage', 'overdue', 'architecture'} else [(0, 4)]
    scenes = json.loads(SCENES_PATH.read_text(encoding='utf-8-sig'))
    work = WORK_DIR
    work.mkdir(exist_ok=True)
    previews = ROOT / ('previews-hinglish' if LANGUAGE == 'hin' else 'previews')
    previews.mkdir(exist_ok=True)
    all_cues = []
    chapters = []
    master = wave.open(str(work / 'narration-master.wav'), 'wb') if not preview_only else None
    if master:
        master.setnchannels(1)
        master.setsampwidth(2)
        master.setframerate(48000)
    offset = 0
    for index, scene in enumerate(scenes):
        sid = int(scene['id'])
        original = AUDIO_DIR / f'scene-{sid:02d}.wav'
        raw_duration = seconds(original)
        if preview_only:
            duration = raw_duration+LEAD+TAIL
            cues = caption_cues(scene, raw_duration)
            base = render_scene(scene, duration*.55, duration, index, len(scenes))
            middle = cues[len(cues)//2]['text']
            add_caption(base, middle).save(previews / f'scene-{sid:02d}.png')
            continue
        prepared, audio_duration = prepare_audio(scene)
        frame_count = math.ceil(audio_duration*FPS)
        duration = frame_count / FPS
        with wave.open(str(prepared), 'rb') as chapter_audio:
            audio_data = chapter_audio.readframes(chapter_audio.getnframes())
        exact_audio_bytes = round(duration * 48000) * 2
        master.writeframes(audio_data[:exact_audio_bytes].ljust(exact_audio_bytes, b'\x00'))
        cues = caption_cues(scene, raw_duration)
        starts = [c['start'] for c in cues]
        for c in cues:
            all_cues.append({**c, 'start': c['start']+offset, 'end': min(c['end'], duration)+offset})
        chapters.append({'id': scene['id'], 'title': scene['chapter'], 'start': offset, 'end': offset+duration})
        target = work / f'chapter-{sid:02d}.mp4'
        log = work / f'chapter-{sid:02d}.log'
        args = [FFMPEG, '-hide_banner', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                '-s', '1920x1080', '-r', str(FPS), '-i', 'pipe:0', '-i', str(prepared),
                '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast',
                '-crf', '22', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
                '-t', f'{duration:.6f}', '-movflags', '+faststart', str(target)]
        windows = motion_windows(scene, duration)
        cache_key = None
        cache_bytes = None
        base_key = None
        base = None
        with log.open('wb') as errors:
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
            try:
                for f in range(frame_count):
                    t = f/FPS
                    visual_t = t
                    for start, end in windows:
                        if start <= t <= end:
                            break
                    else:
                        preceding = [end for start, end in windows if end < t]
                        visual_t = max(preceding) if preceding else 0
                    ci = bisect.bisect_right(starts, t)-1
                    cue_text = cues[ci]['text'] if ci >= 0 and t <= cues[ci]['end'] else None
                    # Static holds share the exact frame bytes; only entry/movement windows redraw.
                    key = (visual_t, cue_text)
                    if key != cache_key:
                        if visual_t != base_key:
                            base = render_scene(scene, visual_t, duration, index, len(scenes))
                            base_key = visual_t
                        frame = add_caption(base, cue_text)
                        assert frame.size == (1920, 1080) and frame.mode == 'RGB'
                        cache_bytes = frame.tobytes()
                        cache_key = key
                    process.stdin.write(cache_bytes)
                process.stdin.close()
                code = process.wait()
            except Exception:
                process.kill()
                process.wait()
                raise
        if code:
            raise RuntimeError(log.read_text(errors='replace')[-1500:])
        mid = duration*.55
        ci = bisect.bisect_right(starts, mid)-1
        frame = add_caption(render_scene(scene, mid, duration, index, len(scenes)), cues[ci]['text'] if ci>=0 else None)
        frame.save(previews / f'scene-{sid:02d}.png')
        offset += duration
        print(f'Encoded scene {sid:02d}/{len(scenes)}: {duration:.1f}s; total {offset:.1f}s', flush=True)
    if preview_only:
        print('Rendered 16 visual/caption previews', flush=True)
        return
    master.close()
    srt = '\n\n'.join(f'{i+1}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for i,c in enumerate(all_cues))+'\n'
    CAPTIONS_PATH.write_text(srt, encoding='utf-8')
    concat = '\n'.join(f"file 'chapter-{int(s['id']):02d}.mp4'\nduration {c['end']-c['start']:.9f}" for s,c in zip(scenes,chapters))
    (work / 'concat.txt').write_text(concat, encoding='utf-8')
    meta = ';FFMETADATA1\ntitle=I2I — Intelligence to Impact\ncomment=HackWave 3.0 project explainer. Synthesized male narration. Illustrated prototype walkthrough.\n'
    for c in chapters:
        meta += f'\n[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(c["start"]*1000)}\nEND={round(c["end"]*1000)}\ntitle={c["title"]}\n'
    (work / 'chapters.ffmetadata').write_text(meta, encoding='utf-8')
    run(['-f', 'concat', '-safe', '0', '-i', str(work/'concat.txt'), '-i', str(work/'narration-master.wav'),
         '-i', str(work/'chapters.ffmetadata'), '-i', str(CAPTIONS_PATH),
         '-map', '0:v:0', '-map', '1:a:0', '-map', '3:0', '-map_metadata', '2', '-map_chapters', '2',
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-c:s', 'mov_text', '-metadata:s:s:0', 'language='+LANGUAGE,
         '-movflags', '+faststart', str(OUTPUT)], work/'final-mux.log')
    CHAPTERS_PATH.write_text(json.dumps(chapters, indent=2), encoding='utf-8')
    print(f'Complete: {OUTPUT}; {offset:.2f}s; {OUTPUT.stat().st_size/1024/1024:.1f} MB', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--previews', action='store_true')
    parser.add_argument('--hinglish', action='store_true')
    args = parser.parse_args()
    if args.hinglish:
        LANGUAGE = 'hin'
        AUDIO_DIR = ROOT / 'audio-hinglish'
        SCENES_PATH = ROOT / 'storyboard-hinglish.json'
        WORK_DIR = ROOT / 'render-hinglish'
        OUTPUT = ROOT / 'I2I_Project_Explainer_Hinglish.mp4'
        CAPTIONS_PATH = ROOT / 'I2I_Project_Explainer_Hinglish.srt'
        CHAPTERS_PATH = ROOT / 'chapters-hinglish.json'
    render(args.previews)
