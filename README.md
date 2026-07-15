# vonatverseny
# Vonatverseny (Train Race)

A browser-based train racing game written in vanilla JavaScript with HTML5 Canvas — no frameworks, no build step, one file.

**Play it here:** https://Naka9307.github.io/vonatverseny/ 

## Gameplay

Race your steam locomotive against a bot that gets faster on every level.

- Mash **Space** (or the on-screen button) — every press adds a burst of steam; stop pressing and drag slows you down
- **W / ↑** to jump: clear fallen logs and catch floating boost stars mid-air
- Yellow trackside signs show each curve's speed limit (km/h) — enter faster and you skid
- Ride over coin rows to collect currency, then spend it in the workshop (upgrades) and the paint shop (liveries)
- Local profiles with persistent progress

## Tech notes

- **1D simulation, 2D rendering:** every entity lives on a single track-distance axis; screen positions are derived from a sampled centerline (position + heading + curvature every 2 m), so collision checks stay one-dimensional even on a winding track
- **Procedural tracks:** seeded per level (deterministic), built from straight and arc segments with a bounded heading so the course always progresses forward
- **Physics-based curve limits:** v = √(a·R), rendered as trackside signs
- **Frame-independent movement:** `requestAnimationFrame` with delta-time; exponential drag makes the tap-rate ↔ equilibrium-speed relationship tunable in one formula
- **Storage adapter:** persists to `localStorage`, with graceful in-memory fallback

## Roadmap

- [x] Core race loop, curves, jumping, pickups
- [x] Economy: coins, upgrades, liveries, local profiles
- [x] Public hosting (GitHub Pages)
- [ ] Real authentication (Google + email via Supabase Auth)
- [ ] FastAPI backend with server-side reward validation
- [ ] Leaderboard, PWA install
