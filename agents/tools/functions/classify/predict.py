from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


MODEL_DIR = Path(__file__).resolve().parents[4] / "training" / "models"
MODEL_FILES = {
	"excel": "excel_top10_random_forest.joblib",
	"html": "html_top13_random_forest.joblib",
	"pdf": "pdf_top10_random_forest.joblib",
	"word": "word_top10_random_forest.joblib",
}
FILE_TYPE_ALIASES = {
	"xls": "excel",
	"xlsx": "excel",
	"htm": "html",
	"doc": "word",
	"docx": "word",
}
_MODEL_CACHE: dict[str, dict[str, Any]] = {}


def classify_precomputed_features(
	file_type: str,
	features: dict[str, float],
) -> dict[str, Any]:
	"""Score one complete, pre-extracted feature vector with a local model."""
	model_type = file_type.strip().lower().lstrip(".")
	model_type = FILE_TYPE_ALIASES.get(model_type, model_type)
	if model_type not in MODEL_FILES:
		return {
			"status": "unsupported_file_type",
			"supported_types": sorted(MODEL_FILES),
			"message": "No trained classifier is available for this file type.",
		}

	model_path = MODEL_DIR / MODEL_FILES[model_type]
	if not model_path.is_file():
		return {
			"status": "model_unavailable",
			"file_type": model_type,
			"message": "The model artifact is not present in training/models.",
		}

	artifact = _MODEL_CACHE.get(model_type)
	if artifact is None:
		artifact = joblib.load(model_path)
		_MODEL_CACHE[model_type] = artifact

	feature_columns = artifact.get("feature_columns")
	if not isinstance(feature_columns, list) or not feature_columns:
		return {
			"status": "invalid_model_artifact",
			"file_type": model_type,
			"message": "The saved model does not contain a valid feature schema.",
		}

	missing_features = [name for name in feature_columns if name not in features]
	extra_features = [name for name in features if name not in feature_columns]
	if missing_features or extra_features:
		return {
			"status": "invalid_features",
			"file_type": model_type,
			"required_features": feature_columns,
			"missing_features": missing_features,
			"unexpected_features": extra_features,
			"message": "Provide exactly the trained feature names and values.",
		}

	values: dict[str, float] = {}
	for name in feature_columns:
		value = features[name]
		if isinstance(value, bool):
			return {
				"status": "invalid_features",
				"file_type": model_type,
				"feature": name,
				"message": "Feature values must be finite numbers, not booleans.",
			}
		try:
			numeric_value = float(value)
		except (TypeError, ValueError):
			return {
				"status": "invalid_features",
				"file_type": model_type,
				"feature": name,
				"message": "Feature values must be finite numbers.",
			}
		if not math.isfinite(numeric_value):
			return {
				"status": "invalid_features",
				"file_type": model_type,
				"feature": name,
				"message": "Feature values must be finite numbers.",
			}
		values[name] = numeric_value

	model_input = pd.DataFrame([values], columns=feature_columns)
	model = artifact["model"]
	predicted_class = int(model.predict(model_input)[0])
	class_labels = [int(value) for value in model.classes_]
	malicious_index = class_labels.index(1)
	malicious_score = float(model.predict_proba(model_input)[0][malicious_index])
	label_mapping = artifact.get("label_mapping", {0: "benign", 1: "malicious"})

	return {
		"status": "ok",
		"file_type": model_type,
		"predicted_label": label_mapping.get(predicted_class, str(predicted_class)),
		"malicious_score": malicious_score,
		"score_note": "Model score is not calibrated as a probability.",
		"warning": (
			"Experimental model trained on preselected features. This result is "
			"not an independent security verdict."
		),
	}