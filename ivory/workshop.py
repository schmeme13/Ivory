"""Versioned edits kept separate from the model's transcription."""
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from uuid import uuid4
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from music21 import converter, stream, note, chord, clef, meter, tempo, key, metadata, layout
from .notation import spelled
from .playback import score_events, synthesize

class EditableNote(BaseModel):
    id: str = Field(min_length=1,max_length=80)
    pitch: int = Field(ge=21,le=108)
    start: float = Field(ge=0,le=1200,allow_inf_nan=False)
    duration: float = Field(gt=0,le=64,allow_inf_nan=False)
    staff: Literal[0,1] = 0

class EditDocument(BaseModel):
    revision: str = Field(max_length=80)
    title: str = Field(default='Ivory transcription',min_length=1,max_length=120)
    bpm: float = Field(ge=20,le=300,allow_inf_nan=False)
    sharps: int = Field(ge=-7,le=7)
    meter: Literal['4/4','3/4','2/4','6/8'] = '4/4'
    notes: list[EditableNote] = Field(max_length=4000)

    @model_validator(mode='after')
    def validate_notes(self):
        if len({n.id for n in self.notes})!=len(self.notes):
            raise ValueError('Note identifiers must be unique.')
        if max((n.start+n.duration for n in self.notes),default=0)*60/self.bpm>600:
            raise ValueError('Workshop scores are limited to ten minutes.')
        # Eighths of a quarter support the existing transcription grid without huge tuplets.
        for n in self.notes:
            if any(abs(v*8-round(v*8))>1e-5 for v in (n.start,n.duration)):
                raise ValueError('Note positions and lengths must use multiples of 0.125 beats.')
        return self

def read_document(folder: Path):
    pointer=folder/'workshop/current.json'
    if pointer.exists():
        return json.loads(pointer.read_text(encoding='utf-8'))
    source=folder/'score.musicxml'
    score=converter.parse(source)
    notes=[]
    for staff,part in enumerate(score.parts[:2]):
        for element in part.stripTies().flatten().notes:
            for p in element.pitches:
                notes.append({'id':f'n{len(notes)}','pitch':p.midi,'start':float(element.offset),
                              'duration':float(element.quarterLength),'staff':staff})
    signature=score.recurse().getElementsByClass(key.KeySignature).first()
    time=score.recurse().getElementsByClass(meter.TimeSignature).first()
    speed=score.recurse().getElementsByClass(tempo.MetronomeMark).first()
    title=ET.parse(source).findtext('./work/work-title') or ET.parse(source).findtext('./movement-title') or 'Ivory transcription'
    return {'revision':'base-'+hashlib.sha256(source.read_bytes()).hexdigest(),
            'title':title,'bpm':float(speed.number) if speed else 120,
            'sharps':signature.sharps if signature else 0,'meter':time.ratioString if time else '4/4','notes':notes}

def build_score(document):
    score=stream.Score()
    score.metadata=metadata.Metadata(title=document.title)
    signature=key.KeySignature(document.sharps)
    parts=[]
    for staff in (0,1):
        part=stream.PartStaff(id=f'staff{staff}')
        selected=[n for n in document.notes if n.staff==staff]
        part.insert(0,clef.TrebleClef() if not selected or sorted(n.pitch for n in selected)[len(selected)//2]>=60 else clef.BassClef())
        part.insert(0,key.KeySignature(document.sharps))
        part.insert(0,meter.TimeSignature(document.meter))
        if staff==0:part.insert(0,tempo.MetronomeMark(number=document.bpm))
        groups=defaultdict(list)
        for n in selected:groups[(n.start,n.duration)].append(n.pitch)
        voices=[]; ends=[]
        for (start,duration),pitches in sorted(groups.items()):
            index=next((i for i,end in enumerate(ends) if end<=start),len(ends))
            if index==len(ends):voices.append(stream.Voice(id=str(index+1)));ends.append(0)
            pitches=[spelled(p,signature) for p in pitches]
            element=note.Note(pitches[0]) if len(pitches)==1 else chord.Chord(pitches)
            element.quarterLength=duration
            voices[index].insert(start,element);ends[index]=start+duration
        if not voices:part.insert(0,note.Rest(quarterLength=4))
        for voice in voices:
            voice.makeRests(fillGaps=True,inPlace=True);part.insert(0,voice)
        part.makeNotation(inPlace=True);parts.append(part);score.insert(0,part)
    score.insert(0,layout.StaffGroup(parts,symbol='brace',barTogether=True))
    return score

def save_document(folder: Path,document: EditDocument):
    if read_document(folder)['revision']!=document.revision:
        raise ValueError('This score changed in another tab. Reload before saving.')
    revision=uuid4().hex
    destination=folder/'workshop'/revision
    destination.mkdir(parents=True)
    score=build_score(document)
    score.write('musicxml',fp=str(destination/'score.musicxml'))
    rendered=score_events(score,document.bpm)
    synthesize(rendered,destination/'score.wav')
    (destination/'score-events.json').write_text(json.dumps(rendered),encoding='utf-8')
    data=document.model_dump();data['revision']=revision
    (destination/'document.json').write_text(json.dumps(data),encoding='utf-8')
    pointer=folder/'workshop/current.json'
    temporary=pointer.with_suffix('.tmp')
    temporary.write_text(json.dumps(data),encoding='utf-8');temporary.replace(pointer)
    return data
