#!/bin/bash
# Keçdim saytına Google Analytics 4 qoşur — tək əmr.
#   ./ga-qos.sh G-XXXXXXXXXX     → qoşur
#   ./ga-qos.sh off              → söndürür və bütün tagları silir
set -e
cd "$(dirname "$0")"
ID="${1:-}"
if [ -z "$ID" ]; then echo "İstifadə: ./ga-qos.sh G-XXXXXXXXXX   |   ./ga-qos.sh off"; exit 1; fi
if [ "$ID" = "off" ]; then ID=""; MSG="GA söndürüldü";
elif [[ ! "$ID" =~ ^G-[A-Z0-9]{6,12}$ ]]; then
  echo "🔴 «$ID» GA4 ölçmə ID-sinə oxşamır (G- ilə başlamalı). Dayandırıldı."; exit 1
else MSG="GA qoşuldu: $ID"; fi

python3 - "$ID" <<'PY'
import re, sys
p = "build.py"; s = open(p).read()
s = re.sub(r'^GA_ID = ".*"', f'GA_ID = "{sys.argv[1]}"', s, count=1, flags=re.M)
open(p, "w").write(s)
PY
python3 build.py

if [ -n "$ID" ]; then
  n=$(grep -l "$ID" ./*.html | wc -l | tr -d ' ')
  t=$(ls ./*.html | wc -l | tr -d ' ')
  echo "   tag: $n/$t səhifə"
  [ "$n" = "$t" ] || { echo "🔴 bəzi səhifələrdə tag yoxdur — deploy dayandırıldı"; exit 1; }
else
  grep -l googletagmanager ./*.html >/dev/null 2>&1 && { echo "🔴 qalıq tag var"; exit 1; }
  echo "   bütün taglar silindi"
fi

git add -A
git -c user.email=turanmammad@gmail.com -c user.name="Turan Mammad" commit -q -m "$MSG"
git push -q origin main
echo "✓ $MSG — GitHub Pages 30-90 saniyəyə yeniləyir"
echo "  Yoxla: curl -s https://kecdim.pro-tech.az/ | grep -o 'G-[A-Z0-9]*'"
