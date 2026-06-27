# Meeting Recorder - CLAUDE.md

## Project Overview
macOS menu bar app for recording meetings and generating transcripts with speaker diarization. Fully local, no API costs.

## Stack
- **UI**: `rumps` (Python menu bar app)
- **Recording**: `sounddevice` capturing from "Meeting Aggregate Jithin" (BlackHole aggregate device)
- **Audio switching**: pyobjc CoreAudio — switches system output to "Meeting Multi-Output Jithin" during recording so user still hears audio
- **Transcription**: `mlx-whisper` with `mlx-community/whisper-large-v3-turbo` model
- **Diarization**: Pure numpy MFCC extraction + sklearn AgglomerativeClustering (no librosa — broken on Python 3.13 pyenv due to missing `_lzma`)

## Key Files
- `app.py` — menu bar app, manages recording state and UI
- `recorder.py` — audio capture, device switching, WAV saving
- `transcriber.py` — diarization + whisper transcription pipeline
- `audio_devices.py` — CoreAudio device creation (currently incomplete, devices created manually)
- `setup.py` — first-run setup (brew, pip, model download)

## Known Issues / Decisions
- **librosa removed**: Python 3.13 pyenv build is missing `_lzma`, which breaks librosa via pooch. Replaced with pure numpy MFCC implementation.
- **speechbrain removed**: Incompatible with torchaudio 2.11.0 (`list_audio_backends` removed). Replaced with numpy MFCC + sklearn.
- **pyobjc audio switching**: `_set_output_device_pyobjc` fails with "Need 6 arguments, got 4" — output device switching not working yet. Recording still works, just doesn't auto-switch output.
- **rumps.alert on background thread**: Crashes with NSWindow main thread error. Errors are printed to console only.
- **audio_devices.py**: Programmatic device creation via plist is unreliable. Devices must be created manually in Audio MIDI Setup.

## Output
`~/Documents/MeetingRecordings/YYYY-MM-DD/meeting_HH-MM.wav` + `.txt`

## Device Names
- Input (recording): `Meeting Aggregate Jithin`
- Output (playback during recording): `Meeting Multi-Output Jithin`
