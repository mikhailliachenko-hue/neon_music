# Game Design and Player Experience

Use this reference for core loops, onboarding, level design, game feel, camera, UI, audio feedback, pacing, or difficulty.

## Causal chain

Check: `player intent -> input -> action starts -> state changes -> result is perceived -> cause is understood`. Diagnose the broken layer instead of adding generic juice.

## Player learning

For every required verb, observe whether the player did not see the cue, saw but did not understand, understood but could not execute, or could execute but did not consider it useful. Teach one new verb or combination at a time. After prompting, require an unprompted repetition and later a changed-context application. Fix layout, affordance, timing, controls, or motivation before adding larger text.

## Level test record

Record the mechanic under test, prerequisite knowledge, new knowledge, meaningful decisions, failure readability, retry time, and unintended solutions. A level should let the player observe, predict, act, and correct. Preserve unintended solutions that express mastery without breaking the rules.

## Feel measurements

- Platformer: jump buffer, coyote time, variable jump, corner correction, air control, retry latency.
- Action: startup/active/recovery, input queue, cancel rules, hit stop, invulnerability, threat readability.
- Shooter: aim response, recoil readability, hit confirmation, damage direction, target acquisition.
- Strategy/card: selection confidence, command acknowledgement, state readability, reversibility, information latency.
- Puzzle/narrative: affordance, state persistence, consequence clarity, pacing, skip/history controls.

Do not copy another game's frame values. Tune against the current fantasy, audience, difficulty, input device, and measured play.

## Feedback, camera, and UI

- Distinguish successful, ineffective, damaging, rewarding, and terminal outcomes through more than one appropriate channel.
- Shake, flashes, hit stop, vibration, and loud transients need proportional intensity controls or alternatives.
- Camera behavior must preserve threat, landing, navigation, and objective readability.
- UI should communicate the current decision and state, not mirror every internal variable.

## Audio information

Prefer named buses such as `Music`, `UI`, `Player`, `Enemies`, `Environment`, and `Voice` when needed. For critical sounds, define purpose, priority, concurrency, mix behavior, and a non-audio equivalent. Test timing-sensitive audio against real output latency.

## Source notes

- The [BioShock](https://www.gamedeveloper.com/design/postmortem-2k-boston-2k-australia-s-bioshock) and [Mark of the Ninja](https://www.gamedeveloper.com/design/classic-postmortem-klei-entertainment-s-i-mark-of-the-ninja-i-) postmortems describe redesigning onboarding from fresh-player behavior.
- Metanet's [N++ level-design talk](https://www.gdcvault.com/play/1023282/Empowering-the-Player-Level-Design) frames levels as spaces for player agency across skill levels.
- Nintendo's [Celeste developer interview](https://www.nintendo.com/jp/topics/article/19b31c18-6544-11e8-b9c0-063b7ac45a6d) illustrates the small, tunable rules behind responsive platforming.
