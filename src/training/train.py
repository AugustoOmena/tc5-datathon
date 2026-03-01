import os
from datetime import datetime
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score
from imblearn.over_sampling import SMOTE
from feast import FeatureStore
import boto3
import io

# MLflow for experiment tracking (drift monitoring will be based on logged runs)
import mlflow
import mlflow.sklearn

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT", "evasao_experiment"))


def save_model_to_s3(pipeline, model_name):
    bucket_name = "tc5-mlops-artifacts-f4d7a3e1"
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    s3_key = f"models/model_{model_name}_{timestamp}.joblib"
    
    buffer = io.BytesIO()
    joblib.dump(pipeline, buffer)
    buffer.seek(0)
    
    s3_client = boto3.client("s3")
    
    try:
        s3_client.upload_fileobj(buffer, bucket_name, s3_key)
        print(f"Sucesso! Melhor modelo ({model_name}) salvo no S3 em: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"Erro ao salvar no S3: {e}")


model_params = {
    "knn": {
        "model": KNeighborsClassifier(),
        "params": {"n_neighbors": [3, 5, 11], "weights": ["uniform", "distance"]},
    },
    "logistic_regression": {
        "model": LogisticRegression(max_iter=1000, solver="liblinear"),
        "params": {"C": [0.1, 1, 10], "penalty": ["l1", "l2"]},
    },
    "random_forest": {
        "model": RandomForestClassifier(random_state=42),
        "params": {"n_estimators": [100, 200], "max_depth": [None, 10, 20], "min_samples_leaf": [1, 4]},
    },
}


def _calculate_psi(reference_series, current_series, buckets=10):
    ref = pd.to_numeric(reference_series, errors="coerce").dropna().astype(float)
    cur = pd.to_numeric(current_series, errors="coerce").dropna().astype(float)

    if ref.empty or cur.empty:
        return 0.0

    if ref.nunique() == 1 and cur.nunique() == 1 and ref.iloc[0] == cur.iloc[0]:
        return 0.0

    quantiles = np.linspace(0, 1, buckets + 1)
    breakpoints = np.unique(np.quantile(ref, quantiles))

    if len(breakpoints) < 3:
        min_v = min(ref.min(), cur.min())
        max_v = max(ref.max(), cur.max())
        if min_v == max_v:
            return 0.0
        breakpoints = np.linspace(min_v, max_v, buckets + 1)

    ref_counts, _ = np.histogram(ref, bins=breakpoints)
    cur_counts, _ = np.histogram(cur, bins=breakpoints)

    epsilon = 1e-6
    ref_ratio = np.where(ref_counts == 0, epsilon, ref_counts / len(ref))
    cur_ratio = np.where(cur_counts == 0, epsilon, cur_counts / len(cur))

    return float(np.sum((cur_ratio - ref_ratio) * np.log(cur_ratio / ref_ratio)))


def _drift_level(psi_value):
    if psi_value < 0.1:
        return "baixo"
    if psi_value < 0.25:
        return "moderado"
    return "alto"


def log_drift_panel_mlflow(reference_df, current_df, feature_cols):
    valid_features = [f for f in feature_cols if f in reference_df.columns and f in current_df.columns]

    if not valid_features:
        return

    rows = []
    for feature in valid_features:
        ref_col = pd.to_numeric(reference_df[feature], errors="coerce").dropna()
        cur_col = pd.to_numeric(current_df[feature], errors="coerce").dropna()
        if ref_col.empty or cur_col.empty:
            continue

        psi = _calculate_psi(ref_col, cur_col)
        mean_shift = float(abs(cur_col.mean() - ref_col.mean()))

        rows.append({
            "feature": feature,
            "reference_mean": float(ref_col.mean()),
            "current_mean": float(cur_col.mean()),
            "mean_shift_abs": mean_shift,
            "psi": psi,
            "drift_level": _drift_level(psi),
        })

    if not rows:
        return

    drift_df = pd.DataFrame(rows).sort_values("psi", ascending=False)

    for _, row in drift_df.iterrows():
        mlflow.log_metric(f"drift_psi_{row['feature']}", float(row["psi"]))
        mlflow.log_metric(f"drift_mean_shift_{row['feature']}", float(row["mean_shift_abs"]))

    mlflow.log_metric("drift_avg_psi", float(drift_df["psi"].mean()))
    mlflow.log_metric("drift_max_psi", float(drift_df["psi"].max()))
    mlflow.log_metric("drift_features_high", float((drift_df["drift_level"] == "alto").sum()))
    mlflow.log_metric("drift_features_moderate", float((drift_df["drift_level"] == "moderado").sum()))

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    summary_csv = artifacts_dir / "drift_summary.csv"
    drift_df.to_csv(summary_csv, index=False)
    mlflow.log_artifact(str(summary_csv), artifact_path="drift")

    status_color = {"baixo": "#16a34a", "moderado": "#f59e0b", "alto": "#dc2626"}
    table_rows = ""
    for _, row in drift_df.iterrows():
        color = status_color.get(row["drift_level"], "#6b7280")
        table_rows += (
            f"<tr>"
            f"<td>{row['feature']}</td>"
            f"<td>{row['reference_mean']:.4f}</td>"
            f"<td>{row['current_mean']:.4f}</td>"
            f"<td>{row['mean_shift_abs']:.4f}</td>"
            f"<td>{row['psi']:.4f}</td>"
            f"<td><span style='color:{color};font-weight:600'>{row['drift_level']}</span></td>"
            f"</tr>"
        )

    panel_html = f"""
<html>
  <head>
    <meta charset=\"utf-8\" />
    <title>Painel de Drift - MLflow</title>
  </head>
  <body style=\"font-family:Arial,sans-serif;padding:20px;\">
    <h2 style=\"margin-bottom:8px;\">Painel de Drift</h2>
    <p style=\"margin-top:0;color:#4b5563;\">
      Referência: dados de treino | Atual: validação real<br/>
      Média PSI: <b>{drift_df['psi'].mean():.4f}</b> | Máximo PSI: <b>{drift_df['psi'].max():.4f}</b>
    </p>
    <table border=\"1\" cellspacing=\"0\" cellpadding=\"8\" style=\"border-collapse:collapse;width:100%;\">
      <thead style=\"background:#f3f4f6;\">
        <tr>
          <th>Feature</th>
          <th>Média Referência</th>
          <th>Média Atual</th>
          <th>Shift Absoluto</th>
          <th>PSI</th>
          <th>Nível</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </body>
</html>
"""

    panel_path = artifacts_dir / "drift_panel.html"
    panel_path.write_text(panel_html, encoding="utf-8")
    mlflow.log_artifact(str(panel_path), artifact_path="drift")


def run_training():
    # Carregamento de Dados (Offline) para Treinamento e Testes
    # Primeiro, apontar para o repositório da FeatureStore
    feature_store = FeatureStore(repo_path="feature_repo")

    # Em seguida, carregar os dados off-line que contêm as chaves (RAs) e timestamps
    training_df = pd.read_parquet("feature_repo/data/df_evasao_escolar.parquet")
    training_df["DATA_REGISTRO"] = pd.to_datetime(training_df["DATA_REGISTRO"])

    data_ref = pd.to_datetime("2022-01-01")
    df_filtrado = training_df[training_df["DATA_REGISTRO"].dt.date == data_ref.date()]

    # Criação da entity_df com os RAs únicos e a data de referência (Feast usa essa tabela)
    entity_df = df_filtrado[["RA", "DATA_REGISTRO"]].drop_duplicates()

    # Recuperar as features históricas via Feast
    retrieval_df = (
        feature_store.get_historical_features(
            entity_df=entity_df,
            features=feature_store.get_feature_service("aluno_service"),
        )
        .to_df()
    )

    # Selecionar as features desejadas para o treinamento
    features_desejadas = [
        "EVASAO",
        "DESTAQUE_IEG",
        "CG",
        "CT",
        "DESTAQUE_IPV",
        "DESTAQUE_IDA",
        "CF",
        "IDADE",
        "FASE_IDEAL",
        "FASE",
        "ANO_INGRESSO",
    ]
    train_df = retrieval_df[features_desejadas]

    # Separar 10% para validação balanceada (Dados REAIS)
    val_size = max(int(len(train_df) * 0.10), 2)
    n_per_class = max(val_size // 2, 1)

    df_val_evasao = train_df[train_df["EVASAO"] == 1].sample(n=n_per_class, random_state=42)
    df_val_nao_evasao = train_df[train_df["EVASAO"] == 0].sample(n=n_per_class, random_state=42)

    df_val = pd.concat([df_val_evasao, df_val_nao_evasao]).sample(frac=1, random_state=42)
    df_treino_original = train_df.drop(df_val.index)

    X_restante = df_treino_original.drop("EVASAO", axis=1)
    y_restante = df_treino_original["EVASAO"]

    # SMOTE para 10.000 registros balanceados
    smote = SMOTE(sampling_strategy={0: 5000, 1: 5000}, random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_restante, y_restante)

    X_train, X_test, y_train, y_test = train_test_split(
        X_resampled, y_resampled, test_size=0.2, random_state=42
    )

    # Normalização (Ajustada no treino e aplicada ao resto)
    scaler = StandardScaler()
    if len(X_train) == 0:
        raise ValueError("No training samples available after resampling and split")
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # In case df_val has fewer rows than expected, handle gracefully
    if df_val.shape[0] == 0:
        X_val_scaled = X_test_scaled
        y_val = y_test
    else:
        X_val_scaled = scaler.transform(df_val.drop("EVASAO", axis=1))
        y_val = df_val["EVASAO"]

    # 6. Configuração do GridSearchCV para múltiplos modelos (usa `model_params` do módulo)

    results = []
    best_estimators = {}
    best_model_name = None
    pipeline = None
    model_path = None

    # iniciar experimento mlflow
    with mlflow.start_run():
        for model_name, mp in model_params.items():
            print(f"Iniciando GridSearchCV para {model_name}...")
            clf = GridSearchCV(mp["model"], mp["params"], cv=5, scoring="f1", n_jobs=-1)
            clf.fit(X_train_scaled, y_train)
            # Predição na validação (Dados REAIS)
            y_pred = clf.predict(X_val_scaled)
            f1 = f1_score(y_val, y_pred)

            # log dos parâmetros e métricas
            for k, v in clf.best_params_.items():
                mlflow.log_param(f"{model_name}_{k}", v)
            mlflow.log_metric(f"{model_name}_f1_val_real", f1)

            results.append({
                "model": model_name,
                "best_score_treino": clf.best_score_,
                "best_params": clf.best_params_,
                "f1_val_real": f1,
            })
            best_estimators[model_name] = clf.best_estimator_

        # ao final do run, registramos o modelo e metadata

        print("Registrando resultados no MLflow")

        # Selecionar o melhor modelo baseado em F1 na validação real
        best_result = max(results, key=lambda r: r["f1_val_real"])
        best_model_name = best_result["model"]
        best_estimator = best_estimators[best_model_name]

        # Criar pipeline com scaler + melhor estimador e salvar com timestamp
        pipeline = Pipeline([("scaler", scaler), ("model", best_estimator)])
        os.makedirs("models", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        model_path = f"models/model_{best_model_name}_{timestamp}.joblib"
        joblib.dump(pipeline, model_path)
        print(f"Melhor modelo ({best_model_name}) salvo em: {model_path}")

        # painel de drift no MLflow (comparação treino vs validação real)
        reference_for_drift = X_train
        if df_val.shape[0] == 0:
            current_for_drift = X_test
        else:
            current_for_drift = df_val.drop("EVASAO", axis=1)
        log_drift_panel_mlflow(reference_for_drift, current_for_drift, list(X_train.columns))

        # log do pipeline e parâmetros no MLflow
        mlflow.log_param("best_model", best_model_name)
        mlflow.log_artifact(model_path, artifact_path="models")
        mlflow.sklearn.log_model(pipeline, artifact_path="sklearn-model")

    print("\n" + "=" * 50)
    print("RESULTADOS FINAIS NA VALIDAÇÃO REAL")
    print("=" * 50)
    df_results = pd.DataFrame(results)
    print(df_results[["model", "f1_val_real", "best_params"]])

    # Executa o salvamento
    save_model_to_s3(pipeline, best_model_name)

    # Mostrar importância das variáveis para o Random Forest treinado (se existir)
    if "random_forest" in best_estimators:
        rf = best_estimators["random_forest"]
        importances = pd.Series(rf.feature_importances_, index=X_restante.columns)
        print("\nTop 5 Variáveis mais importantes (Random Forest):")
        print(importances.sort_values(ascending=False).head(5))


if __name__ == "__main__":
    run_training()
