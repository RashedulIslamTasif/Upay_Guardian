#!/usr/bin/env bash
set -e
echo "=========================================================="
echo " [Guardian] Executing Model Training Pipeline "
echo "=========================================================="
export PYTHONPATH=.
python -m src.guardian.models.train --data_dir data --artifacts_dir models_artifacts