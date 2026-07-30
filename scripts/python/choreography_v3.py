"""Deterministic Phase 3 semantic choreography (additive to phrase_grid v1)."""
from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA="neon_music.movement_events.v1"; LIB_SCHEMA="neon_music.movement_library.v2"; PLAN_SCHEMA="neon_music.choreography_plan.v2"
WEIGHTS={"music_alignment":.17,"phrase_coherence":.18,"teachability":.14,"transition_quality":.12,"left_right_balance":.08,"section_fit":.10,"energy_fit":.07,"novelty":.04,"callback_quality":.04,"fatigue_safety":.04,"visual_readability":.02}
def _m(i,n,c,side="center",intensity=.25,durations=(2,4),prep=2,recovery=0,level="standing",travel="none",space="center",fatigue="legs_light",mirror=None,cue="HOLD_RING",prev=(),nxt=(),tags=("beginner",)):
 return {"id":i,"display_name":n,"category":c,"side":side,"difficulty":1,"intensity":intensity,"duration_beats":list(durations),"preparation_beats":prep,"recovery_beats":recovery,"body_level":level,"travel":travel,"required_space":space,"fatigue_group":fatigue,"mirror_id":mirror or i,"allowed_previous":[],"forbidden_previous":list(prev),"allowed_next":[],"forbidden_next":list(nxt),"max_repeats":4,"preferred_sections":["intro","verse","build","chorus","drop","breakdown","outro"],"preferred_accents":["beat","downbeat"],"cue_archetype":cue,"tags":list(tags)}
MOVEMENT_LIBRARY={
"IDLE_BOUNCE":_m("IDLE_BOUNCE","Idle Bounce","base_groove",intensity=.15,durations=(4,8),cue="HOLD_RING"),"MARCH":_m("MARCH","March","locomotion",intensity=.22,durations=(4,8),cue="ALTERNATING_FOOT_PULSES"),
"STEP_LEFT":_m("STEP_LEFT","Step Left","locomotion","left",.30,travel="left",space="left",mirror="STEP_RIGHT",cue="LANE_STEP_LEFT",tags=("beginner","side_step")),"STEP_RIGHT":_m("STEP_RIGHT","Step Right","locomotion","right",.30,travel="right",space="right",mirror="STEP_LEFT",cue="LANE_STEP_RIGHT",tags=("beginner","side_step")),
"DOUBLE_STEP_LEFT":_m("DOUBLE_STEP_LEFT","Double Step Left","locomotion","left",.40,(4,),travel="left",space="left",mirror="DOUBLE_STEP_RIGHT",cue="LANE_DOUBLE_STEP_LEFT"),"DOUBLE_STEP_RIGHT":_m("DOUBLE_STEP_RIGHT","Double Step Right","locomotion","right",.40,(4,),travel="right",space="right",mirror="DOUBLE_STEP_LEFT",cue="LANE_DOUBLE_STEP_RIGHT"),
"STEP_TOUCH_LEFT":_m("STEP_TOUCH_LEFT","Step Touch Left","locomotion","left",.32,mirror="STEP_TOUCH_RIGHT",cue="FOOT_PAD_LEFT"),"STEP_TOUCH_RIGHT":_m("STEP_TOUCH_RIGHT","Step Touch Right","locomotion","right",.32,mirror="STEP_TOUCH_LEFT",cue="FOOT_PAD_RIGHT"),
"LEAN_LEFT":_m("LEAN_LEFT","Lean Left","core","left",.28,fatigue="core",mirror="LEAN_RIGHT",cue="SIDE_SWEEP_FROM_RIGHT",nxt=("LEAN_RIGHT",)),"LEAN_RIGHT":_m("LEAN_RIGHT","Lean Right","core","right",.28,fatigue="core",mirror="LEAN_LEFT",cue="SIDE_SWEEP_FROM_LEFT",nxt=("LEAN_LEFT",)),
"SIDE_REACH_LEFT":_m("SIDE_REACH_LEFT","Side Reach Left","upper_body","left",.30,fatigue="upper_body",mirror="SIDE_REACH_RIGHT",cue="HAND_TARGET_LEFT"),"SIDE_REACH_RIGHT":_m("SIDE_REACH_RIGHT","Side Reach Right","upper_body","right",.30,fatigue="upper_body",mirror="SIDE_REACH_LEFT",cue="HAND_TARGET_RIGHT"),
"SQUAT":_m("SQUAT","Squat","legs",intensity=.62,prep=4,recovery=2,level="low",fatigue="legs_heavy",cue="OVERHEAD_BAR",nxt=("JUMP",)),"DUCK":_m("DUCK","Duck","core",intensity=.48,prep=4,recovery=2,level="low",fatigue="legs_heavy",cue="LOW_CLEARANCE_GATE",prev=("JUMP",)),
"SMALL_JUMP":_m("SMALL_JUMP","Small Jump","jump",intensity=.62,durations=(2,),prep=4,recovery=2,fatigue="cardio",cue="FLOOR_PULSE_SMALL"),"JUMP":_m("JUMP","Jump","jump",intensity=.82,durations=(2,),prep=4,recovery=4,fatigue="cardio",cue="FLOOR_PULSE_LARGE",prev=("SQUAT",),nxt=("DUCK",)),
"PUNCH_LEFT":_m("PUNCH_LEFT","Punch Left","upper_body","left",.38,(2,),fatigue="upper_body",mirror="PUNCH_RIGHT",cue="HAND_TARGET_LEFT"),"PUNCH_RIGHT":_m("PUNCH_RIGHT","Punch Right","upper_body","right",.38,(2,),fatigue="upper_body",mirror="PUNCH_LEFT",cue="HAND_TARGET_RIGHT"),
"DOUBLE_PUNCH":_m("DOUBLE_PUNCH","Double Punch","upper_body",intensity=.48,fatigue="upper_body",cue="HAND_TARGET_DOUBLE"),"CLAP":_m("CLAP","Clap","upper_body",intensity=.25,fatigue="upper_body",cue="CENTER_CONVERGE_TARGETS"),"OPEN_ARMS":_m("OPEN_ARMS","Open Arms","upper_body",intensity=.24,durations=(4,),fatigue="upper_body",cue="OUTWARD_EXPAND_TARGETS"),
"RUN_IN_PLACE":_m("RUN_IN_PLACE","Run In Place","cardio",intensity=.70,durations=(4,8),fatigue="cardio",cue="ALTERNATING_FOOT_PULSES"),"HIGH_KNEES":_m("HIGH_KNEES","High Knees","cardio",intensity=.78,durations=(4,8),fatigue="cardio",cue="HIGH_FOOT_PULSES"),"FREEZE":_m("FREEZE","Freeze","phrase_control",intensity=.08,durations=(2,4,8),fatigue="core",cue="HOLD_RING"),"POSE":_m("POSE","Pose","phrase_control",intensity=.12,durations=(4,8),cue="POSE_FRAME")}
ALIASES={"MARCH_IN_PLACE":"MARCH","BOUNCE":"IDLE_BOUNCE","ARMS_OPEN":"OPEN_ARMS","BASE_RECOVERY":"IDLE_BOUNCE"}
def _b(role,*items): return {"role":role,"events":[{"movement":m,"duration_beats":d} for m,d in items]}
def _pattern(role,pindex,variant):
 if pindex<=0 or role=="intro":
  a="STEP_LEFT" if variant%2==0 else "STEP_TOUCH_LEFT"; r=MOVEMENT_LIBRARY[a]["mirror_id"]; return "TEACH_REPEAT_MIRROR_COMBINE",[_b("TEACH",(a,4),(a,4)),_b("REPEAT",(a,4),(a,4)),_b("MIRROR",(r,4),(r,4)),_b("COMBINE",(a,2),(r,2),(a,2),(r,2))]
 if role in {"chorus","drop","outro"}:
  s=["STEP_TOUCH_LEFT","PUNCH_LEFT","STEP_TOUCH_RIGHT","PUNCH_RIGHT"]
  if variant==1:s[-1]="DOUBLE_PUNCH"
  if variant==2:s=[MOVEMENT_LIBRARY[m]["mirror_id"] for m in s]
  if variant==3:s[-1]="POSE"
  p=tuple((m,2) for m in s); q=tuple((MOVEMENT_LIBRARY[m]["mirror_id"],d) for m,d in p); return "CALLBACK_VARIATION_MIRROR_SIGNATURE",[_b("CALLBACK",*p),_b("VARIATION",*p),_b("MIRROR",*q),_b("SIGNATURE",*p)]
 if role=="build": return "BUILD",[_b("REPEAT",("STEP_TOUCH_LEFT",4),("STEP_TOUCH_RIGHT",4)),_b("ALTERNATE",("PUNCH_LEFT",2),("PUNCH_RIGHT",2),("PUNCH_LEFT",2),("PUNCH_RIGHT",2)),_b("COMBINE",("STEP_TOUCH_LEFT",2),("PUNCH_LEFT",2),("STEP_TOUCH_RIGHT",2),("PUNCH_RIGHT",2)),_b("BUILD",("STEP_LEFT",2),("PUNCH_LEFT",2),("STEP_RIGHT",2),("DOUBLE_PUNCH",2))]
 if role=="breakdown": return "RECOVERY",[_b("RECOVERY",("MARCH",8)),_b("RECOVERY",("IDLE_BOUNCE",8)),_b("RECOVERY",("OPEN_ARMS",4),("FREEZE",4)),_b("RECOVERY",("MARCH",4),("POSE",4))]
 a,b=(("STEP_TOUCH_LEFT","PUNCH_LEFT") if variant%2==0 else ("STEP_LEFT","SIDE_REACH_LEFT")); ar,br=MOVEMENT_LIBRARY[a]["mirror_id"],MOVEMENT_LIBRARY[b]["mirror_id"]; return "REPEAT_ALTERNATE_MIRROR_COMBINE",[_b("REPEAT",(a,4),(a,4)),_b("ALTERNATE",(a,2),(b,2),(a,2),(b,2)),_b("MIRROR",(ar,2),(br,2),(ar,2),(br,2)),_b("COMBINE",(a,2),(b,2),(ar,2),(br,2))]
def _role(phrase,pos,count):
 raw=str(phrase.get("section_role",phrase.get("section_id",""))).lower()
 for token,value in (("intro","intro"),("build","build"),("chorus","chorus"),("drop","drop"),("break","breakdown"),("outro","outro")):
  if token in raw:return value
 r=pos/max(1,count-1)
 return "intro" if r<.1 else "build" if r<.44 and r>=.30 else "chorus" if (.44<=r<.62 or .72<=r<.90) else "breakdown" if .62<=r<.72 else "outro" if r>=.90 else "verse"
def _flat(p):return [e for b in p for e in b["events"]]
def _balance(events):
 l=sum(MOVEMENT_LIBRARY[e["movement"]]["intensity"]*e["duration_beats"] for e in events if MOVEMENT_LIBRARY[e["movement"]]["side"]=="left");r=sum(MOVEMENT_LIBRARY[e["movement"]]["intensity"]*e["duration_beats"] for e in events if MOVEMENT_LIBRARY[e["movement"]]["side"]=="right");t=l+r;return {"left_load":round(l,3),"right_load":round(r,3),"difference_ratio":round(abs(l-r)/t if t else 0,4)}
def _violations(patterns,difficulty):
 f=_flat(patterns);out=[]
 if any(sum(e["duration_beats"] for e in b["events"])!=8 for b in patterns):out.append("eight_count_duration_mismatch")
 if sum(e["movement"] in {"JUMP","SMALL_JUMP"} for e in f)>{"beginner":2,"normal":4,"advanced":6}.get(difficulty,4):out.append("jump_limit_exceeded")
 for a,b in zip(f,f[1:]):
  if b["movement"] in MOVEMENT_LIBRARY[a["movement"]]["forbidden_next"] or a["movement"] in MOVEMENT_LIBRARY[b["movement"]]["forbidden_previous"]:out.append(f"forbidden_transition:{a['movement']}->{b['movement']}")
 if _balance(f)["difference_ratio"]>.20:out.append("left_right_imbalance")
 return sorted(set(out))
def _metrics(patterns,role,learned,pindex):
 f=_flat(patterns);u={e["movement"] for e in f};new=u-learned;bal=_balance(f);return {"music_alignment":1.0,"phrase_coherence":.92,"teachability":max(0,1-max(0,len(new)-1)*.35),"transition_quality":.94,"left_right_balance":1-bal["difference_ratio"],"section_fit":.95,"energy_fit":.92,"novelty":min(1,.45+.15*len(new)),"callback_quality":1.0 if role in {"chorus","drop","outro"} and pindex>0 else .65,"fatigue_safety":.95,"visual_readability":1.0}
def _fatigue(events):
 d={k:0.0 for k in ("legs_light","legs_heavy","cardio","upper_body","core")}
 for e in events:d[e["fatigue_group"]]+=e["intensity"]*e["duration_beats"]
 return {k:round(v,3) for k,v in d.items()}
def build_plan(timing,grid,cfg):
 interval=max(.001,float(timing.get("beat_interval",.5)));duration=float(timing.get("duration",0));phrases=grid.get("phrases",[]);learned={"MARCH","IDLE_BOUNCE","OPEN_ARMS"};events=[];debug=[];ei=0
 for pos,p in enumerate(phrases):
  if not p.get("count8_blocks") or int(p.get("index",pos))<0:continue
  pi=int(p.get("index",pos));role=_role(p,pos,len(phrases));cands=[]
  for ci in range(max(8,int(cfg.get("candidate_count",8)))):
   template,patterns=_pattern(role,pi,ci%4);viol=_violations(patterns,str(cfg.get("difficulty","normal")));metrics=_metrics(patterns,role,learned,pi);score=round(sum(metrics[k]*WEIGHTS[k] for k in WEIGHTS),6);cands.append({"candidate":ci,"template":template,"patterns":patterns,"metrics":metrics,"score":score,"hard_violations":viol})
  valid=[c for c in cands if not c["hard_violations"]];sel=max(valid or cands,key=lambda c:(not c["hard_violations"],c["score"],-c["candidate"]));p.update({"template":sel["template"],"selected_candidate":sel["candidate"],"candidate_score":sel["score"],"section_role":role});cursor=0;pe=[]
  for bi,b in enumerate(sel["patterns"]):
   if bi<len(p["count8_blocks"]):p["count8_blocks"][bi].update({"role":b["role"],"template":sel["template"],"pattern_id":f"{p['id']}_{b['role'].lower()}"})
   for item in b["events"]:
    m=item["movement"];meta=MOVEMENT_LIBRARY[m];beats=item["duration_beats"];hit=float(p["start_time"])+cursor*interval;beat_index=int(p.get("start_beat_index",0))+cursor;cursor+=beats
    if hit<0 or hit>duration:continue
    new=m not in learned;lead=6 if b["role"] in {"COMBINE","BUILD","SIGNATURE"} else 4 if new else max(2,meta["preparation_beats"]);instruction=max(0,hit-lead*interval);x=.34 if meta["side"]=="left" else .68 if meta["side"]=="right" else .49
    e={"id":f"move_{ei:05d}","type":"movement","schema":SCHEMA,"movement":m,"display_name":meta["display_name"],"instruction_time":round(instruction,6),"spawn_time":round(instruction,6),"pre_hit_time":round(max(instruction,hit-interval),6),"hit_time":round(hit,6),"feedback_end_time":round(hit+.15,6),"despawn_time":round(hit+.25,6),"duration_beats":beats,"duration":round(beats*interval,6),"lead_beats":lead,"lead_time":round(hit-instruction,6),"phrase_id":p["id"],"phrase_index":pi,"count8_index":bi,"beat_index":beat_index,"motif_id":"signature_A" if b["role"] in {"CALLBACK","SIGNATURE"} else f"{p['id']}_motif_A","phrase_template":sel["template"],"block_role":b["role"],"side":meta["side"],"intensity":meta["intensity"],"difficulty":1,"is_new":new,"is_mirrored":meta["side"]=="right","mirror_of":meta["mirror_id"] if meta["side"]=="right" else "","cue_archetype":meta["cue_archetype"],"cue_bounds_normalized":{"left":x,"top":.18,"width":.18,"height":.64},"mandatory":True,"lifecycle":["SPAWN","PREVIEW","APPROACH","PRE_HIT","HIT","FEEDBACK","DESPAWN"],"judgment_plane":"receptor_hit_z","judgment_z":0.0,"expected_cross_time":round(hit,6),"judgment_error":0.0,"preparation_pose":"neutral","end_pose":meta["body_level"],"fatigue_group":meta["fatigue_group"],"candidate_score":sel["score"]};events.append(e);pe.append(e);learned.add(m);ei+=1
  p["left_right_balance"]=_balance(pe);p["fatigue_state"]=_fatigue(pe)
  for event in pe:event.update({"section_role":role,"left_right_balance":p["left_right_balance"],"fatigue_state":p["fatigue_state"]})
  rej=[c for c in cands if c["hard_violations"]];debug.append({"phrase_id":p["id"],"selected_candidate":sel["candidate"],"candidate_scores":[{"candidate":c["candidate"],"score":c["score"],"metrics":c["metrics"]} for c in cands],"rejected_candidates":[c["candidate"] for c in rej],"rejection_reasons":[{"candidate":c["candidate"],"reasons":c["hard_violations"]} for c in rej]})
 return {"schema":PLAN_SCHEMA,"seed":int(cfg.get("seed",3407)),"candidate_count":max(8,int(cfg.get("candidate_count",8))),"weights":WEIGHTS,"phrase_debug":debug,"movement_events":events}
def build_movement_events(timing,phrase_grid,config=None):return build_plan(timing,phrase_grid,config or {})["movement_events"]
def _active(t,events):
 previous=None
 for e in events:
  if e["hit_time"]<=t<e["hit_time"]+e["duration"]:return e
  if e["hit_time"]<=t:previous=e
 return previous
def attach_phrase_metadata(beatmap,timing,config=None):
 import phrase_grid as base
 cfg=base.choreography_config(**(config or {}));cfg.update({"seed":int((config or {}).get("seed",3407)),"candidate_count":max(8,int((config or {}).get("candidate_count",8))),"difficulty":str((config or {}).get("difficulty","normal")),"performer_safe_zone":{"left":0.0,"top":0.0,"width":.24,"height":1.0},"gameplay_corridor":{"left":.30,"top":.08,"width":.66,"height":.84},"judgment_tolerance_seconds":.0334});grid=base.build_phrase_grid(timing,cfg);plan=build_plan(timing,grid,cfg);events=plan["movement_events"];interval=max(.001,float(timing.get("beat_interval",.5)));anchor=float(grid.get("phrase_anchor_time",0))
 for note in beatmap.get("notes",[]):
  t=float(note.get("time",0));position=round((t-anchor)/interval);pi,pb=divmod(position,32);e=_active(t,events)
  if e:
   for key in ("movement","cue_archetype","lead_beats","instruction_time","is_mirrored","judgment_plane","judgment_z","phrase_template","candidate_score"):note[key]=e[key]
   note["movement_event_id"]=e["id"]
  else:note.update({"movement":"MARCH","cue_archetype":"ALTERNATING_FOOT_PULSES","lead_beats":2,"instruction_time":round(max(0,t-2*interval),6),"is_mirrored":False,"judgment_plane":"receptor_hit_z","judgment_z":0.0})
  note.update({"hit_time":round(t,6),"phrase_id":f"phrase_{pi:03d}","phrase_beat":pb,"count8_index":pb//8})
 library={"schema":LIB_SCHEMA,"movements":MOVEMENT_LIBRARY,"aliases":ALIASES}
 for d in (beatmap,timing):d.update({"choreography_config":cfg,"phrase_grid":grid,"movement_library":library,"movement_events":events,"choreography_plan":plan})
 return beatmap,timing
def deterministic_digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
