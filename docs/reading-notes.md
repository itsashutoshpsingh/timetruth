# Reading notes

## 1. Hargreaves, Nelson and Casey (NIST), "An abstract model for digital forensic analysis tools: a foundation for systematic error mitigation analysis", DFRWS EU 2024 (FSI: Digital Investigation)

- Sources: https://www.nist.gov/publications/abstract-model-digital-forensic-tools-foundation-systematic-error-mitigation-analysis,
  https://www.sciencedirect.com/science/article/pii/S2666281723001981
- Builds on ASTM E3016-18, which says most tool errors are *systematic*, not
  statistical, and names three kinds: **incompleteness** (INCOMP: something is there
  and the tool does not show it), **misinterpretation** (MISINT: shown, but its meaning
  is presented wrongly) and **inaccuracy** (INAC: the value is wrong).
- Breaks a tool into stages (read the image, parse the volume and file system,
  identify files, extract artefacts, present). An error at an early stage propagates,
  and two tools agreeing proves little if they share a library ("the same incorrect
  knowledge, assumptions or even code libraries").
- Argues tools should expose intermediate output so errors can be isolated.
- **What I take from it:** my outcomes map onto E3016's classes. *missing* = INCOMP.
  *wrong value* = INAC. *wrong zone* and *ambiguous* are MISINT, because the stored
  value is fine but its zone meaning is lost on the way to the examiner. The
  shared-library warning is exactly the Plaso case: Plaso and anything else built on
  libfsfat will agree with each other and both be a month wrong. Differential testing
  only works if the tools are independent at the parsing stage, so I record which
  library each tool uses (`versions.md`).

## 2. Studiawan, Breitinger et al., "Towards a standardized methodology and dataset for evaluating LLM-based digital forensic timeline analysis", DFRWS APAC 2025

- Sources: https://www.sciencedirect.com/science/article/pii/S2666281725001222, arXiv 2505.03100
- Built Windows 11 timelines with Plaso (Docker 20230717) from a VM, with scripted
  ground truth, and published them on Zenodo. The purpose is to score language
  models answering questions about a timeline, not to test Plaso.
- They take Plaso's output as correct and score the model against it.
- **What I take from it:** this is the closest existing work, and it is the reverse of
  this project. It trusts the timeline tool; here the tool is the thing under test. Their
  scripted-actions-on-a-VM method is the same as my Windows kit. I did not find a
  dataset that scores timeline tools' time and zone handling against ground truth.
  That is a statement about what I found in a short search, not a claim that none exists.

## 3. Forensic Science Regulator, Code of Practice, version 2 (statutory; in force 2 October 2025)

- Source: https://assets.publishing.service.gov.uk/media/68401f4be550203c8209cce9/2025_05_20_Code_of_Practice_final.pdf, section 24
- 24.1.2: validation is "providing objective evidence that a method or procedure is
  fit for the specific purpose intended", including that "the limitations of the method
  are properly understood".
- 24.2.3: "Even where a method is considered standard and is in widespread use,
  scientific validity still needs to be demonstrated."
- 24.2.6: external developers or testers of tools are encouraged to validate "in a
  comparable manner" and to make "the SOP and data available".
- 24.3.4: if acceptance criteria are not met, the method "is declared to have failed
  validation", not quietly fixed during validation.
- 24.6.1(b): the risk assessment must identify where interpretation "requires
  specialist skills or knowledge to prevent ambiguous or misleading outputs".
- 24.9.8(e)-(f): results must be "consistent, reliable, accurate and robust", and
  compatible with "results obtained by other practitioners using different equipment
  and different methods".
- 24.9.18: "minor modifications, including software and firmware, might affect the
  operation". In other words, a tool upgrade needs re-verification.
- 24.12.2(c), (j): the validation report names "version number" of everything used and
  "any limitations/constraints".
- 24.2.5 and 24.2.12(e): the validation status has to be disclosed in reports.
- **What I take from it:** a timeline tool is a method component, and "it's Plaso" or
  "it's TSK" is not validation. This repository gives a forensic unit reusable
  objective evidence (24.2.6), with the SOP (`run_all.sh`), the data (`truth/`,
  `results/`) and pinned versions (`versions.md`). Mapping in `docs/fsr-code-mapping.md`.

## 4. Tool documentation on time zones (read for the pinned versions)

**Plaso 20261027** (`log2timeline --help`, `psort --help`):
- `log2timeline -z/--timezone`: "preferred time zone of extracted date and time values
  that are stored without a time zone indicator. The time zone is determined based on
  the source data where possible otherwise it will default to UTC."
- `psort --output_time_zone`: only for output formats that support it (`dynamic`, ...).
  `json_line` carries `timestamp` in microseconds UTC.
- So for FAT (local time, no indicator) Plaso's documented default is UTC unless told
  otherwise. In these runs the month error hides that, because every FAT/exFAT value
  is off by weeks before any zone is applied.

**The Sleuth Kit 4.12.1** (`fls(1)`, `mactime(1)`):
- `fls -z zone`: "The ASCII string of the time zone of the original system. For example,
  EST or GMT." Body-file times are epoch seconds.
- `mactime -z`: zone used to *display* times. `-d` prints comma-separated output whose
  date column has no zone or offset (`Sun Oct 25 2026 01:58:00`). `-y` prints ISO 8601
  with a `Z`, but only in UTC.
- Neither page says which file systems `-z` affects. Reading the source: only FAT and
  exFAT (via `mktime`); NTFS and ext4 store UTC and ignore it.

**Eric Zimmerman's MFTECmd** (README and `--help`): all times are written in UTC, with
separate columns for `$STANDARD_INFORMATION` (0x10) and `$FILE_NAME` (0x30). There is
no zone option. It does not run on Linux (see `versions.md`); it is covered by the
Windows kit.

**analyzeMFT 3.1.1** (`--help`, output): ISO 8601 UTC with millisecond precision, `$SI`
and `$FN` columns. Its `Filepath` column comes out empty, so the converter rebuilds
paths from parent record numbers.

## 5. Also read

- Lee et al., "SoK: Timeline based event reconstruction for digital forensics", DFRWS EU 2025.
  It lists "different timestamp formats, timestamp resolutions, and timezone settings"
  as a core normalisation challenge, and "initial changes may disappear due to
  subsequent events". The second point is why this harness has a separate
  *not on disk* outcome, kept apart from tool errors.
- forensics.wiki "FAT" page: the FAT date layout (bits 0-4 day, 5-8 month with 1 =
  January, 9-15 years since 1980), used to decode raw directory entries independently of
  any tool.
