# PB-1 verifier fixtures

Harbor agent jobs read `/logs/agent/trajectory.json`. Gold skips workflow.

`phase-b-trajectory.json` is the C9 copy of
`jobs/2026-08-19__00-59-44/pb-1__iL3XzHC/agent/trajectory.json` (ATIF-v1.7).
`offline.py` uses this file. Do not play it in `solve.sh`. Harbor does not
run `offline.py`.
