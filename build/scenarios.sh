# Writer time zone and (faked) start instant for each scenario.
# Starts sit at :07 s so no action lands on a whole half hour (FAT access
# times are date-only, i.e. midnight). 30 actions x 12 s = ~6 minutes, so the
# DST scenarios start 3 minutes before
# the clock change and cross it.
scenario() {
  case $1 in
    utc)         ZONE=UTC;              START=2026-11-02T10:00:07Z ;;
    kolkata)     ZONE=Asia/Kolkata;     START=2026-11-02T10:00:07Z ;;  # +05:30, no DST
    london_fall) ZONE=Europe/London;    START=2026-10-25T00:57:07Z ;;  # 02:00 BST -> 01:00 GMT
    ny_spring)   ZONE=America/New_York; START=2026-03-08T06:57:07Z ;;  # 02:00 EST -> 03:00 EDT
    *) echo "unknown scenario $1" >&2; return 2 ;;
  esac
  # ext4 is stamped by the kernel clock, which libfaketime cannot move.
  if [ "${FS:-}" = ext4 ]; then START=now; fi
}
SCENARIOS="utc kolkata london_fall ny_spring"
FILESYSTEMS="ntfs exfat fat32 ext4"
