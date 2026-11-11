# The 30 actions

Same list in `run_actions.py` (Linux) and `run_actions.ps1` (Windows 11 kit). Spacing is 12 s
(the guide suggests 60 s; 12 s keeps a run to 6 minutes so a DST scenario can start
3 minutes before the clock change and cross it, while staying far above the 2.5 s tolerance).

`check_path` is where the action's time should land: the file itself, except for a
delete, which leaves no time on the deleted file and is checked on the parent folder's
modified time. Earlier times of a file that is later renamed or moved are checked under
its final name.

| # | Action | Path | From |
|---|---|---|---|
| 1 | mkdir | /docs | |
| 2 | mkdir | /archive | |
| 3 | create | /docs/report.txt | |
| 4 | modify | /docs/report.txt | |
| 5 | create | /docs/notes.txt | |
| 6 | copy | /docs/notes_copy.txt | /docs/notes.txt |
| 7 | rename | /docs/notes_v2.txt | /docs/notes_copy.txt |
| 8 | move | /archive/notes_v2.txt | /docs/notes_v2.txt |
| 9 | modify | /docs/report.txt | |
| 10 | create | /docs/budget.csv | |
| 11 | zip | /archive/budget.zip | /docs/budget.csv |
| 12 | delete | /docs/budget.csv | |
| 13 | mkdir | /restored | |
| 14 | unzip | /restored/budget.csv | /archive/budget.zip |
| 15 | create | /docs/run.sh (`run.cmd` on Windows) | |
| 16 | access ("run a program") | /docs/run.sh | |
| 17 | mkdir | /photos | |
| 18 | create | /photos/img001.jpg | |
| 19 | create | /photos/img002.jpg | |
| 20 | rename | /photos/holiday.jpg | /photos/img002.jpg |
| 21 | delete | /photos/img001.jpg | |
| 22 | modify | /docs/notes.txt | |
| 23 | copy | /archive/report_backup.txt | /docs/report.txt |
| 24 | move | /restored/notes.txt | /docs/notes.txt |
| 25 | create | /docs/final.txt | |
| 26 | modify | /docs/final.txt | |
| 27 | rename | /docs/final_v2.txt | /docs/final.txt |
| 28 | access | /archive/report_backup.txt | |
| 29 | delete | /archive/budget.zip | |
| 30 | create | /done.txt | |

Not in the Linux runs: log off/on (no Windows session), and "run a program" is a read
of a script rather than an execution recorded by Prefetch. The Windows kit executes
`run.cmd`, which Prefetch records.
