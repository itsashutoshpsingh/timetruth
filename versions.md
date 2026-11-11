# Versions

Every number in this repository was produced with exactly these versions. A result
without its tool version is not a result. Re-run `./run_all.sh` after any upgrade.

## Platform

| Item | Version |
|---|---|
| OS | Ubuntu 24.04.5 LTS (x86_64), in a cloud VM |
| Kernel | 6.18.44 |
| glibc (`mktime`, used by TSK for FAT/exFAT) | 2.39-0ubuntu8.9 |
| tzdata | 2026e-0ubuntu0.24.04.1 |
| Python (harness) | 3.13.18 |

## Writers (what put the timestamps on disk)

| File system | Writer | Version | Clock |
|---|---|---|---|
| NTFS | ntfs-3g (FUSE), `mkntfs` | 2022.10.3 (Ubuntu 1:2022.10.3-1.2ubuntu3.2) | libfaketime |
| exFAT | fuse-exfat (`mount.exfat-fuse`), `mkfs.exfat` from exfatprogs | 1.4.0 (libfuse3); exfatprogs 1.2.2 | libfaketime |
| FAT32 | GNU mtools (`mcopy`, `mren`, `mmove`, `mdel`, `mmd`), `mkfs.vfat` (dosfstools) | 4.0.43; dosfstools 4.2 | libfaketime |
| ext4 | Linux kernel driver, `mke2fs` | 6.18.44; e2fsprogs 1.47.0 | real clock (the kernel ignores libfaketime) |
| Fake clock | libfaketime, `FAKETIME=±Ns` constant offset, `NO_FAKE_STAT=1` | 0.9.10-2.1 | |

## Tools under test

| Tool | Version | Notes |
|---|---|---|
| The Sleuth Kit (`fls`, `mactime`, `icat`, `istat`) | 4.12.1 (Ubuntu 4.12.1+dfsg-1.1ubuntu2) | |
| Plaso (`log2timeline`, `psort`) | 20261027 (PyPI wheel) | in its own venv, `/opt/plaso-venv` |
| dfVFS | 20260924 | Plaso's file-system layer |
| dfDateTime | 20261027 | |
| libfsfat-python | 20260826 | dfVFS's FAT/exFAT back-end; month error also in 20240501 and 20260208 |
| libfsntfs-python | 20260827 | |
| libfsext-python | 20260821 | |
| pytsk3 | 20260715 | |
| analyzeMFT | 3.1.1 (PyPI) | independent `$MFT` parser, stands in for MFTECmd on Linux |

## Tools that could not be run here

| Tool | Version tried | What happened |
|---|---|---|
| MFTECmd | 2026.10.6 (`download.ericzimmermanstools.com/MFTECmd.zip`, SHA-256 `cf5892102c75df6000e87aec5653046f453f65846f361ee48ed1ab2771b0f1e3`) | The release build targets .NET Framework 4.7.2. Under Mono 6.8.0.105 it starts, prints its version, then reports every input as "not found": its AlphaFS file layer calls Windows APIs. Building the net10.0 target from source was not possible in this environment. It is covered by the Windows 11 kit (`docs/windows-kit.md`). |
| EvtxECmd, PECmd | not tried | Windows artefacts; Windows 11 kit only. |
| Plaso Docker image | `log2timeline/plaso:latest` | Docker Hub returned HTTP 429 (rate limit), so the PyPI wheel was used. |

## Harness libraries

See `requirements.txt` (pandas 3.1.1, matplotlib 3.11.2, numpy 2.5.4, pytest 9.2.0, analyzeMFT 3.1.1).

## Source revisions read for root-cause analysis

| Project | Commit | Date |
|---|---|---|
| libyal/libfsfat | `7bf92e028617049e57fbe752b8019fd453d509ad` | 2026-11-09 |
| sleuthkit/sleuthkit | `08167c8d6d5fc1bd4ee6d822e2fe042cabcdee6d` | 2026-11-10 |
