# MeghyanAI Codex Pack

Files to copy into the root of your Quantum-Assisted-Assurance repo before
opening in Codex:

```
AGENTS.md                          ← Codex reads this first (already in repo)
PLANS.md                           ← Step-by-step execution checklist
CODEX_PROMPT.md                    ← The prompt to paste into Codex
.agents/skills/quantum_tree_portal.md  ← Skill for pipeline wiring
```

## How to use

1. Copy all 4 files into the root of your repo (or merge with existing AGENTS.md)
2. Open the repo in Codex
3. Paste the contents of CODEX_PROMPT.md as your first message
4. Let Codex work through all 9 steps autonomously

## What Codex will build

- Public landing page with live Quantum Tree demo (no login)
- /pricing page with 3 packages (Red Team / API / Certification)
- Rebuilt studio.html showing real pipeline data
- POST /api/demo/run endpoint wired to real Quantum Tree pipeline
- Dark minimal design matching MeghyanAI brand

## Run locally after Codex finishes

```bash
cd Quantum-Assisted-Assurance
.\.venv\Scripts\python.exe -m meghyan_portal.app
# Open http://127.0.0.1:5055
```

Demo credentials:
- Admin: admin@meghyan.ai / admin-demo
- Red Team customer: redteam@client.ai / rt-demo
- API customer: api@client.ai / api-demo
- Enterprise: enterprise@client.ai / ent-demo
- Public demo: no login (3 runs/hour)
