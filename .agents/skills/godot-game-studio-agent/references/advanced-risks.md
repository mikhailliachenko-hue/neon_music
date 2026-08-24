# Advanced Game-System Risks

Read this reference only when the named system is actually in scope. It routes risk; it does not authorize a large subsystem or external service.

## Saves

Define the saved schema, version, ownership, write boundary, and recovery behavior before implementation. Use atomic replacement rather than overwriting the only good copy. Test new save, round trip, interrupted/corrupt input, incompatible version, missing fields, and platform path behavior. Do not add speculative migrations; support only explicitly required versions.

## Randomness and procedural generation

Expose and record the seed. When reproduction matters, use a fixed simulation step, semantic input trace, selected state checkpoints, and first-divergence reporting. Test generation invariants and failure bounds, not only one attractive seed.

## Economy and progression

List every source, sink, stock, cap, unlock, and irreversible choice. Simulate normal, optimal, idle, and extreme paths before content scaling. A reward should change decisions or pacing, not merely inflate numbers. Monetization requires separate product and compliance authorization.

## Multiplayer

Stop ordinary implementation until authority, replication boundaries, latency assumptions, prediction/reconciliation, disconnect/rejoin, persistence, abuse, privacy, and deployment ownership have a dedicated plan. The core Skill does not provide a complete network architecture.

## Live operations, telemetry, and commerce

Require explicit scope for collected events, retention, consent, accounts, environments, release controls, rollback, support ownership, pricing, and platform compliance. Do not create accounts, deploy services, publish builds, or add paid dependencies from a design discussion alone.

Record detected risk in `docs/dev-plan.md`, mark the affected feature blocked on a dedicated design when appropriate, and continue only with unaffected local work.
