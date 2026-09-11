"""Readable two-staff reduction; acoustic detections are never modified."""
from collections import defaultdict
from pathlib import Path
import json
import statistics
from music21 import stream, note, chord, meter, tempo, clef, metadata, layout, key, pitch
from .playback import synthesize, score_events
from .rhythm import interpret, infer_tempo

def staff_boundary(notes):
    values = sorted(n['midi_note'] for n in notes)
    if len(values) >= 10:
        trim = len(values) // 10
        values = values[trim:-trim]
    if not values or min(values) < 60 <= max(values):
        return 60
    low, high = min(values), max(values)
    for _ in range(12):
        split = (low + high) / 2
        lower, upper = [p for p in values if p < split], [p for p in values if p >= split]
        if not lower or not upper:
            break
        low, high = statistics.mean(lower), statistics.mean(upper)
    return round((low + high) / 2)

def spelled(midi, signature):
    p = pitch.Pitch()
    p.midi = midi
    def cost(candidate):
        accidental=signature.accidentalByStep(candidate.step)
        expected=accidental.alter if accidental else 0
        actual=candidate.accidental.alter if candidate.accidental else 0
        return (actual!=expected, abs(actual)>1, abs(actual), actual>0 if signature.sharps<0 else actual<0)
    return min([p]+p.getAllCommonEnharmonics(),key=cost)

def make_score(events: dict, output: Path, bpm: float | None = None, signature: str = '4/4', split: int | None = None, feel: str = 'expressive'):
    bpm = max(20.0, min(300.0, bpm or infer_tempo(events)))
    interpreted, grid = interpret(events['notes'],bpm,feel)
    boundary = split if split is not None else staff_boundary(events['notes'])
    score = stream.Score()
    score.metadata = metadata.Metadata(title='Ivory transcription')
    analysis = stream.Stream()
    for event in events['notes']:
        n = note.Note(event['midi_note'])
        n.quarterLength = max(.125, (event['offset_time'] - event['onset_time']) * bpm / 60)
        analysis.append(n)
    estimated_key = analysis.analyze('key') if events['notes'] else key.Key('C')
    parts = []
    for upper in (True, False):
        selected = [n for n in events['notes'] if (n['midi_note'] >= boundary) == upper]
        part = stream.PartStaff(id='right' if upper else 'left')
        part.partName = 'Piano' if upper else ''
        use_treble = not selected or statistics.median(n['midi_note'] for n in selected) >= 60
        part.insert(0, clef.TrebleClef() if use_treble else clef.BassClef())
        part.insert(0, meter.TimeSignature(signature))
        part.insert(0, key.KeySignature(estimated_key.sharps))
        if upper:
            part.insert(0, tempo.MetronomeMark(number=bpm))
        groups = defaultdict(list)
        for start, cluster in interpreted:
            for event in cluster:
                if (event['midi_note'] >= boundary) == upper:
                    groups[start].append(event)
        starts = sorted(groups)
        for index, start in enumerate(starts):
            group = groups[start]
            duration = max(grid, statistics.median(n['offset_time'] * bpm / 60 - start for n in group))
            duration = min([v for v in [.125,.25,.375,.5,.75,1,1.5,2,3,4,6,8,12,16] if v>=grid], key=lambda value: abs(value-duration))
            if index + 1 < len(starts):
                gap=starts[index+1]-start
                if feel!='precise' and 0<gap-duration<=grid:
                    duration=gap
                duration = min(duration, gap)
            pitches = [spelled(value, estimated_key) for value in sorted(set(n['midi_note'] for n in group))]
            element = note.Note(pitches[0]) if len(pitches) == 1 else chord.Chord(pitches)
            element.quarterLength = duration
            part.insert(start, element)
        if not selected:
            part.insert(0, note.Rest(quarterLength=4))
        part.makeRests(fillGaps=True, inPlace=True)
        part.makeNotation(inPlace=True)
        score.insert(0, part)
        parts.append(part)
    score.insert(0, layout.StaffGroup(parts, symbol='brace', barTogether=True))
    score.write('musicxml', fp=str(output / 'score.musicxml'))
    rendered = score_events(score,bpm)
    synthesize(rendered,output/'score.wav')
    if not (output/'performance.wav').exists():
        synthesize(events,output/'performance.wav')
    (output/'score-events.json').write_text(json.dumps(rendered),encoding='utf-8')
    details = {'bpm':round(bpm,1), 'key':str(estimated_key), 'meter':signature, 'staff_split':boundary, 'feel':feel,
        'warnings': ['Pitch detection has not been corrected against a reference score.',
        'Readable reduction: simultaneous notes share a duration; each staff advances at its next attack. Independent sustained voices may be shortened.',
        f'Interpretation: {feel}. Nearby chord attacks are grouped; rhythmic resolution is {grid} quarter notes. Tempo is constant and meter is selected manually; rubato and tuplets still need review.',
        'Staff boundary and clefs are estimated; adjust the split for overlapping hand ranges.',
        'Detected-performance playback includes pedal estimates. Written-score playback follows MusicXML without pedal. Both use synthesized tones.']}
    (output/'details.json').write_text(json.dumps(details),encoding='utf-8')
    return details
