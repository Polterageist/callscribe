# Callscribe

> Automatic call recording with perfect-quality transcription. Cross-platform. Plugin-based.

---

## The Idea

When a call starts — on mobile or desktop — Callscribe detects it, starts recording automatically (or on manual trigger), and produces a high-quality transcript. The primary source (audio, optionally screen) is always preserved. Transcription quality is maximized through a combination of fast local models, powerful remote backends, and feedback loops.

Output goes wherever you tell it: a file, Obsidian vault, Notion, a webhook, or a custom plugin.

---

## Architecture

### Layers

```
┌─────────────────────────────────┐
│           GUI Layer             │  Flutter (or React Native)
│  (platform UI, manual trigger,  │  — iOS, Android, Windows, macOS, Linux
│   transcript viewer, settings)  │
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│         Platform Layer          │  OS-specific adapters
│  (call detection, audio/screen  │  — phone API hooks (mobile)
│   capture, notifications,       │  — audio session monitor (desktop)
│   permissions)                  │  — screen capture (optional)
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│         Engine (Core)           │  Platform-agnostic business logic
│  (routing, decisions, quality   │  — pure Dart / Rust / Go (TBD)
│   assessment, feedback loops,   │  — no OS dependencies
│   storage, plugin registry)     │
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│      STT Provider Plugins       │  Plugin interface, swappable
│  (Whisper local, Whisper remote,│  — each plugin: transcribe(audio) → transcript
│   Deepgram, Google, OpenAI,     │  — metadata: latency, confidence, cost
│   custom backends)              │
└─────────────────────────────────┘
```

---

### Engine — Core Responsibilities

The Engine is the brain. It is completely decoupled from OS and UI.

**1. Recording Orchestration**
- Receives "call started / stopped" events from the Platform Layer
- Controls the recording session lifecycle
- Stores raw audio (primary source, never discarded)

**2. STT Routing**
- Decides which providers to invoke, in what order, with what audio segment
- Default strategy:
  1. Fast local Whisper → timestamps + basic markup + confidence score per segment
  2. Quality assessment: if `confidence < threshold` for a segment → delegate that segment to a powerful remote provider
  3. Merge results: local timestamps + remote quality text → final transcript
- Strategy is configurable and extensible

**3. Quality Assessment**
- Per-segment confidence scoring (from Whisper logprobs or heuristics)
- Detects: background noise, overlapping speakers, low-confidence words
- Routes only the problematic segments upstream (cost-efficient)

**4. Feedback Loops**
- User corrections on the transcript are logged
- Correction patterns update routing thresholds and segment-level confidence calibration
- Over time: fewer segments escalated to remote, lower cost, same quality

**5. Plugin Registry**
- Plugins implement a standard interface:
  ```
  interface STTProvider {
    transcribe(audio: AudioSegment, options: Options): TranscriptResult
    metadata: { latency: Latency, cost: Cost, capabilities: Capability[] }
  }
  ```
- Engine selects providers by capability (timestamps, diarization, language, cost ceiling)

**6. Output Routing**
- Transcript delivered to configured destinations via output plugins:
  - Local file (plain text, JSON, SRT, Markdown)
  - Obsidian vault
  - Notion / Confluence
  - Webhook
  - Custom

---

### Platform Layer — OS Adapters

Each platform implements the same adapter interface:

```
interface PlatformAdapter {
  onCallStarted(callback)
  onCallEnded(callback)
  startAudioCapture(): AudioStream
  stopAudioCapture()
  startScreenCapture(): ScreenStream   // optional
}
```

Platform implementations:
| Platform | Call Detection | Audio Capture |
|----------|---------------|---------------|
| Android | `TelecomManager` / `CallLog` observer | `AudioRecord`, `MediaProjection` |
| iOS | `CallKit` | `AVAudioEngine` |
| macOS | Audio session observer | `AVCaptureSession` / `ScreenCaptureKit` |
| Windows | `WASAPI` / Windows Phone Link hooks | `WASAPI loopback` |
| Linux | PulseAudio / PipeWire monitor source | same |

---

### Transcription Pipeline

```
Audio (raw, preserved)
        │
        ▼
┌───────────────────┐
│  Local Whisper    │  fast, offline, timestamps, logprobs
│  (base/small)     │
└────────┬──────────┘
         │
         ▼
  Per-segment confidence?
         │
    ┌────┴────┐
high│         │low / noisy
    ▼         ▼
  Accept   Remote Provider
  segment  (Whisper large /
           Deepgram / OpenAI)
    │         │
    └────┬────┘
         ▼
   Merge & align
   (timestamps from local,
    text quality from remote)
         │
         ▼
  Post-processing
  (speaker diarization,
   punctuation, formatting)
         │
         ▼
   Final Transcript
   → Output destinations
```

---

### Data Model (Core)

```
Recording
  id: UUID
  started_at: DateTime
  ended_at: DateTime
  participants: [Participant]
  audio_path: Path            // raw audio, always kept
  screen_path: Path?          // optional screen capture
  transcripts: [Transcript]

Transcript
  id: UUID
  created_at: DateTime
  provider_log: [ProviderEntry]
  segments: [Segment]
  confidence_avg: Float

Segment
  start_ms: Int
  end_ms: Int
  speaker: Speaker?
  text: String
  confidence: Float
  provider: String            // which STT produced this segment

ProviderEntry
  provider: String
  segments_sent: Int
  latency_ms: Int
  cost_units: Float
```

---

### GUI

Flutter (primary candidate) or React Native. Single codebase for iOS, Android, macOS, Windows, Linux.

Screens:
- **Dashboard** — recent calls, recording status indicator, manual record button
- **Transcript Viewer** — segments with timestamps, speaker labels, inline edit (corrections fed back to engine)
- **Settings** — provider plugins (enable/disable, API keys, thresholds), output destinations, storage
- **Recording** — live waveform, elapsed time, manual stop

---

## Tech Stack (proposed)

| Component | Candidate | Notes |
|-----------|-----------|-------|
| GUI | Flutter | Best cross-platform audio/permission support |
| Engine | Dart (in Flutter) or Rust FFI | Rust if heavy processing needed |
| Local Whisper | `whisper.cpp` via FFI | Runs on-device, no network |
| Remote STT | Plugin (Deepgram, OpenAI, custom) | Pay-per-use, quality ceiling |
| Storage | SQLite + local filesystem | Simple, offline-first |
| Output plugins | Dart interface + impl per destination | Obsidian, file, webhook |

---

## Non-Goals (v1)

- Real-time streaming transcription (batch per call is sufficient initially)
- Multi-user / cloud sync
- Web app
- Paid subscription model

---

## Status

`idea` — architecture proposal, no code yet.
