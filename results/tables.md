1828 tool-reported times checked (16 runs: 4 file systems x 4 time-zone scenarios x 30 actions, 6 tool configurations). 502 (27%) were not the true instant: 264 wrong value, 146 right clock reading in the wrong zone, 76 ambiguous, 16 missing.

| Tool (version) | Correct | Wrong zone | Ambiguous | Wrong value | Missing | Not on disk* | Correct % |
|---|---|---|---|---|---|---|---|
| TSK fls 4.12.1 (default) | 239 | 92 | 13 | 0 | 0 | 136 | 69.5 |
| TSK fls 4.12.1 -z <writer zone> | 299 | 32 | 13 | 0 | 0 | 136 | 86.9 |
| TSK mactime 4.12.1 -z, -d display | 272 | 22 | 50 | 0 | 0 | 136 | 79.1 |
| Plaso 20261027 (default) | 204 | 0 | 0 | 132 | 8 | 136 | 59.3 |
| Plaso 20261027 --timezone <writer zone> | 204 | 0 | 0 | 132 | 8 | 136 | 59.3 |
| analyzeMFT 3.1.1 (NTFS only) | 108 | 0 | 0 | 0 | 0 | 12 | 100.0 |

| File system / tool | Correct | Wrong zone | Ambiguous | Wrong value | Missing | Not on disk* | Correct % |
|---|---|---|---|---|---|---|---|
| exfat / plaso | 0 | 0 | 0 | 80 | 8 | 32 | 0.0 |
| exfat / plaso_z | 0 | 0 | 0 | 80 | 8 | 32 | 0.0 |
| exfat / tsk_fls | 22 | 66 | 0 | 0 | 0 | 32 | 25.0 |
| exfat / tsk_fls_z | 56 | 32 | 0 | 0 | 0 | 32 | 63.6 |
| exfat / tsk_mactime_z | 56 | 22 | 10 | 0 | 0 | 32 | 63.6 |
| ext4 / plaso | 96 | 0 | 0 | 0 | 0 | 24 | 100.0 |
| ext4 / plaso_z | 96 | 0 | 0 | 0 | 0 | 24 | 100.0 |
| ext4 / tsk_fls | 96 | 0 | 0 | 0 | 0 | 24 | 100.0 |
| ext4 / tsk_fls_z | 96 | 0 | 0 | 0 | 0 | 24 | 100.0 |
| ext4 / tsk_mactime_z | 96 | 0 | 0 | 0 | 0 | 24 | 100.0 |
| fat32 / plaso | 0 | 0 | 0 | 52 | 0 | 68 | 0.0 |
| fat32 / plaso_z | 0 | 0 | 0 | 52 | 0 | 68 | 0.0 |
| fat32 / tsk_fls | 13 | 26 | 13 | 0 | 0 | 68 | 25.0 |
| fat32 / tsk_fls_z | 39 | 0 | 13 | 0 | 0 | 68 | 75.0 |
| fat32 / tsk_mactime_z | 39 | 0 | 13 | 0 | 0 | 68 | 75.0 |
| ntfs / analyzemft | 108 | 0 | 0 | 0 | 0 | 12 | 100.0 |
| ntfs / plaso | 108 | 0 | 0 | 0 | 0 | 12 | 100.0 |
| ntfs / plaso_z | 108 | 0 | 0 | 0 | 0 | 12 | 100.0 |
| ntfs / tsk_fls | 108 | 0 | 0 | 0 | 0 | 12 | 100.0 |
| ntfs / tsk_fls_z | 108 | 0 | 0 | 0 | 0 | 12 | 100.0 |
| ntfs / tsk_mactime_z | 81 | 0 | 27 | 0 | 0 | 12 | 75.0 |

*Not on disk: no source (the driver's own stat, or any tool) shows the time; it was never stored or a later action overwrote it. Not counted against tools.
