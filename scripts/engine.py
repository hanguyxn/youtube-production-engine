"""Portable video project CLI; management commands use Python standard library only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import venv
import wave

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def cache_root():
    override = os.environ.get('YOUTUBE_ENGINE_CACHE')
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Caches'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    return base / 'youtube-production-engine'


def runtime_paths():
    key = ROOT.joinpath('requirements.txt').read_bytes() + f'{sys.version_info[:2]}-{sys.platform}-{platform.machine()}'.encode()
    directory = cache_root() / 'runtimes' / hashlib.sha256(key).hexdigest()[:16]
    python = directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return directory, python


def bootstrap(allow_setup=True):
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        raise ValueError('Voice/render runtime supports Python 3.11–3.13. Management commands need Python 3.10+.')
    directory, python = runtime_paths()
    marker = directory / 'ready.json'
    if marker.is_file() and python.is_file():
        return python
    if not allow_setup:
        raise ValueError('Runtime not prepared. Run bootstrap online first, or omit --no-setup.')
    directory.parent.mkdir(parents=True, exist_ok=True)
    print(f'Preparing isolated runtime: {directory}', flush=True)
    venv.EnvBuilder(with_pip=True).create(directory)
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(ROOT / 'requirements.txt')], check=True)
    subprocess.run([str(python), '-c', 'import kokoro_onnx, numpy, soundfile, onnxruntime, imageio_ffmpeg'], check=True)
    write_json(marker, {'python': sys.version, 'requirements': ROOT.joinpath('requirements.txt').read_text()})
    return python


def runtime_command(args):
    python = bootstrap(not args.no_setup)
    child = list(sys.argv[1:])
    env = dict(os.environ, YOUTUBE_ENGINE_RUNTIME='1', YOUTUBE_ENGINE_CACHE=str(cache_root()))
    return subprocess.run([str(python), str(Path(__file__).resolve()), *child], env=env).returncode


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text.')


def positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be finite and positive.')


def inside(base, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or re.match(r'^[A-Za-z]:', relative) or '\\' in relative:
        raise ValueError('Use a nonempty project-relative path with forward slashes.')
    base = Path(base).resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base) or path == base:
        raise ValueError(f'Path escapes project/profile directory: {relative}')
    return path


def validate_profile(p):
    if p.get('schema_version') != 1 or p.get('ready') is not True:
        raise ValueError('Profile requires schema_version 1 and ready true; complete the template first.')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', p.get('id', '')):
        raise ValueError('Profile id must be a lowercase slug.')
    for name in ['name', 'audience', 'viewer_promise', 'language']:
        text(p.get(name), name)
    for name in ['topic_scope']:
        if not isinstance(p.get(name), list) or not p[name]:
            raise ValueError(f'{name} must be a nonempty list.')
        for item in p[name]:
            text(item, name)
    ed, voice, visual, packaging, render = [p.get(k, {}) for k in ['editorial', 'voice', 'visual', 'packaging', 'render']]
    if not all(isinstance(v, dict) for v in [ed, voice, visual, packaging, render]):
        raise ValueError('Profile sections must be objects.')
    text(ed.get('tone'), 'editorial.tone')
    target = ed.get('target_minutes')
    if not isinstance(target, list) or len(target) != 2:
        raise ValueError('target_minutes must be [minimum, maximum].')
    for value in target:
        positive(value, 'target_minutes')
    if target[0] > target[1]:
        raise ValueError('target_minutes is reversed.')
    if voice.get('provider') not in ['kokoro', 'external']:
        raise ValueError('voice.provider must be kokoro or external.')
    text(voice.get('id'), 'voice.id')
    text(voice.get('language'), 'voice.language')
    positive(voice.get('speed'), 'voice.speed')
    if voice['provider'] == 'kokoro' and (p['language'] != 'en' or voice['language'] not in ['en-us', 'en-gb']):
        raise ValueError('Local Kokoro helper supports English; select external for other languages.')
    text(visual.get('style_anchor'), 'visual.style_anchor')
    if not all(isinstance(visual.get(k), str) for k in ['style_lock', 'character']):
        raise ValueError('visual.style_lock and character must be strings (may be empty).')
    if visual.get('aspect_ratio') != '16:9':
        raise ValueError('This renderer supports 16:9 profiles.')
    count = packaging.get('thumbnail_concepts')
    if type(count) is not int or not 1 <= count <= 10:
        raise ValueError('thumbnail_concepts must be an integer from 1 to 10.')
    if not isinstance(packaging.get('angles'), list) or not packaging['angles']:
        raise ValueError('packaging.angles must be a nonempty list.')
    for angle in packaging['angles']:
        text(angle, 'packaging angle')
    for k in ['width', 'height', 'fps']:
        positive(render.get(k), f'render.{k}')
        if type(render[k]) is not int:
            raise ValueError(f'render.{k} must be an integer.')
    if render['width'] % 2 or render['height'] % 2 or render['width'] * 9 != render['height'] * 16:
        raise ValueError('Render dimensions must be even and 16:9.')
    return p


def profile_path(value):
    candidate = Path(value)
    if candidate.is_file():
        return candidate.resolve()
    if not re.fullmatch(r'[a-z0-9-]+', value):
        raise ValueError(f'Profile does not exist: {value}')
    return ROOT / 'profiles' / f'{value}.json'


def init_project(directory, profile, topic):
    text(topic, 'topic')
    source = profile_path(profile)
    p = validate_profile(read_json(source))
    logo = p.get('assets', {}).get('logo')
    logo_source = inside(source.parent, logo) if logo else None
    if logo_source and not logo_source.is_file():
        raise ValueError(f'Missing logo: {logo_source}')
    project = Path(directory).resolve()
    project.mkdir(parents=True, exist_ok=False)
    (project / 'images').mkdir()
    if logo_source:
        (project / 'assets').mkdir()
        target = 'assets/logo' + logo_source.suffix.lower()
        shutil.copyfile(logo_source, project / target)
        p['assets']['logo'] = target
    write_json(project / 'profile.json', p)
    artifacts = {k: v for k, v in [('research', 'research.md'), ('script', 'script.txt'), ('voice', 'voiceover.wav'), ('captions', 'voiceover.srt'), ('scenes', 'scenes.json'), ('metadata', 'metadata.md'), ('video', 'video.mp4')]}
    write_json(project / 'project.json', {'schema_version': 1, 'topic': topic, 'profile': 'profile.json', 'artifacts': artifacts})
    print(f'Initialized: {project}')
    return project


def project_data(directory):
    project = Path(directory).resolve()
    manifest = read_json(project / 'project.json')
    if manifest.get('schema_version') != 1 or manifest.get('profile') != 'profile.json':
        raise ValueError('Unsupported project manifest.')
    return project, validate_profile(read_json(project / 'profile.json'))


def wav_duration(path):
    with wave.open(str(path), 'rb') as audio:
        duration = audio.getnframes() / audio.getframerate()
    positive(duration, 'audio duration')
    return duration


def captions(project):
    from align_timestamps import parse_srt_or_vtt
    cues = parse_srt_or_vtt((project / 'voiceover.srt').read_text(encoding='utf-8-sig'))
    if not cues:
        raise ValueError('No speech cues found.')
    return cues


def scene_seed(directory):
    project, _ = project_data(directory)
    out = project / 'scenes.json'
    if out.exists():
        raise ValueError('scenes.json exists; edit it rather than overwriting the plan.')
    duration, cues = wav_duration(project / 'voiceover.wav'), captions(project)
    if cues[-1][1] > duration + .02:
        raise ValueError('SRT extends past audio duration.')
    scenes = []
    for i, cue in enumerate(cues):
        scenes.append({'id': f'{i+1:03d}', 'start': 0.0 if i == 0 else cue[0], 'end': cues[i+1][0] if i+1 < len(cues) else duration,
                       'image': f'images/{i+1:03d}.png', 'cue_start': i+1, 'cue_end': i+1, 'prompt': '', 'notes': cue[2]})
    write_json(out, {'schema_version': 1, 'scenes': scenes})
    print('Scene seed created. Write meaningful prompts and refine the visual beats before validation.')


def validate_project(directory, require_images=True, export=True):
    project, p = project_data(directory)
    duration, cues = wav_duration(project / 'voiceover.wav'), captions(project)
    if cues[-1][1] > duration + .02:
        raise ValueError('Speech captions extend beyond the WAV.')
    plan = read_json(project / 'scenes.json')
    scenes = plan.get('scenes')
    if plan.get('schema_version') != 1 or not isinstance(scenes, list) or not scenes:
        raise ValueError('Scene manifest requires schema_version 1 and nonempty scenes.')
    previous, ids = 0.0, set()
    prompt_lines, raw_lines = [], []
    for scene in scenes:
        ident = scene.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', ident) or ident in ids:
            raise ValueError('Scene IDs must be safe unique strings.')
        ids.add(ident)
        start, end = scene.get('start'), scene.get('end')
        for v in [start, end]:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f'{ident}: non-finite scene time.')
        if start < 0 or end <= start or abs(start - previous) > .02:
            raise ValueError(f'{ident}: scenes must be positive and contiguous from zero.')
        if end > duration + .02:
            raise ValueError(f'{ident}: scene exceeds audio duration.')
        a, b = scene.get('cue_start'), scene.get('cue_end')
        if type(a) is not int or type(b) is not int or not 1 <= a <= b <= len(cues):
            raise ValueError(f'{ident}: invalid cue range.')
        overlapping = [i+1 for i, cue in enumerate(cues) if cue[0] < end - .001 and cue[1] > start + .001]
        if overlapping and (a != min(overlapping) or b != max(overlapping)):
            raise ValueError(f'{ident}: cue range must match all overlapping speech cues.')
        prompt = scene.get('prompt')
        text(prompt, f'{ident}.prompt')
        if '\n' in prompt or '\r' in prompt:
            raise ValueError(f'{ident}: keep each prompt on one line.')
        visual = p['visual']
        if not prompt.startswith(visual['style_anchor']) or (visual['style_lock'] and visual['style_lock'] not in prompt):
            raise ValueError(f'{ident}: prompt must use this profile style anchor and lock.')
        image = inside(project, scene.get('image'))
        if require_images and not image.is_file():
            raise ValueError(f'{ident}: missing image {image}')
        rounded = int(round(start))
        prompt_lines.append(f'[{rounded // 60:02d}:{rounded % 60:02d}] {prompt}')
        raw_lines.append(prompt)
        previous = end
    if abs(previous - duration) > .02:
        raise ValueError('Scene coverage does not reach audio end.')
    if export:
        (project / 'image_prompts.txt').write_text('\n\n'.join(prompt_lines) + '\n', encoding='utf-8')
        (project / 'image_prompts_no_timestamps.txt').write_text('\n\n'.join(raw_lines) + '\n', encoding='utf-8')
    return project, p, scenes, duration


def voice(directory, force=False, allow_download=True):
    from models import ensure_models
    project, p = project_data(directory)
    settings = p['voice']
    if settings['provider'] != 'kokoro':
        raise ValueError('External voice selected: provide voiceover.wav plus matching voiceover.srt using your configured provider.')
    outputs = ['voiceover.wav', 'voiceover.srt', 'transcript_timestamped.txt']
    if not force and any((project / name).exists() for name in outputs):
        raise ValueError('Voice outputs exist; use --force for intentional regeneration.')
    if not (project / 'script.txt').is_file() or not (project / 'script.txt').read_text(encoding='utf-8-sig').strip():
        raise ValueError('Write a nonempty spoken-only script.txt first.')
    import tts_kokoro as tts
    if settings['id'] not in tts.VOICES:
        raise ValueError(f'Unsupported local voice: {settings["id"]}')
    expected_language = 'en-gb' if settings['id'].startswith('b') else 'en-us'
    if settings['language'] != expected_language:
        raise ValueError('Voice language does not match selected English voice.')
    model, voices = ensure_models(cache_root() / 'models' / 'kokoro-v1.0', allow_download)
    tts.MODEL_FILE, tts.VOICES_FILE = model, voices
    with tempfile.TemporaryDirectory(prefix='.voice-', dir=project) as temp:
        wav, transcript, srt, duration = tts.generate_voice(str(project / 'script.txt'), str(Path(temp) / 'voiceover.wav'), settings['id'], settings['speed'])
        for source, target in [(wav, outputs[0]), (transcript, outputs[2]), (srt, outputs[1])]:
            os.replace(source, project / target)
    print(f'Voice generated: {duration:.3f}s. Listening QA remains separate.')


def ffmpeg_executable():
    custom = os.environ.get('YOUTUBE_ENGINE_FFMPEG')
    if custom:
        if not Path(custom).is_file():
            raise ValueError('YOUTUBE_ENGINE_FFMPEG must name an existing executable file.')
        return custom
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def render_video(directory, force=False):
    project, p, scenes, duration = validate_project(directory)
    output = project / 'video.mp4'
    if output.exists() and not force:
        raise ValueError('video.mp4 exists; use --force to replace intentionally.')
    ffmpeg = ffmpeg_executable()
    settings = p['render']
    fps, width, height = settings['fps'], settings['width'], settings['height']
    def run(command):
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', *command], check=True)
    with tempfile.TemporaryDirectory(prefix='.render-', dir=project) as temp:
        temp = Path(temp)
        concat = []
        frame_cursor = 0
        for i, scene in enumerate(scenes):
            # Quantize cumulative endpoints to avoid accumulating per-scene drift.
            frame_end = max(frame_cursor + 1, round(scene['end'] * fps))
            frames = frame_end - frame_cursor
            frame_cursor = frame_end
            segment = temp / f'{i:06d}.mp4'
            run(['-loop', '1', '-i', str(inside(project, scene['image'])), '-vf',
                 f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1',
                 '-frames:v', str(frames), '-r', str(fps), '-an', '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', str(segment)])
            concat.append(f"file '{segment.name}'")
        if abs(frame_cursor / fps - duration) > max(.1, 2 / fps):
            raise ValueError('Too many sub-frame scenes; regroup them to prevent timing drift.')
        (temp / 'segments.txt').write_text('\n'.join(concat), encoding='utf-8')
        final = temp / 'video.mp4'
        run(['-f', 'concat', '-safe', '1', '-i', str(temp / 'segments.txt'), '-i', str(project / 'voiceover.wav'),
             '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-t', f'{duration:.6f}', '-movflags', '+faststart', str(final)])
        import imageio_ffmpeg
        # Use the same executable for inspection as for rendering.
        prior_ffmpeg = os.environ.get('IMAGEIO_FFMPEG_EXE')
        os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg
        reader = imageio_ffmpeg.read_frames(str(final))
        try:
            metadata = next(reader)
        finally:
            reader.close()
            if prior_ffmpeg is None:
                os.environ.pop('IMAGEIO_FFMPEG_EXE', None)
            else:
                os.environ['IMAGEIO_FFMPEG_EXE'] = prior_ffmpeg
        if abs(metadata['duration'] - duration) > max(.15, 2 / fps):
            raise ValueError('Rendered duration differs from narration; final output not replaced.')
        # Decode both complete streams before promoting the temporary output.
        run(['-i', str(final), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
        os.replace(final, output)
    print(f'Rendered: {output}. Technical duration check passed; playback review remains separate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    sub.add_parser('bootstrap')
    check = sub.add_parser('profile-check')
    check.add_argument('--profile', required=True)
    init = sub.add_parser('init')
    init.add_argument('--profile', required=True)
    init.add_argument('--project', required=True)
    init.add_argument('--topic', required=True)
    for cmd in ['voice', 'scene-seed', 'validate', 'render']:
        command = sub.add_parser(cmd)
        command.add_argument('--project', required=True)
        if cmd in ['voice', 'render']:
            command.add_argument('--force', action='store_true')
            command.add_argument('--no-setup', action='store_true')
        if cmd == 'validate':
            command.add_argument('--prompts-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.command in ['voice', 'render'] and os.environ.get('YOUTUBE_ENGINE_RUNTIME') != '1':
            return runtime_command(args)
        if args.command == 'doctor':
            directory, python = runtime_paths()
            print(json.dumps({'python': sys.version, 'platform': platform.platform(), 'skill_root': str(ROOT), 'cache': str(cache_root()),
                              'runtime_ready': python.is_file() and (directory / 'ready.json').is_file(),
                              'runtime_supported': (3, 11) <= sys.version_info[:2] <= (3, 13),
                              'models_cached': all((cache_root() / 'models' / 'kokoro-v1.0' / name).is_file() for name in ['kokoro-v1.0.onnx', 'voices-v1.0.bin']),
                              'external_capabilities': 'Research/image services are discovered by the host agent, not by this CLI.'}, indent=2))
        elif args.command == 'bootstrap':
            print(bootstrap())
        elif args.command == 'profile-check':
            p = validate_profile(read_json(profile_path(args.profile)))
            print(f'Valid profile: {p["id"]}')
        elif args.command == 'init':
            init_project(args.project, args.profile, args.topic)
        elif args.command == 'voice':
            voice(args.project, args.force, not args.no_setup)
        elif args.command == 'scene-seed':
            scene_seed(args.project)
        elif args.command == 'validate':
            _, _, scenes, duration = validate_project(args.project, not args.prompts_only)
            print(f'Validated {len(scenes)} scenes covering {duration:.3f}s; prompts exported.')
        elif args.command == 'render':
            render_video(args.project, args.force)
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError, RuntimeError, wave.Error) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
