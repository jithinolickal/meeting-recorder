#!/usr/bin/env python3
"""
First-run setup:
- Installs BlackHole via brew
- Creates Multi-Output + Aggregate devices via CoreAudio
- Installs Python dependencies
- Downloads models
"""

import subprocess
import sys
import os


AGGREGATE_NAME = "Meeting Aggregate Jithin"
MULTI_OUTPUT_NAME = "Meeting Multi-Output Jithin"


def run(cmd, check=True):
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)


def install_blackhole():
    result = run("brew list blackhole-2ch", check=False)
    if result.returncode == 0:
        print("BlackHole already installed ✓")
        return True

    print("Installing BlackHole 2ch...")
    result = run("brew install blackhole-2ch", check=False)
    if result.returncode != 0:
        print("Failed to install BlackHole. Make sure Homebrew is installed.")
        return False

    print("BlackHole installed.")
    print()
    print("ACTION REQUIRED: Approve the system extension.")
    print("→ Open System Settings → Privacy & Security → scroll down → click Allow")
    print()
    input("Press Enter once you've approved it...")
    return True


def install_python_deps():
    print("Installing Python dependencies...")
    run(f"{sys.executable} -m pip install -r requirements.txt -q")
    print("Dependencies installed ✓")


def create_audio_devices():
    """Create Meeting Aggregate and Meeting Multi-Output devices via CoreAudio."""
    try:
        import CoreAudio
        from AudioToolbox import AudioObjectSetPropertyData, AudioObjectGetPropertyData
    except ImportError:
        print("pyobjc-framework-CoreAudio not available, skipping device creation.")
        print("Please create devices manually in Audio MIDI Setup.")
        return

    try:
        from audio_devices import create_devices
        create_devices(AGGREGATE_NAME, MULTI_OUTPUT_NAME)
        print(f"'{AGGREGATE_NAME}' and '{MULTI_OUTPUT_NAME}' created ✓")
    except Exception as e:
        print(f"Could not create devices automatically: {e}")
        print("Please create them manually in Audio MIDI Setup (see README).")


def download_models():
    print("Downloading Whisper model (first time only, ~1.6GB)...")
    import mlx_whisper
    # Trigger model download by running a tiny transcription
    import tempfile
    import numpy as np
    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
        sf.write(tmp, np.zeros(16000, dtype=np.float32), 16000)

    try:
        mlx_whisper.transcribe(tmp, path_or_hf_repo="mlx-community/whisper-large-v3-turbo")
        print("Whisper model ready ✓")
    except Exception as e:
        print(f"Model download issue: {e}")
    finally:
        os.unlink(tmp)

    print("Verifying librosa + sklearn for diarization...")
    import librosa
    from sklearn.cluster import AgglomerativeClustering
    print("Diarization dependencies ready ✓")


if __name__ == "__main__":
    print("=== Meeting Recorder Setup ===\n")

    if not install_blackhole():
        sys.exit(1)

    install_python_deps()
    create_audio_devices()
    download_models()

    print("\n=== Setup complete. Run: python app.py ===")
