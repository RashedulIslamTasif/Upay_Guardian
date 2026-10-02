#!/usr/bin/env bash
set -e
echo "=========================================================="
echo " [Guardian] Running Benchmark & Business Impact Suite "
echo "=========================================================="
export PYTHONPATH=.
python -m src.guardian.eval.evaluate --data_dir data --artifacts_dir models_artifacts --output_json data/eval_results.json