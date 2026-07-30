#!/usr/bin/env python3
"""Build the deterministic 56-second Phase 3/4 acceptance slice documents."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'/'python'))
from phrase_grid import attach_phrase_metadata,choreography_config
from validate_choreography_v3 import validate

def main():
 out=ROOT/'output'; beatmap=json.loads((out/'beatmap.json').read_text(encoding='utf-8-sig')); timing=json.loads((out/'beat_grid.json').read_text(encoding='utf-8-sig')); duration=56.0
 timing['duration']=duration; timing['beat_grid']=[b for b in timing.get('beat_grid',[]) if float(b.get('time',0))<=duration]; timing['sections']=[{'id':'intro_teach','role':'intro','start_time':0.0,'end_time':14.0},{'id':'build_1','role':'build','start_time':14.0,'end_time':28.0},{'id':'chorus_1','role':'chorus','start_time':28.0,'end_time':42.0},{'id':'breakdown_1','role':'breakdown','start_time':42.0,'end_time':56.0}]
 beatmap['notes']=[n for n in beatmap.get('notes',[]) if float(n.get('time',0))<=duration]; beatmap['events']=[e for e in beatmap.get('events',[]) if float(e.get('time',e.get('start',0)))<=duration]
 beatmap,timing=attach_phrase_metadata(beatmap,timing,choreography_config())
 slice_map=out/'debug'/'vertical_slice_choreo_v3_beatmap.json';debug=out/'debug'/'vertical_slice_choreo_v3.json';report_path=out/'reports'/'vertical_slice_choreo_v3_validation.json';slice_map.parent.mkdir(parents=True,exist_ok=True);report_path.parent.mkdir(parents=True,exist_ok=True)
 slice_map.write_text(json.dumps(beatmap,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); debug.write_text(json.dumps({'schema':'neon_music.vertical_slice_debug.v3','duration':duration,'beat_interval':timing['beat_interval'],'choreography_config':timing['choreography_config'],'phrase_grid':timing['phrase_grid'],'movement_library':timing['movement_library'],'choreography_plan':timing['choreography_plan'],'movement_events':timing['movement_events']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 report=validate(beatmap,timing);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['summary'],ensure_ascii=False));return 0 if report['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
