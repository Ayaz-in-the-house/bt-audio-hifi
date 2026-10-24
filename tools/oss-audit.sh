#!/usr/bin/env bash
# C5.3 — açık kaynak sızıntı kapısı. "Gönderilen" küme (kod + araç + config şablonu + skill + README) içinde kişisel
# veri OLMAMALI: Bluetooth MAC, ev dizini yolu, makine adı, e-posta, Tailscale/özel IP. docs/ (bu kurulumun laboratuvar
# defteri), state/, analysis/ ve tests/fixtures (gerçek ölçüm örnekleri) KAPSAM DIŞI — paylaşım paketine girmez.
# Çıkış: 0 temiz · 1 bulgu var.
set -uo pipefail
cd "$(dirname "$0")/.."
SHIP=(btaudio bin tools config config-optional skill README.md)
host=$(hostname -s 2>/dev/null || echo __nohost__)
pat="([0-9A-F]{2}[:_]){5}[0-9A-F]{2}|/home/[a-z_][a-z0-9_-]*|${host}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
hits=$(git ls-files -- "${SHIP[@]}" | grep -v -E '^tools/oss-audit\.sh$' | xargs grep -nIE "$pat" 2>/dev/null \
       | grep -vE 'noreply@anthropic\.com|user@example\.com|02:00:00:00:00:01')
if [ -n "$hits" ]; then
  echo "OSS-AUDIT: KİŞİSEL VERİ BULUNDU ($(echo "$hits" | wc -l) satır):"
  echo "$hits" | sed 's/^/  /'
  exit 1
fi
echo "OSS-AUDIT: temiz ($(git ls-files -- "${SHIP[@]}" | wc -l) dosya tarandı)"
