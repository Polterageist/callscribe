# Callscribe

> Automatic call recording with perfect-quality transcription. Plugin-based STT routing with local + remote providers and feedback loops.

Open source. Built live on stream.

---

## Getting started (dev)

### Prerequisites

- Python **3.12+**
- [Poetry](https://python-poetry.org/) (dependency + venv management)

### Install

```bash
poetry install
```

### Run (tray app)

```bash
poetry run python -m callscribe
```

### Logs

- **Default**: logs go to a file:
  - Windows: `%APPDATA%/Callscribe/logs/callscribe.log`
  - Other OS: `~/.callscribe/logs/callscribe.log`
- **Console output**: enable stream logging via env flag:

```bash
CALLSCRIBE_LOG_STDOUT=1 poetry run python -m callscribe
```

### Tests

```bash
poetry run pytest
```

Test layout:

- `tests/unit/` — fast isolated logic
- `tests/ui/` — adapter / toolkit wiring with fakes
- `tests/integration/` — subprocess / multi-process seams

### Lint / types

```bash
poetry run ruff check .
poetry run mypy .
```

---

## The Idea

When a call starts, Callscribe detects it, starts recording automatically (or on manual trigger), and produces a high-quality transcript. The primary source — raw audio — is always preserved. Transcription quality is maximized through a combination of fast local models, powerful remote backends, and feedback loops that improve routing over time.

Output goes wherever you tell it: a Markdown file, Obsidian vault, Notion, a webhook, or a custom plugin.

---

## Roadmap

### v1 — Windows, system tray *(first stream)*

Working prototype for Windows:
- System tray app + background service
- Auto-detects call apps by process name (Google Meet, Telemost, Zoom, Teams, ...)
- Records system audio + mic via WASAPI loopback
- Runs `faster-whisper` locally → timestamps + logprobs
- Routes low-confidence segments to remote provider (OpenAI Whisper API)
- Saves transcript as `.md` to a configured folder

Stack: **Python** — `psutil`, `soundcard`, `faster-whisper`, `pystray`, `openai`

### v2 — Engine refactor + output plugins

- Extract Engine as a clean module with no UI/OS dependencies
- Output plugin interface: file, Obsidian, Notion, webhook
- Config file (TOML/YAML) for process list, thresholds, destinations
- Feedback loop: corrections logged → threshold calibration

### v3 — Cross-platform GUI

- Flutter desktop (Windows, macOS, Linux)
- Transcript viewer with inline edit
- Provider plugin management UI

### v4 — Mobile

- Android (`TelecomManager` + `AudioRecord`)
- iOS (`CallKit` + `AVAudioEngine`)

---

## Architecture

### Layers

```
┌─────────────────────────────────┐
│           GUI Layer             │  v1: system tray (pystray)
│  (tray icon, manual trigger,    │  v3+: Flutter desktop
│   status, settings)             │  v4+: mobile (iOS/Android)
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│         Platform Layer          │  OS-specific adapters
│  (process monitor, audio        │  v1: Windows — psutil + WASAPI
│   capture, notifications)       │  v3+: macOS, Linux
│                                 │  v4+: Android, iOS
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│         Engine (Core)           │  Platform-agnostic business logic
│  (routing, quality assessment,  │  No OS or UI dependencies
│   feedback loops, storage,      │  v1: Python module
│   plugin registry)              │  v3+: extracted, potentially Rust
└────────────────┬────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼──────────┐   ┌──────────▼──────┐
│ STT Plugins  │   │  Output Plugins  │
│ local Whisper│   │  file, Obsidian  │
│ OpenAI API   │   │  Notion, webhook │
│ Deepgram ... │   │  custom          │
└──────────────┘   └─────────────────┘
```

---

### Engine — Core Responsibilities

The Engine is the brain. Completely decoupled from OS and UI.

**1. Recording Orchestration**
- Receives `call_started` / `call_stopped` events from the Platform Layer
- Controls session lifecycle, stores raw audio (never discarded)

**2. STT Routing**
- Default pipeline:
  1. `faster-whisper` local → segments with timestamps + logprobs (confidence per token)
  2. Per-segment quality assessment: `avg_logprob`, `no_speech_prob`, word-level confidence
  3. Low-confidence segments → escalated to remote provider
  4. Merge: local timestamps + remote text quality → final transcript
- Strategy is configurable

**3. Quality Assessment**
- Per-segment metrics from `faster-whisper`: `avg_logprob`, `no_speech_prob`, `compression_ratio`
- Detects: background noise, crosstalk, garbled audio
- Only problematic segments hit the remote API — cost-efficient

**4. Feedback Loops**
- User corrections on transcripts are logged
- Correction patterns calibrate per-provider confidence thresholds
- Over time: fewer escalations, lower cost, same or better quality

**5. Plugin Interface — STT Providers**

```python
class STTProvider(Protocol):
    name: str
    capabilities: set[Capability]  # TIMESTAMPS, DIARIZATION, LANGUAGES...

    def transcribe(
        self,
        audio: AudioSegment,
        options: TranscribeOptions,
    ) -> TranscriptResult: ...
```

**6. Plugin Interface — Output Destinations**

```python
class OutputDestination(Protocol):
    def deliver(self, recording: Recording, transcript: Transcript) -> None: ...
```

Built-in destinations: local Markdown file, Obsidian vault (drop into folder), webhook POST, stdout.

---

### Transcription Pipeline

```
Audio (raw, always preserved)
        │
        ▼
┌─────────────────────┐
│   faster-whisper    │  local, offline
│   (small / medium)  │  → segments: text + timestamps + avg_logprob
└──────────┬──────────┘
           │
    per-segment quality check
    (avg_logprob, no_speech_prob)
           │
      ┌────┴────┐
 high │         │ low / uncertain
      ▼         ▼
   Accept    Remote Provider
   segment   (OpenAI Whisper /
              Deepgram / custom)
      │         │
      └────┬────┘
           ▼
     Merge & align
     (local timestamps + remote text)
           │
           ▼
    Post-processing
    (speaker diarization opt.,
     punctuation, Markdown formatting)
           │
           ▼
     Final Transcript
     → Output destinations
```

---

### Platform Layer — v1 Windows

```python
class WindowsPlatformAdapter:
    # Process monitor
    CALL_PROCESSES = [
        "chrome.exe",       # Google Meet
        "teams.exe",        # Microsoft Teams
        "zoom.exe",         # Zoom
        "telemost.exe",     # Yandex Telemost
        "discord.exe",      # Discord calls
        "skype.exe",
    ]

    def watch(self, on_call_started, on_call_stopped) -> None:
        # psutil poll loop — detects process appear/disappear
        ...

    def start_audio_capture(self) -> AudioStream:
        # soundcard — WASAPI loopback (system) + mic mixed
        ...
```

Full platform adapter interface (for future ports):

```python
class PlatformAdapter(Protocol):
    def watch(self, on_call_started, on_call_stopped) -> None: ...
    def start_audio_capture(self) -> AudioStream: ...
    def stop_audio_capture(self) -> None: ...
    def start_screen_capture(self) -> ScreenStream | None: ...  # optional
```

---

### Data Model

```python
@dataclass
class Recording:
    id: str                      # UUID
    started_at: datetime
    ended_at: datetime | None
    audio_path: Path             # raw audio, always kept
    screen_path: Path | None     # optional
    transcripts: list[Transcript]

@dataclass
class Transcript:
    id: str
    created_at: datetime
    segments: list[Segment]
    provider_log: list[ProviderEntry]
    confidence_avg: float

@dataclass
class Segment:
    start_ms: int
    end_ms: int
    text: str
    confidence: float            # avg_logprob normalized
    provider: str                # "faster-whisper" | "openai" | ...
    speaker: str | None          # diarization, optional

@dataclass
class ProviderEntry:
    provider: str
    segments_sent: int
    latency_ms: int
    tokens_used: int | None
```

---

## Tech Stack

| Component | v1 | v3+ |
|-----------|-----|-----|
| Language | Python | Python + Rust (engine) |
| GUI | `pystray` + `Pillow` (tray) | Flutter desktop |
| Process detection | `psutil` | platform adapters |
| Audio capture | `soundcard` (WASAPI loopback) | platform adapters |
| Local STT | `faster-whisper` | same |
| Remote STT | `openai` (Whisper API) | plugin, swappable |
| Storage | local filesystem + JSON | SQLite |
| Config | TOML | same |
| Output | Markdown file | plugin (Obsidian, Notion, webhook) |

---

## Non-Goals (v1)

- Real-time streaming transcription (batch per session is sufficient)
- Multi-user / cloud sync
- Mobile (v4)
- Paid model — this is open source

---

## Status

`in development` — v1 being built live on stream.
