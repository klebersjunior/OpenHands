#!/bin/sh
# Wrapper around budtmo/docker-android run.sh.
#
# After the first successful start, change_permission() runs:
#   sudo chown 1300:1301 /dev/kvm
#   sudo sed -i '1d' /etc/passwd
# The sed deletes the root passwd line, so the next container start fails with
# "sudo: unknown user root" and the Android emulator never comes back.
# noVNC stays up (empty X desktop) — the Emulator tab then looks "dead".

set -eu

restore_root_passwd() {
  if ! grep -q '^root:' /etc/passwd 2>/dev/null; then
    printf 'root:x:0:0:root:/root:/bin/bash\n' > /tmp/passwd.heimdall
    cat /etc/passwd >> /tmp/passwd.heimdall
    cat /tmp/passwd.heimdall > /etc/passwd
    rm -f /tmp/passwd.heimdall
  fi
}

install_sudo_guard() {
  if [ ! -x /usr/bin/sudo ]; then
    return 0
  fi
  if [ -x /usr/bin/sudo.budtmo ]; then
    return 0
  fi
  mv /usr/bin/sudo /usr/bin/sudo.budtmo
  if [ -f /opt/heimdall/sudo-guard.sh ]; then
    cp /opt/heimdall/sudo-guard.sh /usr/bin/sudo
  else
    printf '%s\n' '#!/bin/sh' 'exit 0' > /usr/bin/sudo
  fi
  chmod 755 /usr/bin/sudo
}

restore_root_passwd
install_sudo_guard

if [ -e /dev/kvm ]; then
  chown 1300:1301 /dev/kvm 2>/dev/null || chmod 666 /dev/kvm 2>/dev/null || true
fi

if [ "$(id -u)" = "0" ]; then
  exec su -s /bin/sh androidusr -c \
    'exec /home/androidusr/docker-android/mixins/scripts/run.sh'
fi

exec /home/androidusr/docker-android/mixins/scripts/run.sh
