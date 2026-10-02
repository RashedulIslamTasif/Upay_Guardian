#!/usr/bin/env bash
set -e
echo "=========================================================="
echo " [Guardian] Generating Synthetic Datasets for upay "
echo "=========================================================="
export PYTHONPATH=.
python -m src.guardian.datagen.generate --users 5000 --agents 300 --txns 150000 --texts 6000 --seed 42 --output_dir data