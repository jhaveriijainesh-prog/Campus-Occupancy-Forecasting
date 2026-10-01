"""Generate model-native feature importance and point-error slice artifacts."""

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.analytics.explainability import generate_explainability_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        default="experiments/xgboost/feature_metadata.json",
        help="XGBoost feature metadata JSON",
    )
    parser.add_argument(
        "--xgboost-predictions",
        default="experiments/xgboost/test_predictions.csv",
        help="XGBoost point predictions CSV",
    )
    parser.add_argument(
        "--baseline-predictions",
        default="experiments/baseline/test_predictions.csv",
        help="Historical seasonal baseline predictions CSV",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/comparison/explainability",
        help="Directory for generated artifacts",
    )
    args = parser.parse_args()
    paths = generate_explainability_artifacts(
        model_metadata_path=args.metadata,
        xgboost_predictions_path=args.xgboost_predictions,
        baseline_predictions_path=args.baseline_predictions,
        output_dir=args.output_dir,
    )
    print(json.dumps(paths, indent=2))


if __name__ == "__main__":
    main()