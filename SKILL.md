---
name: youtube-production-engine
description: Research and produce YouTube videos using reusable channel profiles, local narration, timed scene plans, image prompts, packaging and portable MP4 rendering. Use for a video production workflow or creating a new video direction; review requests remain read-only.
metadata:
  version: "1.0.0"
---

# YouTube production engine

Separate production mechanics from channel choices. Communicate in the user's language; use the selected profile's content language for narration and public metadata. Resolve all bundled paths relative to this skill, never a username, drive or current working directory.

## Start and route

1. Discover tools actually available for research, image generation and optional editing. Do not assume a particular agent API or service exists.
2. Read [runtime](references/runtime.md) when setting up or executing helpers. Run `python scripts/engine.py doctor` from this skill folder. Read-only research, profile creation and prompt validation need only Python; voice/render use an isolated runtime installed by `bootstrap`.
3. Select a profile explicitly requested by the user, or retain the current project's snapshot. Do not silently apply Paleon to another channel. If no direction is given, ask one focused question about the intended audience/topic while preparing independent work.
4. Read [editorial](references/editorial.md) for research, writing, packaging or analytics. Read [profiles](references/profiles.md) when creating/editing a direction. Read [production](references/production.md) for voice, scenes, images or rendering.

| Request | Scope |
|---|---|
| Ideas / start | About five distinct audience questions with evidence feasibility; user chooses unless choice is delegated |
| New direction / profile | Define audience, topic boundaries, promise, voice, visual style and packaging; save a new profile |
| Topic / produce | Research, narration, voice, timed scenes, image prompts and metadata; generate images when supported and within authorized services/budget |
| Voice / audition | Selected narration or same-text voice comparisons |
| Scenes / prompts | Use existing audio and precise timing; preserve voice |
| Assemble / render | Validate supplied assets and render local MP4 |
| Review | Inspect/evaluate only; do not install dependencies or alter project assets |
| Analytics | Separate observations, hypotheses and one meaningful next experiment |

A general production request proceeds through packaging without repeated permission questions. Local rendering follows when requested. Never equate local production with permission to publish, purchase credits or alter public metadata. If a required service is unavailable, finish independent deliverables and report the exact missing step; never label prompts as generated images or a draft as a verified video.

## Project contract

Initialize a new dedicated directory with `engine.py init --profile paleon --project <new-directory> --topic <topic>`. This snapshots the profile as `profile.json` and records relative artifact paths in `project.json`. `--profile` also accepts an external JSON profile. Existing directories are rejected to protect prior work.

Work within that project and explicitly supplied references. Do not scan other video project directories. Shared engine code, selected profiles and model/runtime caches are allowed. Reuse brand assets and explicit experiment records when authorized; do not copy another creator's wording or prior scripts.

Produce `research.md`, spoken-only `script.txt`, `voiceover.wav`, `voiceover.srt`, `transcript_timestamped.txt`, `scenes.json`, `image_prompts.txt`, `image_prompts_no_timestamps.txt`, `metadata.md` and final images under `images/`. Rendering writes `video.mp4`. Optional outputs and review evidence belong in `production_report.md`. The project manifest names expected artifacts, not proof that stages completed.

## Invariants

- Research before committing to a premise; trace material claims to sources actually read. Mark reconstruction and uncertainty.
- Preserve explicit user choices and per-project overrides. Snapshot settings so later profile edits do not change an existing video.
- Timing comes from actual audio/SRT. Rounded transcript labels are not alignment data. Scenes may group multiple speech cues.
- Use scene IDs and explicit image filenames, never download order. Validate complete contiguous coverage against actual WAV duration before rendering.
- Style belongs to the profile. Do not hard-code doodles, a character, a voice, five dramatic angles or an ancestral story into the shared engine.
- Review actual audio/images when tools permit. Report technical validation separately from listening, visual review and playback.
- No promises of CTR, retention, virality or revenue. Preserve one principal variable in a controlled experiment.

## Portability boundary

The download is self-contained instructions, profiles and helpers, not a bundled agent, Python distribution or image service. Supported runtime target: Python 3.11–3.13 on Windows, macOS and Linux where dependency wheels are available. First voice/render use needs internet and writable user cache; subsequent use can be offline once assets and dependencies exist. The package does not claim all operating systems have been tested. CapCut is optional and not a required dependency.
