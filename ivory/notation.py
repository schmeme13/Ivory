"""Conservative first-pass notation; never modify the acoustic performance."""
from collections import defaultdict
from pathlib import Path
from music21 import stream, note, chord, meter, tempo, clef, metadata, layout, key

def make_score(events: dict, output: Path, bpm: float | None = None, signature: str = '4/4'):
    bpm = bpm or events['estimated_bpm'] or 120.0
    bpm = max(20.0, min(300.0, bpm))
    score = stream.Score()
    score.metadata = metadata.Metadata(title='Ivory transcription', composer='Estimated notation — review before use')
    analysis = stream.Stream()
    for event in events['notes']:
        n = note.Note(event['midi_note'])
        n.quarterLength = max(0.125, (event['offset_time'] - event['onset_time']) * bpm / 60)
        analysis.append(n)
    estimated_key = analysis.analyze('key') if events['notes'] else key.Key('C')
    parts = []
    for upper in (True, False):
        part = stream.PartStaff(id='right' if upper else 'left')
        part.partName = 'Upper staff' if upper else 'Lower staff'
        part.insert(0, clef.TrebleClef() if upper else clef.BassClef())
        part.insert(0, meter.TimeSignature(signature))
        part.insert(0, key.KeySignature(estimated_key.sharps))
        part.insert(0, tempo.MetronomeMark(number=bpm))
        groups = defaultdict(list)
        for event in events['notes']:
            if (event['midi_note'] >= 60) != upper:
                continue
            start = round(event['onset_time'] * bpm / 60 * 4) / 4
            end = max(start + 0.25, round(event['offset_time'] * bpm / 60 * 4) / 4)
            groups[(start, end)].append(event['midi_note'])
        voices, ends = [], []
        for (start, end), pitches in sorted(groups.items()):
            slot = next((i for i, value in enumerate(ends) if value <= start), len(voices))
            if slot == len(voices):
                voices.append(stream.Voice(id=str(slot + 1)))
                ends.append(0)
            element = note.Note(pitches[0]) if len(pitches) == 1 else chord.Chord(sorted(set(pitches)))
            element.quarterLength = end - start
            voices[slot].insert(start, element)
            ends[slot] = end
        if not voices:
            part.insert(0, note.Rest(quarterLength=4))
        for voice in voices:
            voice.makeRests(fillGaps=True, inPlace=True)
            part.insert(0, voice)
        part.makeNotation(inPlace=True)
        score.insert(0, part)
        parts.append(part)
    score.insert(0, layout.StaffGroup(parts, symbol='brace', barTogether=True))
    score.write('musicxml', fp=str(output / 'score.musicxml'))
    return {'bpm': round(bpm, 1), 'key': str(estimated_key), 'meter': signature,
            'warnings': ['Tempo is a single estimate; rubato and tempo changes are not yet modeled.',
                         'Meter is your selected value, not automatic detection. Timing snaps to sixteenth notes.',
                         'Staff assignment uses middle C; crossing hands and complex voices need review.',
                         'Key and note endings are estimates. Pedal events are preserved in MIDI and event JSON, not engraved.']}
