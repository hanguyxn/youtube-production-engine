import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import engine
import models


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = engine.init_project(self.base / 'video', 'general-explainer', 'A test question')
        with wave.open(str(self.project / 'voiceover.wav'), 'wb') as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(b'\0\0' * 24000 * 2)
        (self.project / 'voiceover.srt').write_text('1\n00:00:00,000 --> 00:00:00,800\nFirst thought.\n\n2\n00:00:01,000 --> 00:00:01,900\nSecond thought.\n', encoding='utf-8')
        engine.scene_seed(self.project)
        self.plan = engine.read_json(self.project / 'scenes.json')
        profile = engine.read_json(self.project / 'profile.json')
        for scene in self.plan['scenes']:
            scene['prompt'] = profile['visual']['style_anchor'] + ' a meaningful example, ' + profile['visual']['style_lock']
        self.save()

    def save(self):
        engine.write_json(self.project / 'scenes.json', self.plan)

    def test_profile_snapshot_and_existing_project_preserved(self):
        before = (self.project / 'profile.json').read_bytes()
        with self.assertRaises(FileExistsError):
            engine.init_project(self.project, 'paleon', 'Other topic')
        self.assertEqual((self.project / 'profile.json').read_bytes(), before)
        self.assertNotIn(str(ROOT), (self.project / 'project.json').read_text())

    def test_template_and_unsupported_local_language_rejected(self):
        with self.assertRaises(ValueError):
            engine.validate_profile(engine.read_json(ROOT / 'profiles/template.json'))
        p = engine.read_json(ROOT / 'profiles/paleon.json')
        p['language'] = 'vi'
        with self.assertRaises(ValueError):
            engine.validate_profile(p)

    def test_scene_seed_covers_pauses_and_tail(self):
        self.assertEqual([(s['start'], s['end']) for s in self.plan['scenes']], [(0, 1), (1, 2)])
        engine.validate_project(self.project, require_images=False)

    def test_invalid_scene_timing_cue_ranges_and_styles_rejected(self):
        original = copy.deepcopy(self.plan)
        for field, value in [('start', .3), ('end', 1.5), ('end', float('nan')), ('cue_end', 2), ('prompt', 'Wrong style')]:
            with self.subTest(field=field, value=value):
                self.plan = copy.deepcopy(original)
                self.plan['scenes'][0][field] = value
                self.save()
                with self.assertRaises(ValueError):
                    engine.validate_project(self.project, require_images=False)

    def test_no_missing_images_or_escaped_paths(self):
        with self.assertRaises(ValueError):
            engine.validate_project(self.project)
        for path in ['../outside.png', '/absolute.png', 'C:/outside.png', '..\\outside.png']:
            self.plan['scenes'][0]['image'] = path
            self.save()
            with self.assertRaises(ValueError):
                engine.validate_project(self.project, require_images=False)

    def test_cue_spanning_multiple_scenes_is_valid(self):
        first = self.plan['scenes'][0]
        second = copy.deepcopy(first)
        first['end'] = .4
        second.update(id='extra', start=.4, end=1)
        self.plan['scenes'].insert(1, second)
        self.save()
        engine.validate_project(self.project, require_images=False)

    def test_new_style_is_not_forced_to_doodle(self):
        engine.validate_project(self.project, require_images=False)
        self.assertIn('Clean flat editorial', (self.project / 'image_prompts.txt').read_text())
        self.assertNotIn('[00:', (self.project / 'image_prompts_no_timestamps.txt').read_text())

    def test_model_corruption_rejected_without_download(self):
        cache = self.base / 'models'
        cache.mkdir()
        (cache / 'kokoro-v1.0.onnx').write_bytes(b'broken')
        with patch.object(models.urllib.request, 'urlopen') as request:
            with self.assertRaises(ValueError):
                models.ensure_models(cache)
            request.assert_not_called()

    def test_download_checksum_failure_leaves_no_model_or_temporary_file(self):
        import io
        cache = self.base / 'download'
        with patch.object(models.urllib.request, 'urlopen', return_value=io.BytesIO(b'incorrect download')):
            with self.assertRaises(ValueError):
                models.ensure_models(cache)
        self.assertEqual(list(cache.iterdir()), [])

    def test_relocated_skill_and_unrelated_working_directory(self):
        relocated = self.base / 'skill with spaces'
        shutil.copytree(ROOT, relocated, ignore=shutil.ignore_patterns('__pycache__'))
        result = subprocess.run([sys.executable, '-B', str(relocated / 'scripts/engine.py'), 'profile-check', '--profile', 'paleon'], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, '-B', str(relocated / 'scripts/engine.py'), 'validate', '--project', str(self.project), '--prompts-only'], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_render_failure_preserves_previous_video(self):
        # Decode may fail; the final file must survive an intentional replacement attempt.
        for s in self.plan['scenes']:
            (self.project / s['image']).write_bytes(b'not an image')
        out = self.project / 'video.mp4'
        out.write_bytes(b'previous final')
        with patch.object(engine, 'ffmpeg_executable', return_value='ffmpeg'), patch.object(engine.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'ffmpeg')):
            with self.assertRaises(subprocess.CalledProcessError):
                engine.render_video(self.project, force=True)
        self.assertEqual(out.read_bytes(), b'previous final')


if __name__ == '__main__':
    unittest.main()
