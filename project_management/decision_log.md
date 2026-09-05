# Project Decision Log

Record only decisions that change scope, interfaces, evaluation or reported claims. Short messages and routine debugging do not belong here.

| Date | Decision | Reason/evidence | Affected work | Responsible role |
| --- | --- | --- | --- | --- |
| 2026-09-05 | Use the official public BESSTIE validation split as the project test set; create a 15% stratified validation set from official train | The public official test split is withheld | Data, modelling and evaluation | Data and report coordination |
| 2026-09-05 | Preserve case, spelling, punctuation, emoji, hashtags and regional expressions; normalise whitespace only | These are potential variety, sentiment and sarcasm cues | Data and modelling | Data and report coordination |
| 2026-09-05 | Detect exact/case-only duplicates globally and remove conflicting-label duplicate groups | Prevent leakage and undocumented label ambiguity | Data, modelling and evaluation | Data and report coordination |
| 2026-09-05 | Do not use SHA256 or a local hash-freeze process | Team preference; schema validation, versioned paths and generated audit reports provide sufficient traceability for this project | All roles | Data and report coordination |

## New decision template

| YYYY-MM-DD | What was decided | Why it was decided | Affected work | Responsible role |
