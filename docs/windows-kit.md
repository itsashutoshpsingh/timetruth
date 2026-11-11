# Windows 11 kit (to be run on your own machine)

The Linux runs in this repository cover how file systems store time and how three
tools read it. They cannot cover Windows itself: how the Windows NTFS driver
updates `$STANDARD_INFORMATION` versus `$FILE_NAME`, the event log, Prefetch, or
the registry. This kit repeats the same 30 actions on a Windows 11 VM so the same
`compare/diff.py` can score MFTECmd, EvtxECmd and PECmd as well.

Nothing in this folder has been run on Windows yet. Results from it will be added
as separate rows (`fs=ntfs_win11`) and will not replace the Linux results.

## 1. Build the VM (once)

1. Download the Windows 11 Enterprise evaluation VM from Microsoft and read its licence terms.
2. Import it into VirtualBox or Hyper-V. Add a second virtual disk (1 GB) and format it
   in the VM as NTFS, drive letter `E:`. For the exFAT and FAT32 runs, add one disk each.
3. Turn off Windows Update and time sync with the host for the run window:
   `w32tm /config /syncfromflags:NO /update` (record that you did this).
4. Record `winver` build, VirtualBox version and the host OS in `versions.md`.
5. Take a snapshot named `clean`.

## 2. One run (repeat per zone)

```powershell
tzutil /s "UTC"                     # then "India Standard Time", "GMT Standard Time", "Eastern Standard Time"
powershell -ExecutionPolicy Bypass -File run_actions.ps1 -Root E:\ -Out C:\truth -Spacing 12
```

For the DST runs, set the VM clock to three minutes before the change before running
(`Set-Date "2026-10-25 01:57:07"` in GMT Standard Time, which is still BST at that
moment), with host time sync off. Log the host's real UTC time when you start.

Shut the VM down (do not just suspend), then image the `E:` disk from the host with
FTK Imager (raw `.dd`, verify the hash), or use the VM's `.vdi` after
`VBoxManage clonemedium --format RAW`.

Copy `C:\truth\truth.csv` out to `truth/ntfs_win11_<zone>/truth.csv` and write a
`run.env` with `FS=ntfs`, `SCENARIO=<zone>`, `ZONE=<IANA zone>`, `IMAGE=<path>`.

## 3. Analyse

On a Windows analysis host (MFTECmd and the other Zimmerman tools are .NET and run on Windows):

```powershell
MFTECmd.exe -f E:\$MFT --csv out --csvf mftecmd.csv      # or point -f at the image's extracted $MFT
EvtxECmd.exe -d C:\Windows\System32\winevt\Logs --csv out --csvf evtx.csv   # from the VM image's system disk
PECmd.exe -d C:\Windows\Prefetch --csv out --csvf pecmd.csv
```

Back in this repository:

```bash
python parse/mft_to_common.py mftecmd mftecmd.csv results/events/ntfs_win11_utc/mftecmd.csv --tool mftecmd
build/run_tools.sh ntfs_win11_utc     # TSK and Plaso on the same image
python compare/diff.py
```

`parse/mft_to_common.py mftecmd` is tested only against a hand-written fixture in
MFTECmd's documented column layout (`tests/fixtures/sample_mftecmd.csv`). Check it
against real output on the first run and fix it if a column differs.

## What this kit adds that Linux could not

| Question | Linux runs | Windows kit |
|---|---|---|
| Does the Windows driver leave `$FN` untouched when `$SI` is back-dated (`SetFileTime`)? | No: ntfs-3g rewrites both (see `docs/what-went-wrong.md`) | Yes |
| Program execution time (Prefetch, PECmd) | No | Yes |
| Event log times (EvtxECmd) | No | Yes |
| MFTECmd itself | No (does not run on Linux, see `versions.md`) | Yes |
