#!/usr/bin/env python3
"""
Handles audio recording from the Meeting Aggregate device.
Switches system output to Meeting Multi-Output before recording,
restores it after.
"""

import subprocess
import threading
import wave
import numpy as np
from datetime import datetime
from pathlib import Path

AGGREGATE_DEVICE = "Meeting Aggregate Jithin"
MULTI_OUTPUT_DEVICE = "Meeting Multi-Output Jithin"
RECORDINGS_DIR = Path.home() / "Documents" / "MeetingRecordings"
SAMPLE_RATE = 16000
CHANNELS = 1


def get_current_output_device():
    return _get_output_device_pyobjc()


def set_output_device(name):
    _set_output_device_pyobjc(name)


def _get_output_device_pyobjc():
    try:
        import objc
        from CoreAudio import (
            AudioObjectGetPropertyData,
            AudioObjectPropertyAddress,
            kAudioObjectSystemObject,
            kAudioHardwarePropertyDefaultOutputDevice,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain,
            kAudioDevicePropertyDeviceName,
        )
        addr = AudioObjectPropertyAddress(
            kAudioHardwarePropertyDefaultOutputDevice,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain
        )
        device_id = AudioObjectGetPropertyData(kAudioObjectSystemObject, addr, 0, None)
        name_addr = AudioObjectPropertyAddress(
            kAudioDevicePropertyDeviceName,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain
        )
        name = AudioObjectGetPropertyData(device_id, name_addr, 0, None)
        return name
    except Exception:
        return None


def _set_output_device_pyobjc(name):
    try:
        import objc
        from CoreAudio import (
            AudioObjectSetPropertyData,
            AudioObjectGetPropertyData,
            AudioObjectPropertyAddress,
            kAudioObjectSystemObject,
            kAudioHardwarePropertyDefaultOutputDevice,
            kAudioHardwarePropertyDevices,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain,
            kAudioDevicePropertyDeviceName,
        )
        # Get all devices, find by name, set as default output
        addr = AudioObjectPropertyAddress(
            kAudioHardwarePropertyDevices,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain
        )
        devices = AudioObjectGetPropertyData(kAudioObjectSystemObject, addr, 0, None)
        for device_id in devices:
            name_addr = AudioObjectPropertyAddress(
                kAudioDevicePropertyDeviceName,
                kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain
            )
            device_name = AudioObjectGetPropertyData(device_id, name_addr, 0, None)
            if device_name == name:
                out_addr = AudioObjectPropertyAddress(
                    kAudioHardwarePropertyDefaultOutputDevice,
                    kAudioObjectPropertyScopeGlobal,
                    kAudioObjectPropertyElementMain
                )
                AudioObjectSetPropertyData(kAudioObjectSystemObject, out_addr, 0, None, device_id)
                return
    except Exception as e:
        print(f"Could not set output device: {e}")


def find_input_device_index(name):
    """Find sounddevice index for the aggregate input device."""
    import sounddevice as sd
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if name.lower() in d['name'].lower() and d['max_input_channels'] > 0:
            return i
    return None


class Recorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.thread = None
        self.output_path = None
        self._prev_output_device = None

    def start(self):
        import sounddevice as sd

        now = datetime.now()
        date_folder = RECORDINGS_DIR / now.strftime("%Y-%m-%d")
        date_folder.mkdir(parents=True, exist_ok=True)
        self.output_path = date_folder / f"meeting_{now.strftime('%H-%M')}.wav"
        self.frames = []
        self.recording = True

        # Switch system output to Meeting Multi-Output so we still hear audio
        self._prev_output_device = get_current_output_device()
        set_output_device(MULTI_OUTPUT_DEVICE)

        device_index = find_input_device_index(AGGREGATE_DEVICE)

        def callback(indata, frames, time, status):
            if self.recording:
                self.frames.append(indata.copy())

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            device=device_index,
            callback=callback
        )
        self.stream.start()
        print(f"Recording started → {self.output_path}")

    def stop(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()

        # Restore previous audio output
        if self._prev_output_device:
            set_output_device(self._prev_output_device)

        # Save WAV file
        audio = np.concatenate(self.frames, axis=0)
        with wave.open(str(self.output_path), 'w') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        print(f"Recording saved → {self.output_path}")
        return self.output_path
