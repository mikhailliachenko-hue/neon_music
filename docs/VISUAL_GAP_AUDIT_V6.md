# Visual Gap Audit V6

The existing renderer uses a four-lane world with centers `[-3,-1,1,3]`, lane width `2`, road plane `y=-1.8`, and judgment plane `z=0`. Cues travel toward increasing Z; the camera is at `(0,4.5,7.25)` with a 72 degree FOV.

Before V6, `note.gd` selected the footprint texture by lane but the orientation test placed the right semantic on lane 3 without a dedicated visual gate. Hand targets were spheres and side walls faded/cleared from event time rather than their world-space exit.

V6-A keeps the legacy JSON/parser and makes the left/right resources explicit in the cue layer. V6-B replaces the hand-target sphere with an emissive cube and deterministic, seed-derived shard burst. V6-C keeps wall timing semantics but changes only visual cleanup: a wall is retained until its full Z bounds have crossed the camera plus a 1.5m margin.
