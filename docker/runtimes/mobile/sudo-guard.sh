#!/bin/sh
# Installed over /usr/bin/sudo by emulator-entrypoint.sh.
# budtmo calls: sudo chown 1300:1301 /dev/kvm
#               sudo sed -i '1d' /etc/passwd
for arg in "$@"; do
  case "$arg" in
    *"/etc/passwd"*) exit 0 ;;
  esac
done
if [ "$1" = "chown" ]; then
  exit 0
fi
exec /usr/bin/sudo.budtmo "$@"
