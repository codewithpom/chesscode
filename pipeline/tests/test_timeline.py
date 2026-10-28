from chesscode.stages.timeline import layout

def test_timing_contract():
    segments=[{"kind":"cold_open","ply":1,"text":"hello"},{"kind":"ply","ply":1,"text":"move"}]
    voice=[{"segment_id":"s1","audio":"audio/en_seg-000.mp3","duration_ms":10000,"words":[{"w":"hello","start_ms":0,"end_ms":500}]},{"segment_id":"s2","audio":"audio/en_seg-001.mp3","duration_ms":10000,"words":[{"w":"move","start_ms":0,"end_ms":500}]}]
    result=layout(segments, voice, [{"type":"blunder","ply":1,"intensity":2}], [{"ply":1}], {"outro_ms":20000,"reaction_gap_ms":900,"min_chapters":3,"chapter_min_ms":10000,"beats":{"min_gap_ms":20000,"min_gap_intensity3_ms":60000,"est_ms_per_ply":4500,"priority":["checkmate","blunder","brilliant","missed_win","comeback","rest"],"poses":{"blunder":"facepalm"}}})
    assert result['narration'][1]['start_ms'] >= result['narration'][0]['start_ms']+10000
    assert result['narration'][1]['start_ms'] == result['narration'][0]['start_ms']+10000+900
    assert result['plies_show_at'][1] >= result['narration'][1]['start_ms']
    assert result['duration_ms'] == result['narration'][-1]['start_ms']+10000+20000
    assert len(result['chapters']) >= 3
    assert all(b['start_ms']-a['start_ms']>=10000 for a,b in zip(result['chapters'],result['chapters'][1:]))
