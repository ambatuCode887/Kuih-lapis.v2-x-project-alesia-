from __future__ import annotations

import json
from pathlib import Path

import joblib
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
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


TRAINING_DIR = Path(__file__).resolve().parent
DATA_PATH = TRAINING_DIR / "data" / "PDF_Top10_features.csv"
MODEL_PATH = TRAINING_DIR / "models" / "pdf_top10_random_forest.joblib"
REPORT_PATH = TRAINING_DIR / "reports" / "pdf_top10_metrics.json"
RANDOM_STATE = 42
TEST_SIZE = 0.3


def main() -> None:
	if not DATA_PATH.exists():
		raise FileNotFoundError(f"Training dataset not found: {DATA_PATH}")

	data = pd.read_csv(DATA_PATH)
	if "label" not in data.columns:
		raise ValueError("Dataset is missing the required 'label' column.")

	labels = pd.to_numeric(data["label"], errors="coerce")
	if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
		raise ValueError("The label column must contain only 0 (benign) and 1 (malicious).")

	feature_columns = [column for column in data.columns if column != "label"]
	if not feature_columns:
		raise ValueError("Dataset contains no feature columns.")

	features = data[feature_columns].apply(pd.to_numeric, errors="coerce")
	if features.isna().all(axis=None):
		raise ValueError("All feature values are missing or non-numeric.")

	feature_groups = features.groupby(
		feature_columns,
		sort=False,
		dropna=False,
	).ngroup()
	grouped_labels = pd.DataFrame(
		{"feature_group": feature_groups, "label": labels.astype(int)}
	).groupby("feature_group", sort=False)["label"]
	if grouped_labels.nunique().gt(1).any():
		raise ValueError("Identical feature vectors have conflicting labels.")
	group_labels = grouped_labels.first()

	train_groups, test_groups = train_test_split(
		group_labels.index.to_numpy(),
		test_size=TEST_SIZE,
		random_state=RANDOM_STATE,
		stratify=group_labels.to_numpy(),
	)
	train_mask = feature_groups.isin(train_groups)
	test_mask = feature_groups.isin(test_groups)
	X_train, X_test = features.loc[train_mask], features.loc[test_mask]
	y_train, y_test = labels.loc[train_mask].astype(int), labels.loc[test_mask].astype(int)

	model = Pipeline(
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
	model.fit(X_train, y_train)

	predictions = model.predict(X_test)
	probabilities = model.predict_proba(X_test)[:, 1]
	matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
	metrics = {
		"dataset": DATA_PATH.name,
		"rows": int(len(data)),
		"features": feature_columns,
		"target": "label (0=benign, 1=malicious)",
		"random_state": RANDOM_STATE,
		"test_size": TEST_SIZE,
		"actual_test_fraction": float(len(X_test) / len(data)),
		"train_rows": int(len(X_train)),
		"test_rows": int(len(X_test)),
		"unique_feature_groups": int(len(group_labels)),
		"duplicate_feature_rows": int(len(data) - len(group_labels)),
		"train_groups": int(len(train_groups)),
		"test_groups": int(len(test_groups)),
		"class_counts": {
			str(label): int(count)
			for label, count in labels.astype(int).value_counts().sort_index().items()
		},
		"accuracy": float(accuracy_score(y_test, predictions)),
		"balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
		"roc_auc": float(roc_auc_score(y_test, probabilities)),
		"confusion_matrix_labels_0_1": matrix.tolist(),
		"classification_report": classification_report(
			y_test,
			predictions,
			labels=[0, 1],
			target_names=["benign", "malicious"],
			output_dict=True,
			zero_division=0,
		),
		"feature_selection_note": (
			"Top10 features were supplied preselected; whether selection used "
			"only an independent training split is unknown."
		),
		"split_note": (
			"Rows with identical feature vectors were kept in the same split "
			"group to prevent duplicate-vector leakage."
		),
	}

	MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
	REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(
		{
			"model": model,
			"feature_columns": feature_columns,
			"label_mapping": {0: "benign", 1: "malicious"},
		},
		MODEL_PATH,
	)
	REPORT_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

	print(f"Dataset: {DATA_PATH.name}")
	print(
		f"Rows: {len(data)} (train={len(X_train)}, test={len(X_test)}, "
		f"test fraction={metrics['actual_test_fraction']:.3f})"
	)
	print(f"Unique feature groups: {len(group_labels)}")
	print(f"Accuracy: {metrics['accuracy']:.4f}")
	print(f"Balanced accuracy: {metrics['balanced_accuracy']:.4f}")
	print(f"ROC AUC: {metrics['roc_auc']:.4f}")
	print("Confusion matrix (rows=true, columns=predicted; labels 0, 1):")
	print(matrix)
	print(f"Saved model: {MODEL_PATH}")
	print(f"Saved metrics: {REPORT_PATH}")


if __name__ == "__main__":
	main()
