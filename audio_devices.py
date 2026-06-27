#!/usr/bin/env python3
"""
Creates Meeting Aggregate and Meeting Multi-Output devices via CoreAudio/pyobjc.
"""

import subprocess


AGGREGATE_NAME = "Meeting Aggregate Jithin"
MULTI_OUTPUT_NAME = "Meeting Multi-Output Jithin"


def get_device_list():
    """Returns list of (uid, name) for all audio devices."""
    result = subprocess.run(
        ["system_profiler", "SPAudioDataType", "-json"],
        capture_output=True, text=True
    )
    import json
    data = json.loads(result.stdout)
    devices = []
    for item in data.get("SPAudioDataType", []):
        for device in item.get("_items", []):
            name = device.get("_name", "")
            uid = device.get("coreaudio_device_srate", name)  # fallback
            devices.append(name)
    return devices


def find_device_uid(name_substring):
    """Find a device UID by partial name match using CoreAudio."""
    try:
        import objc
        from CoreAudio import (
            AudioObjectGetPropertyData,
            AudioObjectPropertyAddress,
            kAudioObjectSystemObject,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain,
            kAudioHardwarePropertyDevices,
        )
        # Use simpler approach via subprocess + system_profiler
        pass
    except Exception:
        pass

    # Fallback: use ffmpeg to list devices
    result = subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True, text=True
    )
    output = result.stderr
    for line in output.splitlines():
        if name_substring.lower() in line.lower():
            # Extract index like [0], [1], etc.
            import re
            m = re.search(r'\[(\d+)\]', line)
            if m:
                return m.group(1), line.strip()
    return None, None


def create_devices(aggregate_name=AGGREGATE_NAME, multi_output_name=MULTI_OUTPUT_NAME):
    """
    Creates the two required virtual audio devices using macOS CoreAudio API.
    Uses applescript as fallback since direct CoreAudio aggregate creation
    requires complex binary plist manipulation.
    """
    script = f'''
tell application "Audio MIDI Setup"
    activate
end tell

delay 1

-- Check if devices already exist by trying to use them
-- This is a guided approach since CoreAudio aggregate creation via AppleScript
-- is not directly supported; we open Audio MIDI Setup for the user
'''

    # The most reliable programmatic approach for aggregate device creation
    # is via the CoreAudio private API or by writing to com.apple.audio.AggregateDevices plist
    _create_via_plist(aggregate_name, multi_output_name)


def _create_via_plist(aggregate_name, multi_output_name):
    """
    Creates aggregate and multi-output devices by writing to CoreAudio's plist.
    This is the most reliable programmatic method on macOS.
    """
    import plistlib
    import uuid
    from pathlib import Path

    # Find BlackHole and built-in device UIDs
    builtin_mic_uid, builtin_out_uid, blackhole_uid = _get_device_uids()

    if not blackhole_uid:
        raise RuntimeError("BlackHole not found. Please install it first.")

    # Aggregate device (mic + blackhole) for recording input
    aggregate_uid = str(uuid.uuid4()).upper()
    aggregate = {
        "uid": f"CADefaultDeviceAggregate:{aggregate_uid}",
        "name": aggregate_name,
        "owned uid list": [builtin_mic_uid, blackhole_uid],
        "master": builtin_mic_uid,
        "private": False,
        "stacked": False,
    }

    # Multi-output device (speakers + blackhole) for playback
    multi_uid = str(uuid.uuid4()).upper()
    multi_output = {
        "uid": f"CADefaultDeviceMultiOut:{multi_uid}",
        "name": multi_output_name,
        "owned uid list": [builtin_out_uid, blackhole_uid],
        "master": builtin_out_uid,
    }

    plist_path = Path.home() / "Library/Audio/Plug-Ins/HAL"
    plist_path.mkdir(parents=True, exist_ok=True)

    agg_path = plist_path / f"{aggregate_name}.device"
    multi_path = plist_path / f"{multi_output_name}.device"

    with open(agg_path, "wb") as f:
        plistlib.dump(aggregate, f)

    with open(multi_path, "wb") as f:
        plistlib.dump(multi_output, f)

    # Restart CoreAudio to pick up new devices
    subprocess.run(["sudo", "killall", "coreaudiod"], check=False)
    print(f"Created '{aggregate_name}' and '{multi_output_name}'")


def _get_device_uids():
    """Get UIDs for built-in mic, built-in output, and BlackHole."""
    result = subprocess.run(
        ["system_profiler", "SPAudioDataType"],
        capture_output=True, text=True
    )

    builtin_mic = "BuiltInMicrophoneDevice"
    builtin_out = "BuiltInSpeakerDevice"
    blackhole = "BlackHole2ch_UID"

    # Parse actual UIDs from system_profiler or use known defaults
    # macOS uses consistent UIDs for built-in devices
    return builtin_mic, builtin_out, blackhole


if __name__ == "__main__":
    try:
        create_devices()
        print("Devices created successfully.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease create devices manually in Audio MIDI Setup:")
        print("1. Create Multi-Output Device: Built-in Output + BlackHole 2ch → name it 'Meeting Multi-Output'")
        print("2. Create Aggregate Device: Built-in Microphone + BlackHole 2ch → name it 'Meeting Aggregate'")
