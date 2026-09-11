import json
import numpy as np
import soundfile as sf
from music21 import converter, clef
from ivory.playback import synthesize, sounding_notes, score_events
from ivory.notation import make_score, staff_boundary

def test_synthesis_is_note_audio(tmp_path):
    events = {'notes':[{'midi_note':69,'onset_time':.2,'offset_time':.8,'velocity':90}], 'pedals':[]}
    output=tmp_path/'generated.wav'
    synthesize(events,output)
    y,sr=sf.read(output)
    assert np.max(abs(y[:int(.19*sr)])) == 0
    clip=y[int(.3*sr):int(.6*sr)]
    frequencies=np.fft.rfftfreq(len(clip),1/sr)
    fundamental=frequencies[np.argmax(abs(np.fft.rfft(clip)))]
    assert abs(fundamental-440)<4

def test_pedal_and_repeated_note_release():
    events={'notes':[{'midi_note':60,'onset_time':0,'offset_time':.5},
                     {'midi_note':60,'onset_time':1,'offset_time':1.5}],
            'pedals':[{'onset_time':.2,'offset_time':2}]}
    sounding=sounding_notes(events)
    assert [n['offset_time'] for n in sounding] == [1,2]
    assert events['notes'][0]['offset_time']==.5

def test_upper_range_lower_staff_and_score_playback_match_xml(tmp_path):
    events={'estimated_bpm':60,'notes':[
        {'midi_note':73,'onset_time':0,'offset_time':3.91},
        {'midi_note':77,'onset_time':0,'offset_time':4.07},
        {'midi_note':85,'onset_time':0,'offset_time':3},
        {'midi_note':87,'onset_time':3,'offset_time':4}], 'pedals':[]}
    details=make_score(events,tmp_path,60)
    parsed=converter.parse(tmp_path/'score.musicxml')
    assert details['staff_split']>60
    assert all(isinstance(p.recurse().getElementsByClass(clef.Clef).first(),clef.TrebleClef) for p in parsed.parts)
    assert len(parsed.parts[1].flatten().notes)>0
    stored=json.loads((tmp_path/'score-events.json').read_text())
    actual=score_events(parsed,60)
    def key(n): return n['onset_time'],n['midi_note'],n['offset_time']
    assert sorted(map(key,stored['notes']))==sorted(map(key,actual['notes']))
    assert {p.midi for p in parsed.flatten().pitches}=={73,77,85,87}
    assert (tmp_path/'performance.wav').is_file() and (tmp_path/'score.wav').is_file()
