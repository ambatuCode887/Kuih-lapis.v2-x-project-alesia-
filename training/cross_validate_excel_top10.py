from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
	accuracy_score,
	balanced_accuracy_score,
	classification_report,
	confusion_matrix,
	roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline


TRAINING_DIR = Path(__file__).resolve().parent
DATA_PATH = TRAINING_DIR / "data" / "Excel_Top10_Features.csv"
REPORT_PATH = TRAINING_DIR / "reports" / "excel_top10_cross_validation.json"
RANDOM_STATE = 42
N_SPLITS = 5


def make_model() -> Pipeline:
	return Pipeline(
		steps=[
			("imputer", SimpleImputer(strategy="median")),
			(
				"classifier",
				RandomForestClassifier(
					n_estimators=300,
					class_weight="balanced",
					random_state=RANDOM_STATE,
					n_jobs=-1,
				),
			),
		]
	)


def main() -> None:
	if not DATA_PATH.exists():
		raise FileNotFoundError(f"Training dataset not found: {DATA_PATH}")

	data = pd.read_csv(DATA_PATH)
	if "label" not in data.columns:
		raise ValueError("Dataset is missing the required 'label' column.")

	labels = pd.to_numeric(data["label"], errors="coerce")
	if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
		raise ValueError("The label column must contain only 0 (benign) and 1 (malicious).")
	labels = labels.astype(int)

	feature_columns = [column for column in data.columns if column not in {"file_name", "label"}]
	if not feature_columns:
		raise ValueError("Dataset contains no feature columns.")

	features = data[feature_columns].apply(pd.to_numeric, errors="coerce")
	if features.isna().all(axis=None):
		raise ValueError("All feature values are missing or non-numeric.")

	groups = features.groupby(
		feature_columns,
		sort=False,
		dropna=False,
	).ngroup()
	grouped_labels = pd.DataFrame({"group": groups, "label": labels}).groupby("group")["label"]
	if grouped_labels.nunique().gt(1).any():
		raise ValueError("Identical feature vectors have conflicting labels.")

	cross_validator = StratifiedGroupKFold(
		n_splits=N_SPLITS,
		shuffle=True,
		random_state=RANDOM_STATE,
	)
	oof_predictions = np.full(len(data), -1, dtype=int)
	oof_probabilities = np.full(len(data), np.nan, dtype=float)
	fold_metrics = []

	for fold, (train_index, test_index) in enumerate(
		cross_validator.split(features, labels, groups),
		start=1,
	):
		model = make_model()
		model.fit(features.iloc[train_index], labels.iloc[train_index])
		predictions = model.predict(features.iloc[test_index])
		probabilities = model.predict_proba(features.iloc[test_index])[:, 1]
		oof_predictions[test_index] = predictions
		oof_probabilities[test_index] = probabilities
		fold_metrics.append(
			{
				"fold": fold,
				"train_rows": int(len(train_index)),
				"test_rows": int(len(test_index)),
				"accuracy": float(accuracy_score(labels.iloc[test_index], predictions)),
				"balanced_accuracy": float(
					balanced_accuracy_score(labels.iloc[test_index], predictions)
				),
				"roc_auc": float(
					roc_auc_score(labels.iloc[test_index], probabilities)
				),
			}
		)

	if (oof_predictions < 0).any() or np.isnan(oof_probabilities).any():
		raise RuntimeError("Cross-validation did not produce one prediction per row.")

	matrix = confusion_matrix(labels, oof_predictions, labels=[0, 1])
	metrics = {
		"dataset": DATA_PATH.name,
		"rows": int(len(data)),
		"features": feature_columns,
		"target": "label (0=benign, 1=malicious)",
		"random_state": RANDOM_STATE,
		"folds": N_SPLITS,
		"unique_feature_groups": int(groups.nunique()),
		"duplicate_feature_rows": int(len(data) - groups.nunique()),
		"class_counts": {
			str(label): int(count)
			for label, count in labels.value_counts().sort_index().items()
		},
		"fold_metrics": fold_metrics,
		"mean_fold_accuracy": float(np.mean([fold["accuracy"] for fold in fold_metrics])),
		"std_fold_accuracy": float(np.std([fold["accuracy"] for fold in fold_metrics])),
		"mean_fold_balanced_accuracy": float(
			np.mean([fold["balanced_accuracy"] for fold in fold_metrics])
		),
		"std_fold_balanced_accuracy": float(
			np.std([fold["balanced_accuracy"] for fold in fold_metrics])
		),
		"pooled_oof_accuracy": float(accuracy_score(labels, oof_predictions)),
		"pooled_oof_balanced_accuracy": float(
			balanced_accuracy_score(labels, oof_predictions)
		),
		"pooled_oof_roc_auc": float(roc_auc_score(labels, oof_probabilities)),
		"pooled_oof_confusion_matrix_labels_0_1": matrix.tolist(),
		"pooled_oof_classification_report": classification_report(
			labels,
			oof_predictions,
			labels=[0, 1],
			target_names=["benign", "malicious"],
			output_dict=True,
			zero_division=0,
		),
		"split_note": (
			"StratifiedGroupKFold keeps identical feature vectors in one fold "
			"to prevent duplicate-vector leakage."
		),
		"feature_selection_note": (
			"Top10 features were supplied preselected. Cross-validation does not "
			"account for possible leakage during their original selection."
		),
	}

	REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
	REPORT_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

	for fold in fold_metrics:
		print(
			f"Fold {fold['fold']}: accuracy={fold['accuracy']:.4f}, "
			f"balanced_accuracy={fold['balanced_accuracy']:.4f}, "
			f"ROC AUC={fold['roc_auc']:.4f}"
		)
	print(f"Mean fold accuracy: {metrics['mean_fold_accuracy']:.4f} ± {metrics['std_fold_accuracy']:.4f}")
	print(
		"Pooled out-of-fold: "
		f"accuracy={metrics['pooled_oof_accuracy']:.4f}, "
		f"balanced_accuracy={metrics['pooled_oof_balanced_accuracy']:.4f}, "
		f"ROC AUC={metrics['pooled_oof_roc_auc']:.4f}"
	)
	print("Pooled confusion matrix (rows=true, columns=predicted; labels 0, 1):")
	print(matrix)
	print(f"Saved cross-validation report: {REPORT_PATH}")


if __name__ == "__main__":
	main()