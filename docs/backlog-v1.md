# Callscribe — Product Backlog v1

Backlog v1 составлен **строго по** `README.md` (Roadmap → **v1 — Windows, system tray**).

## Prioritization rubric

- **must**: без этого не получается минимально работающее v1 (end-to-end “записал → получил `.md`”).
- **should**: существенно улучшает UX/надёжность/качество, но MVP возможен и без этого.
- **nice**: полезно, но можно отложить после стабилизации.
- **low**: точно не нужно для v1/MVP или можно сильно позже.

## MVP implementation order (end-to-end)

Цель MVP: **ручной старт** → запись **raw audio** (system+mic) → локальная транскрипция → **`.md` в папку**.

1. **Tray skeleton + manual control**: tray, state, start/stop.
2. **Audio capture + raw persistence**: WASAPI loopback + mic, сохранение raw, корректное завершение.
3. **Local STT**: `faster-whisper`, сегменты + timestamps.
4. **Markdown export**: output folder, файл `.md`, предсказуемое имя.
5. **Basic reliability**: error states, базовые логи.
6. **Auto-detect**: старт/стоп по процессам (опционально конфиг).
7. **Selective remote**: confidence, эскалация, merge, устойчивость к API ошибкам.

## Assumptions (from README)

- v1 поддерживает **только Windows**.
- Приложение: **system tray app + background service**.
- Старт записи: **авто-детект** приложений звонков по имени процесса (Meet/Telemost/Zoom/Teams/…); допускается ручной триггер из трея.
- Аудио: запись **system audio + mic** через **WASAPI loopback**.
- STT: локально **`faster-whisper`** (таймкоды + logprobs), затем **выборочная эскалация** “плохих” сегментов в **OpenAI Whisper API**.
- Экспорт: итоговый транскрипт сохраняется **в `.md` в настроенную папку**.
- Первичный стек v1: Python (`psutil`, `soundcard`, `faster-whisper`, `pystray`, `openai`).

## Epics

### E1 — Epic: Windows tray app + background service

#### Stories

- **E1.S1 [must]** As a user, I want Callscribe to run in the system tray, so that it is always available without an open window.
- **E1.S2 [must]** As a user, I want to see the current state (idle / recording / transcribing / error), so that I understand what the app is doing.
- **E1.S3 [must]** As a user, I want to manually start and stop a recording from the tray, so that I can control capture when auto-detection is insufficient.
- **E1.S4 [should]** As a user, I want a clear notification when recording starts/stops, so that I’m confident the session was captured.

### E2 — Epic: Auto-detect call apps by process name

#### Stories

- **E2.S1 [should]** As a user, I want Callscribe to detect when a call app starts (by process name), so that recording can start automatically.
- **E2.S2 [should]** As a user, I want Callscribe to detect when the call ends (process disappears), so that recording stops automatically.
- **E2.S3 [nice]** As a user, I want to configure which processes count as “call apps”, so that auto-detection matches my tools (Zoom/Teams/Chrome/etc.).

### E3 — Epic: Audio capture (WASAPI loopback + mic) and raw audio preservation

#### Stories

- **E3.S1 [must]** As a user, I want Callscribe to record system audio via WASAPI loopback, so that remote participants are captured.
- **E3.S2 [must]** As a user, I want Callscribe to record my microphone audio, so that my speech is included in the source audio.
- **E3.S3 [must]** As a user, I want raw audio to be saved for every session, so that I can re-transcribe or audit the result later.
- **E3.S4 [must]** As a user, I want recording to stop cleanly and finalize files, so that sessions aren’t lost on app stop.

### E4 — Epic: Local transcription with `faster-whisper`

#### Stories

- **E4.S1 [must]** As a user, I want Callscribe to transcribe locally with `faster-whisper`, so that I get fast results without always calling remote APIs.
- **E4.S2 [must]** As a user, I want the local transcript to include timestamps per segment, so that the text can be aligned to audio.
- **E4.S3 [should]** As a user, I want per-segment confidence signals (e.g., logprobs) to be computed, so that quality can be assessed.

### E5 — Epic: Quality assessment and selective routing

#### Stories

- **E5.S1 [should]** As a user, I want Callscribe to detect low-confidence segments, so that only uncertain parts are escalated to a remote provider.
- **E5.S2 [nice]** As a user, I want routing thresholds to be configurable, so that I can balance cost vs quality.
- **E5.S3 [should]** As a user, I want Callscribe to avoid remote calls when confidence is high, so that transcription costs stay low.

### E6 — Epic: Remote fallback transcription (OpenAI Whisper API)

#### Stories

- **E6.S1 [should]** As a user, I want low-confidence segments to be sent to OpenAI Whisper API, so that the final transcript quality improves.
- **E6.S2 [should]** As a user, I want the app to handle remote API failures gracefully (retry / skip / mark), so that one failure doesn’t break the whole session.
- **E6.S3 [nice]** As a user, I want to see (at least in logs/state) when remote fallback is being used, so that cost-driving behavior is visible.

### E7 — Epic: Merge, formatting, and Markdown export

#### Stories

- **E7.S1 [must]** As a user, I want the final transcript to merge local timestamps with improved remote text, so that I get both alignment and quality.
- **E7.S2 [must]** As a user, I want the transcript to be saved as a Markdown (`.md`) file, so that I can read and search it easily.
- **E7.S3 [must]** As a user, I want the output folder to be configurable, so that transcripts land where my notes/workflow are.
- **E7.S4 [should]** As a user, I want the Markdown file name to be predictable (e.g., includes date/time), so that files are easy to manage.

### E8 — Epic: Configuration (minimal v1)

#### Stories

- **E8.S1 [must]** As a user, I want to configure the output folder, so that transcripts are written to my chosen location.
- **E8.S2 [nice]** As a user, I want to configure the process list for call detection, so that auto-recording triggers correctly.
- **E8.S3 [nice]** As a user, I want to configure routing thresholds, so that low-confidence escalation matches my expectations.

### E9 — Epic: Reliability, logging, and safe failure modes

#### Stories

- **E9.S1 [should]** As a user, I want basic logging for recording/transcription steps, so that I can troubleshoot issues.
- **E9.S2 [must]** As a user, I want the app to never discard raw audio, so that I can always recover the primary source.
- **E9.S3 [must]** As a user, I want clear error states surfaced in the tray state, so that I know when intervention is needed.

## Out of scope (Non-goals v1)

- Real-time streaming transcription (batch per session is sufficient)
- Multi-user / cloud sync
- Mobile (v4)
- Paid model — this is open source

