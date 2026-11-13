# Voice, scenes and render

## Voice

Use the project snapshot's provider, voice ID, language and speed. Paleon's existing default is Kokoro `am_michael`, speed 1.0, US English. Do not ask for that choice again. A new voice merits a 70–110 word same-text audition, including a number and relevant pronunciation checks. Compare phrasing, clarity and fatigue from actual listening; a model grade or waveform is not a listening verdict. If no listening tool exists, provide playable samples and state the limit.

`engine.py voice` runs the bundled Kokoro helper inside the cached runtime and normalizes artifact names to the project contract. Local Kokoro supports the bundled English voice list only. For other languages/providers, generate externally using available tools and user-configured services; do not silently change language. Preserve existing audio unless `--force` is supplied. Check text completeness and names, the opening, a dense passage and ending. Chunk failure aborts without replacing prior audio. WAV peaks are limited with one uniform gain, not per-chunk normalization or loudness matching.

SRT represents synthesis chunks, not word-level forced alignment. The rounded transcript is a reading convenience. Timed scene data always uses numeric seconds from SRT/audio. `scene-seed` creates one scene per cue and extends each image through the next cue's start (final scene to WAV end), covering intentional speech pauses. This is a mechanical seed only: prompts are blank, so validation fails until the agent supplies meaningful visual direction. Group or split scenes according to the explanation, not fixed image quotas. Original speech SRT remains unchanged.

## Scene contract

`scenes.json`:

```json
{
  "schema_version": 1,
  "scenes": [
    {"id": "001", "start": 0.0, "end": 4.2,
     "image": "images/001.png", "cue_start": 1, "cue_end": 2,
     "prompt": "The selected profile's style anchor, followed by specific visual content", "notes": "Meaning, evidence/reconstruction label and continuity"}
  ]
}
```

Scene intervals must be finite, positive, ordered and contiguous from 0 to measured WAV duration (20 ms tolerance). Stable IDs are unique, image paths stay within the project, and cue ranges refer to the unchanged source SRT. A cue may span several scenes; every overlapping speech cue must be represented by that scene's range. Validator checks cue coverage as well as timing. Scene filenames are explicit, not inferred from timestamps or download order.

Every prompt starts with `visual.style_anchor`, contains `visual.style_lock` when nonempty, and describes the actual spoken explanation. Include `visual.character` in human character scenes and generate a reference image first when supported. Alternate evidence, demonstration, comparison and consequence as useful. Keep adjacent setting/props coherent. For scientific details use labeled diagrams instead of relying on stylized bodies to carry anatomy.

`validate --prompts-only` checks scenes, timing and style and exports prompt text without requiring images; it does not certify semantics. `validate` additionally requires all final images. Rounded labels in prompt text may coincide for subsecond scenes; scenes.json numeric timing is authoritative, and no scene is dropped or shifted. Prompt exports are generated from this manifest, not parsed back into timing.

Generate images with an available authorized tool or hand off the exported prompts. Save images to the manifest's paths. Review actual images for period/location, scientific accuracy, continuity and readability. Mere file existence is not visual QA.

## Rendering and delivery

The portable renderer validates the complete manifest, makes static 16:9 image segments with letterboxing, joins them and adds narration into H.264/AAC MP4. No automatic zoom, dissolve, logo, subtitles or music is claimed. Keep SRT for optional CC. These are supported features, not claims about optimal retention. Requested editing beyond these features requires an explicit editor workflow.

Rendering runs FFmpeg with argument arrays and safe generated filenames; project paths are not shell commands. Decode failures abort. A temporary output is moved to video.mp4 only after successful FFmpeg and duration checks. Existing final output requires `--force`. An interrupted run preserves the prior final video. Intermediate segments are cleaned in a project-local temporary folder.

Report generated files, automated checks, actual listening/visual/playback checks and unresolved steps separately in production_report.md. Play the opening, a middle section and ending when possible; check framing, cut timing and the mix. Automated duration validation is not complete playback review. No publishing is performed by helpers.
