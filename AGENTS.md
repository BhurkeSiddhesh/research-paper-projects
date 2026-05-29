# Research Paper Side Projects

## Tech Stack
- Python, depending on the paper
- HTML/CSS/JS (if we are building web applications)

## Structural Rules
- All research projects go into this workspace `c:\Users\siddh\Desktop\Projects\research-paper-projects`.
- Each paper implemented will have its own sub-directory.

## Known Patterns and Constraints
- We must maintain the original paper's integrity when recreating the code.
- We must provide a writeup explaining the paper.
- The `science_skills_common` uses `fcntl` which is not available on Windows, so we should avoid using it or rely on powershell `Invoke-RestMethod` for simple arXiv API calls.

## Active Focus
- Implementing the side project based on InvAgent (arXiv:2407.11384): A Multi-Agent System for Supply Chain Inventory Management using LLMs.

## Change Log
- 2026-05-29: Created comprehensive README.md documenting InvAgent (arXiv:2407.11384) and Optimization Heuristics (arXiv:2503.03350). Set up task.md tracking ledger. Prepared repository for default main branch commit.
- 2026-05-28: Selected InvAgent (2407.11384) for the side project. Created implementation plan.
- 2026-05-28: Initialized project workspace, added AGENTS.md and JULES_LOG.json.

## Learned Knowledge
- Need to parse arXiv IDs from filenames directly since the skill throws `fcntl` error on Windows.
