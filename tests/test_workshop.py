import copy
import json
import xml.etree.ElementTree as ET
import pytest
from pydantic import ValidationError
from music21 import converter
from ivory.notation import make_score
from ivory.workshop import read_document,save_document,EditDocument

def original(folder):
    events={'estimated_bpm':120,'notes':[{'midi_note':60,'onset_time':0,'offset_time':1},
        {'midi_note':64,'onset_time':0,'offset_time':1},
        {'midi_note':48,'onset_time':0,'offset_time':3}],'pedals':[]}
    make_score(events,folder,120)
    return read_document(folder)

def test_edit_roundtrip_and_original_preservation(tmp_path):
    doc=original(tmp_path);before=(tmp_path/'score.musicxml').read_bytes()
    doc.update(title='A & B <duet>',bpm=90,sharps=-2)
    doc['notes'][0].update(pitch=62,duration=3,start=1)
    doc['notes'].append({'id':'added','pitch':72,'staff':0,'start':5,'duration':1})
    saved=save_document(tmp_path,EditDocument(**doc))
    assert read_document(tmp_path)==saved
    assert (tmp_path/'score.musicxml').read_bytes()==before
    rendered=converter.parse(tmp_path/'workshop'/saved['revision']/'score.musicxml')
    assert ET.parse(tmp_path/'workshop'/saved['revision']/'score.musicxml').findtext('./work/work-title')=='A & B <duet>'
    pitches={p.midi for p in rendered.flatten().pitches}
    assert 62 in pitches and 72 in pitches and 60 not in pitches
    playback=json.loads((tmp_path/'workshop'/saved['revision']/'score-events.json').read_text())
    assert any(n['midi_note']==62 and abs(n['onset_time']-2/3)<1e-6 for n in playback['notes'])

def test_conflict_and_delete(tmp_path):
    doc=original(tmp_path);stale=copy.deepcopy(doc)
    doc['notes']=doc['notes'][1:]
    save_document(tmp_path,EditDocument(**doc))
    with pytest.raises(ValueError,match='another tab'):save_document(tmp_path,EditDocument(**stale))
    assert len(read_document(tmp_path)['notes'])==2

def test_bad_edits_rejected(tmp_path):
    doc=original(tmp_path)
    for values in ({'pitch':150},{'start':-.5},{'duration':.0001},{'staff':4}):
        invalid=copy.deepcopy(doc);invalid['notes'][0].update(values)
        with pytest.raises(ValidationError):EditDocument(**invalid)
    doc['notes'][0]['id']=doc['notes'][1]['id']
    with pytest.raises(ValidationError):EditDocument(**doc)
