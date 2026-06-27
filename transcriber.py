#!/usr/bin/env python3
"""
Transcribes audio with speaker diarization.
Uses mlx-whisper (Apple Silicon optimized) + librosa/sklearn for speaker ID.
No heavy ML models needed for diarization — works on Python 3.13.
"""

import numpy as np
from pathlib import Path


WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def load_audio(path):
    import soundfile as sf
    audio, sr = sf.read(str(path), dtype='float32')
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, sr


def extract_mfcc(chunk, sr, n_mfcc=20):
    """Pure numpy MFCC extraction — no librosa needed."""
    # Pre-emphasis
    chunk = np.append(chunk[0], chunk[1:] - 0.97 * chunk[:-1])

    # Frame into overlapping windows
    frame_len = int(0.025 * sr)
    frame_hop = int(0.010 * sr)
    frames = np.array([
        chunk[i:i + frame_len]
        for i in range(0, len(chunk) - frame_len, frame_hop)
        if i + frame_len <= len(chunk)
    ])
    if len(frames) == 0:
        return np.zeros(n_mfcc)

    # Power spectrum
    frames *= np.hamming(frame_len)
    mag = np.abs(np.fft.rfft(frames, n=512))
    power = (1 / 512) * (mag ** 2)

    # Mel filterbank (simplified)
    n_filters = 26
    low, high = 0, sr / 2
    mel_low = 2595 * np.log10(1 + low / 700)
    mel_high = 2595 * np.log10(1 + high / 700)
    mel_points = np.linspace(mel_low, mel_high, n_filters + 2)
    hz_points = 700 * (10 ** (mel_points / 2595) - 1)
    bin_points = np.floor((512 + 1) * hz_points / sr).astype(int)

    fbank = np.zeros((n_filters, 257))
    for m in range(1, n_filters + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]
        for k in range(f_m_minus, f_m):
            if f_m != f_m_minus:
                fbank[m - 1, k] = (k - f_m_minus) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if f_m_plus != f_m:
                fbank[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)

    filter_banks = np.dot(power, fbank.T)
    filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
    filter_banks = 20 * np.log10(filter_banks)

    # DCT to get MFCCs
    num_frames = filter_banks.shape[0]
    mfcc = np.zeros((num_frames, n_mfcc))
    for n in range(n_mfcc):
        mfcc[:, n] = np.sum(
            filter_banks * np.cos(np.pi * n / n_filters * (np.arange(1, n_filters + 1) - 0.5)),
            axis=1
        )

    return mfcc.mean(axis=0)


def diarize(audio, sr, num_speakers=None):
    """
    Speaker diarization using MFCC features + agglomerative clustering.
    Pure numpy — no librosa dependency.
    Returns list of (start_sec, end_sec, speaker_label).
    """
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.preprocessing import StandardScaler

    print("Running speaker diarization...")

    window = int(1.5 * sr)
    hop = int(0.75 * sr)
    segments = []
    features = []

    for start in range(0, len(audio) - window, hop):
        chunk = audio[start:start + window]
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms < 0.001:
            continue
        feat = extract_mfcc(chunk, sr)
        features.append(feat)
        segments.append((start / sr, (start + window) / sr))

    if len(features) < 2:
        return [(0, len(audio) / sr, "SPEAKER_00")]

    X = StandardScaler().fit_transform(np.array(features))
    n_speakers = num_speakers or min(max(2, len(segments) // 8), 6)
    clustering = AgglomerativeClustering(n_clusters=n_speakers, metric='euclidean', linkage='ward')
    labels = clustering.fit_predict(X)

    diarization = []
    for i, (start, end) in enumerate(segments):
        speaker = f"SPEAKER_{labels[i]:02d}"
        if diarization and diarization[-1][2] == speaker and start <= diarization[-1][1] + 0.1:
            diarization[-1] = (diarization[-1][0], end, speaker)
        else:
            diarization.append([start, end, speaker])

    return [(s, e, sp) for s, e, sp in diarization]


def get_speaker_at(diarization, time):
    for start, end, speaker in diarization:
        if start <= time <= end:
            return speaker
    return "UNKNOWN"


def transcribe(audio_path, on_progress=None):
    """
    Transcribe audio file and return formatted transcript with speaker labels.
    on_progress: optional callback(message) for status updates.
    """
    import mlx_whisper

    path = Path(audio_path)
    audio, sr = load_audio(path)

    if on_progress:
        on_progress("Running speaker diarization...")
    diarization = diarize(audio, sr)

    if on_progress:
        on_progress("Transcribing audio...")
    result = mlx_whisper.transcribe(
        str(path),
        path_or_hf_repo=WHISPER_MODEL,
        word_timestamps=False,
        verbose=False
    )

    if on_progress:
        on_progress("Building transcript...")

    lines = []
    current_speaker = None
    current_text = []
    current_start = None

    for segment in result.get("segments", []):
        mid = (segment["start"] + segment["end"]) / 2
        speaker = get_speaker_at(diarization, mid)
        text = segment["text"].strip()

        if not text:
            continue

        if speaker != current_speaker:
            if current_text and current_speaker:
                lines.append(f"[{current_speaker}] {format_time(current_start)}  {' '.join(current_text)}")
            current_speaker = speaker
            current_text = [text]
            current_start = segment["start"]
        else:
            current_text.append(text)

    if current_text and current_speaker:
        lines.append(f"[{current_speaker}] {format_time(current_start)}  {' '.join(current_text)}")

    transcript = "\n".join(lines)

    output_path = path.with_suffix(".txt")
    output_path.write_text(transcript)

    if on_progress:
        on_progress(f"Saved → {output_path.name}")

    return transcript, output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <audio.wav>")
        sys.exit(1)

    transcript, out = transcribe(sys.argv[1], on_progress=print)
    print("\n--- TRANSCRIPT ---")
    print(transcript)
    print(f"\nSaved to: {out}")
