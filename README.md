# Meeting Recorder

macOS menu bar app that records meetings and generates transcripts with speaker identification. Runs fully locally — no cloud, no API costs.

## How it works

- Captures both your microphone and remote participants (via BlackHole virtual audio driver)
- Transcribes using Whisper large-v3-turbo (Apple Silicon optimized via MLX)
- Identifies speakers using MFCC + agglomerative clustering (no external model needed)
- Saves audio + transcript to `~/Documents/MeetingRecordings/YYYY-MM-DD/`

## Requirements

- macOS (Apple Silicon)
- Python 3.10+
- Homebrew

## Setup (one-time)

**1. Install BlackHole**
```bash
brew install blackhole-2ch
```
Then approve the system extension: System Settings → Privacy & Security → scroll down → click **Allow**.

**2. Create audio devices in Audio MIDI Setup**

Open Audio MIDI Setup (Finder → Go → Utilities → Audio MIDI Setup):

- Click `+` → **Create Multi-Output Device**
  - Check: MacBook Pro Speakers + BlackHole 2ch
  - Rename to: `Meeting Multi-Output Jithin`

- Click `+` → **Create Aggregate Device**
  - Check: MacBook Pro Microphone + BlackHole 2ch
  - Rename to: `Meeting Aggregate Jithin`

**3. Run setup**
```bash
cd meeting-recorder
python setup.py
```

This installs Python dependencies and downloads the Whisper model (~1.6GB, one-time).

**4. Fix notifications (one-time)**
```bash
/usr/libexec/PlistBuddy -c 'Add :CFBundleIdentifier string "rumps"' "$(pyenv which python | xargs dirname)/Info.plist"
```

## Usage

```bash
python app.py
```

A 🎙 icon appears in your menu bar. Click it to start/stop recording anytime.

| State | Icon |
|-------|------|
| Idle | 🎙 |
| Recording | 🔴 |
| Transcribing | ⏳ |

## Output

Recordings saved to `~/Documents/MeetingRecordings/YYYY-MM-DD/meeting_HH-MM.wav`

Transcript saved alongside as `.txt`:
```
[SPEAKER_00] 00:01  Can everyone hear me?
[SPEAKER_01] 00:01  Yes, go ahead.
[SPEAKER_00] 00:02  Great, let me walk through the plan.
```

Speaker labels are `SPEAKER_00`, `SPEAKER_01`, etc. — label them manually after.
