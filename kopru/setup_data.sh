#!/usr/bin/env bash
# Shiu et al. (2024) model deposunu indirir: FlyWire bağlantı verisi (v630 ve v783),
# yayımlanmış nöron ID'leri ve karşılaştırma için kayıtlı Brian2 çıktıları (~370 MB).
set -euo pipefail
mkdir -p data
if [ -d data/shiu_repo/.git ] || [ -f data/shiu_repo/model.py ]; then
  echo "Veri zaten var: data/shiu_repo"
else
  git clone --depth 1 https://github.com/philshiu/Drosophila_brain_model.git data/shiu_repo
fi
echo "Hazır. Sıradaki adım: python run.py validate"
