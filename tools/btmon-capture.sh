#!/usr/bin/env bash
# F6.2 — Radyo katmanı ölçümü (ROOT gerekir → KULLANICI çalıştırır; ajan sudo şifresi kullanmaz).
#   Kullanım (müzik çalarken):  sudo bash ~/projects/bt-audio-hifi/tools/btmon-capture.sh 60
#   Beklenen çıktı: iki dosya yolu (.btsnoop + .rssi.txt). Sonra: ~/projects/bt-audio-hifi/bin/bta btmon-report <btsnoop>
set -euo pipefail
dur="${1:-60}"
[ "$(id -u)" -eq 0 ] || { echo "sudo ile çalıştır: sudo bash $0 $dur" >&2; exit 1; }
owner="${SUDO_USER:-root}"
repo="$(cd "$(dirname "$0")/.." && pwd)"; dir="$repo/analysis/link-health"; mkdir -p "$dir"
# cihaz: $BTA_DEVICE → kullanıcının en son görülen cihazı (bta yazar) → bağlı ilk ses cihazı (A2DP Sink UUID)
owner_home="$(getent passwd "$owner" | cut -d: -f6)"
mac="${BTA_DEVICE:-$(cat "$owner_home/.config/bt-audio-hifi/device" 2>/dev/null || true)}"
if [ -z "$mac" ]; then
  for d in $(bluetoothctl devices Connected | awk '{print $2}'); do
    bluetoothctl info "$d" | grep -q "0000110b-0000-1000-8000-00805f9b34fb" && { mac="$d"; break; }
  done
fi
[ -n "$mac" ] || { echo "bağlı Bluetooth kulaklık bulunamadı (BTA_DEVICE=<MAC> ver)" >&2; exit 1; }
base="$dir/btmon-$(date +%Y%m%d-%H%M%S)"
timeout "$dur" btmon -w "$base.btsnoop" >/dev/null 2>&1 &
end=$(( $(date +%s) + dur ))
while [ "$(date +%s)" -lt "$end" ]; do
  printf '%s ' "$(date +%T)"; btmgmt conn-info -t 0 "$mac" 2>&1 | tr '\n' ' '; echo
  sleep 2
done > "$base.rssi.txt"
wait || true
chown "$owner": "$base.btsnoop" "$base.rssi.txt"
echo "$base.btsnoop"; echo "$base.rssi.txt"
