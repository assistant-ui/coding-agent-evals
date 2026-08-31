# Output

Return JSON only, matching this schema. No extra keys.

- `verdict`: `pass` | `fail` | `insufficient_evidence`
- `evidence_ids`: list of strings copied from the compact transcript
- `reason`: at most two short sentences

The runner supplies the check ID; do not return it. Cite transcript event
IDs you used. Prefer citing shells or the final message when the verdict is
“nothing relevant happened.” An empty `evidence_ids` list is a last resort.
