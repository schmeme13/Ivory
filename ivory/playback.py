"""Auditable tone synthesis: input consists only of note/pedal events, never audio."""
from pathlib import Path
import numpy as np
import soundfile as sf

def sounding_notes(events):
    notes = sorted(events['notes'], key=lambda n: n['onset_time'])
    next_onset = {}
    result = []
    for n in reversed(notes):
        end = n['offset_time']
        for pedal in events.get('pedals', []):
            if pedal['onset_time'] <= end < pedal['offset_time']:
                end = pedal['offset_time']
        end = min(end, next_onset.get(n['midi_note'], end))
        result.append({**n, 'offset_time': max(n['onset_time'] + .03, end)})
        next_onset[n['midi_note']] = n['onset_time']
    return list(reversed(result))

def synthesize(events, destination: Path, sr=22050):
    notes = sounding_notes(events)
    duration = max((n['offset_time'] for n in notes), default=0) + .4
    audio = np.zeros(int(duration * sr) + 1, dtype=np.float32)
    for n in notes:
        start = int(n['onset_time'] * sr)
        held = n['offset_time'] - n['onset_time']
        t = np.arange(int((held + .3) * sr)) / sr
        frequency = 440 * 2 ** ((n['midi_note'] - 69) / 12)
        wave = np.zeros(len(t))
        for harmonic, amplitude in ((1, 1), (2, .32), (3, .12), (4, .06)):
            if frequency * harmonic < sr / 2:
                wave += amplitude * np.sin(2 * np.pi * frequency * harmonic * t)
        envelope = np.minimum(t / .006, 1) * np.exp(-t / 3.5)
        envelope *= np.exp(-np.maximum(t - held, 0) / .05)
        sound = wave * envelope * n.get('velocity', 80) / 127 * .12
        length = min(len(sound), len(audio) - start)
        audio[start:start+length] += sound[:length].astype(np.float32)
    peak = np.max(np.abs(audio), initial=0)
    if peak > .95:
        audio *= .95 / peak
    sf.write(destination, audio, sr, subtype='PCM_16')

def score_events(score, bpm):
    events = []
    for part in score.parts:
        for element in part.stripTies().flatten().notes:
            for p in element.pitches:
                events.append({'midi_note': p.midi, 'onset_time': float(element.offset)*60/bpm,
                    'offset_time': float(element.offset+element.quarterLength)*60/bpm, 'velocity':80})
    return {'notes':events,'pedals':[]}
