# Attachment Model Training

Place the downloaded attachment feature CSVs in `training/data/`:

- `Word_All_Features.csv` and `Word_Top10_Features.csv`
- `Excel_All_Features.csv` and `Excel_Top10_Features.csv`
- `PDF_All_Features.csv` and `PDF_Top10_Features.csv`
- `HTML_All_Features.csv` and `HTML_Top13_Features.csv`

The CSVs are training data, not trained models. Use `label` as the target
(0 = benign, 1 = malicious) and exclude the filename column from model inputs.
Compare the `All_Features` and `Top` variants with the same stratified
train/test split. Perform any new feature selection using only the training
split to avoid leakage.

The first baseline trains the Excel Top10 dataset:

```powershell
.\.venv\Scripts\python.exe training\train_excel_top10.py
```

It writes the fitted classifier to `training/models/` and the held-out test
metrics to `training/reports/`. The supplied Top10 feature selection was
performed before this workspace's train/test split; its selection provenance
is unknown, so treat the reported score as a baseline rather than a fully
leakage-controlled result.

To measure Excel Top10 performance across grouped folds, run:

```powershell
.\.venv\Scripts\python.exe training\cross_validate_excel_top10.py
```

This keeps identical feature vectors in the same fold and writes a separate
out-of-fold report to `training/reports/`.

Keep training code in this folder, save generated model files under
`training/models/`, and put evaluation metrics under `training/reports/`.
These models are not connected to the chat agent. Qdrant RAG remains the
separate retrieval and explanation layer.

Add the licensed files here before training. Generated `.joblib`, `.pkl`, and
`.pickle` model files are ignored by Git.
