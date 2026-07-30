#!/usr/bin/env python3
from __future__ import annotations
import copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'/'python'))
from phrase_grid import attach_phrase_metadata, choreography_config
from choreography_v3 import MOVEMENT_LIBRARY, deterministic_digest
from validate_choreography_v3 import validate

def fixture():
 interval=.5;beats=[{'index':i,'time':i*interval,'bar_phase':i%4,'downbeat':i%4==0} for i in range(256)]
 timing={'beat_interval':interval,'duration':128.0,'anchor':{'time':0.0},'beat_grid':beats}
 notes=[{'time':i*interval,'lane':i%4,'type':'note'} for i in range(256)]
 return {'schema':'neon_music.beatmap.v3','notes':notes,'events':[]},timing

def main():
 a,t=fixture();a1,t1=attach_phrase_metadata(copy.deepcopy(a),copy.deepcopy(t),choreography_config());a2,t2=attach_phrase_metadata(copy.deepcopy(a),copy.deepcopy(t),choreography_config())
 required={'IDLE_BOUNCE','MARCH','STEP_LEFT','STEP_RIGHT','DOUBLE_STEP_LEFT','DOUBLE_STEP_RIGHT','STEP_TOUCH_LEFT','STEP_TOUCH_RIGHT','LEAN_LEFT','LEAN_RIGHT','SIDE_REACH_LEFT','SIDE_REACH_RIGHT','SQUAT','DUCK','SMALL_JUMP','JUMP','PUNCH_LEFT','PUNCH_RIGHT','DOUBLE_PUNCH','CLAP','OPEN_ARMS','RUN_IN_PLACE','HIGH_KNEES','FREEZE','POSE'}
 assert required==set(MOVEMENT_LIBRARY);assert deterministic_digest(t1['choreography_plan'])==deterministic_digest(t2['choreography_plan'])
 assert all(len(p['candidate_scores'])>=8 for p in t1['choreography_plan']['phrase_debug']);assert all(2<=e['duration_beats']<=8 for e in t1['movement_events'])
 assert {'TEACH_REPEAT_MIRROR_COMBINE','BUILD','CALLBACK_VARIATION_MIRROR_SIGNATURE','RECOVERY'} <= {p.get('template') for p in t1['phrase_grid']['phrases']}
 report=validate(a1,t1);assert not report['hard_errors'],report['hard_errors'];assert report['summary']['mandatory_cue_safe_zone_overlap']==0;assert report['summary']['duration_2_to_8_ratio']>=.8
 print('phase3_choreography: OK',report['summary'])
if __name__=='__main__':main()
