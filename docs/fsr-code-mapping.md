# How this serves as validation evidence under the FSR Code (v2)

The Forensic Science Regulator's statutory Code of Practice v2 (in force 2 October
2025) requires every method a forensic unit uses to be shown fit for purpose
(section 24). A timeline tool is part of a method. This page maps the repository to
the Code's validation steps, so a unit can reuse it as **third-party validation data
to verify** (24.3.1-24.3.2, 24.9.11-24.9.17). It is not a validation the unit can sign
off unchanged.

| Code clause | Requirement (short quote) | Where it is met here | Gap the unit must fill |
|---|---|---|---|
| 24.1.2 | "objective evidence that a method ... is fit for the specific purpose", "limitations ... properly understood" | `results/classified.csv`: 30 actions x 16 runs x 6 tool configurations, each outcome classified; limitations in `docs/what-went-wrong.md` | Their own purpose statement |
| 24.2.3 | "Even where a method is ... in widespread use, scientific validity still needs to be demonstrated" | Shows that two widely used tools give wrong, wrong-zone or ambiguous times on FAT/exFAT under default settings | |
| 24.2.6 | external testers should validate "in a comparable manner" and make "the SOP and data available" | SOP: `run_all.sh`, `build/`, `actions/actions.md`. Data: `truth/`, `results/events/`, image SHA-256s | Images are rebuilt from the SOP, not distributed |
| 24.3.8(a)-(b) | end user requirements; specification | Implicit requirement: "the reported time of a file-system event equals the true instant, or is flagged as uncertain" | Write as formal, testable statements (24.4.5) |
| 24.3.8(e), 24.8 | acceptance criteria set in advance | Tolerance fixed at 2.5 s before the runs (FAT's 2 s step), and outcome definitions fixed in `compare/diff.py`'s docstring | Choose a pass threshold (e.g. 100% correct or flagged on the file systems in scope) |
| 24.3.4 | failures declared, not fixed during validation | Failures are reported as found. The Plaso FAT/exFAT error was not worked around in the results | |
| 24.6.1(b) | risk of "ambiguous or misleading outputs" | *ambiguous* outcome: local times in the repeated DST hour, and `mactime -d` output with no zone | Add caveats to SOPs for FAT/exFAT media |
| 24.9.8(e) | "consistent, reliable, accurate and robust results" | Repeatability: every run is scripted and re-runnable. The TSK ambiguous-hour behaviour was reproduced twice | Repeat on the unit's own build |
| 24.9.8(f) | compatibility with "different equipment and different methods" | Differential design: TSK vs Plaso vs analyzeMFT on the same image | Add the unit's commercial tool(s) under their licence terms |
| 24.9.3 | simulated casework material first | Synthetic images only; nothing from real cases | |
| 24.9.18-24.9.19 | "software and firmware" changes need verification | `run_all.sh` is the regression command; `versions.md` pins every version | Re-run on each tool upgrade |
| 24.12.2(c) | "name, version number and manufacturer of any equipment" | `versions.md` | |
| 24.12.2(j) | "any limitations/constraints" | `docs/what-went-wrong.md`; Linux-written evidence only until the Windows kit is run | |
| 24.13.3(a), (c) | caveats; "circumstances in which the use of the method would be inadvisable" | README "What this means for an examiner" | Their own statement of validation completion |

## Suggested caveats a unit could adopt from these results

1. Do not rely on Plaso 20261027 file-system timestamps for FAT or exFAT volumes. Every
   value is 28-31 days late (libfsfat 20260826).
2. For FAT, record the source device's time zone and DST rules. Treat any time in the hour
   after clocks go back as two possible instants.
3. For exFAT with TSK 4.12.1, the on-disk UTC offset is ignored. Check one known file's time
   against another tool before relying on TSK's values.
4. Never put `mactime -d` output into a report without stating the zone; prefer `-y` (UTC, ISO 8601).
