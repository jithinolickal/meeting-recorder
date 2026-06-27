#!/usr/bin/env python3
"""
Meeting Recorder - macOS menu bar app.
Click the mic icon to start/stop recording.
Transcription runs automatically after stopping.
"""

import rumps
import threading
from pathlib import Path


class MeetingRecorderApp(rumps.App):
    def __init__(self):
        super().__init__("🎙", quit_button=None)
        self.recorder = None
        self.recording = False
        self.transcribing = False

        self.record_item = rumps.MenuItem("Start Recording", callback=self.toggle_recording)
        self.menu = [
            self.record_item,
            rumps.MenuItem("Open Recordings Folder", callback=self.open_recordings),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

    def toggle_recording(self, sender):
        print(f"toggle_recording called, recording={self.recording}, transcribing={self.transcribing}", flush=True)
        if self.transcribing:
            rumps.alert("Please wait", "Transcription is still in progress.")
            return

        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        import traceback
        from recorder import Recorder

        print("Starting recorder...", flush=True)
        self.recorder = Recorder()
        try:
            self.recorder.start()
        except Exception as e:
            print(f"ERROR starting recording: {e}", flush=True)
            traceback.print_exc()
            rumps.alert("Error", f"Could not start recording:\n{e}\n\nMake sure 'Meeting Aggregate Jithin' device exists.")
            return

        self.recording = True
        self.title = "🔴"
        self.record_item.title = "Stop Recording"

    def _stop_recording(self):
        self.recording = False
        self.title = "⏳"
        self.record_item.title = "Transcribing..."

        audio_path = self.recorder.stop()

        self.transcribing = True
        thread = threading.Thread(target=self._transcribe, args=(audio_path,), daemon=True)
        thread.start()

    def _transcribe(self, audio_path):
        from transcriber import transcribe

        try:
            transcript, output_path = transcribe(audio_path, on_progress=lambda msg: print(msg))
            self.title = "🎙"
            self.record_item.title = "Start Recording"
            rumps.notification(
                title="Meeting Recorder",
                subtitle="Transcription complete",
                message=f"Saved to {output_path.name}"
            )
        except Exception as e:
            print(f"Transcription error: {e}")
            self.title = "🎙"
            self.record_item.title = "Start Recording"
        finally:
            self.transcribing = False

    def open_recordings(self, _):
        import subprocess
        folder = Path.home() / "Documents" / "MeetingRecordings"
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(folder)])

    def quit_app(self, _):
        if self.recording:
            self._stop_recording()
        rumps.quit_application()


if __name__ == "__main__":
    try:
        import mlx_whisper
        import sounddevice
        import librosa
    except ImportError:
        import subprocess, sys
        print("Dependencies missing. Running setup...")
        subprocess.run([sys.executable, "setup.py"])

    MeetingRecorderApp().run()
