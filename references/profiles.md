# Profiles: a new direction without modifying the engine

Built-ins: `profiles/paleon.json` and `profiles/general-explainer.json`. The latter is a neutral starting direction, not a validated niche recommendation. `profiles/template.json` is for authoring and cannot initialize a project until completed and marked `ready: true`.

For a new direction, establish the audience and their recurring question, subject boundaries, content language, distinctive viewer promise, narrative tone, visual treatment, voice and practical episode length. Ask only for material unknowns. Do not inherit Paleon's language or visuals silently. Prefer a separate profile over conditionals added to engine code.

Profiles use JSON (no YAML dependency). Required keys:

| Key | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `id` | Stable lowercase slug |
| `ready` | `true` for production; `false` for an incomplete template |
| `name`, `audience`, `viewer_promise` | Nonempty text |
| `topic_scope` | Nonempty list of subject boundaries |
| `language` | Content language; local Kokoro path currently supports English only |
| `editorial` | `tone` text, `target_minutes` positive ordered pair; optional domain-specific evidence rules |
| `voice` | `provider`: `kokoro` or `external`; voice ID, positive speed, language |
| `visual` | `style_anchor`, `style_lock`, `character` (may be empty), and `aspect_ratio`: `16:9` |
| `packaging` | Positive `thumbnail_concepts` integer, list of appropriate `angles` |
| `render` | Even positive width/height, positive fps; renderer currently uses static framing and hard cuts |

Optional `assets.logo` is a relative file path inside the profile's directory. Init copies that file into the project; absolute/outside paths are rejected. Deliver a profile's referenced assets along with it. Logos and music are not automatically composited by this renderer; add them in an editor or extend rendering explicitly. No pretend support via unused settings.

Validate with `engine.py profile-check --profile <file-or-builtin-id>`. Initialize a short pilot, inspect real output and refine before producing a series. User selections take precedence over suggested defaults. Record changes in the project snapshot rather than silently changing an existing episode.
