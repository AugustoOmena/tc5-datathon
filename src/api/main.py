import os
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from feast import FeatureStore
from pathlib import Path

app = FastAPI(title="Predição de Evasão Escolar - TC5")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_PATH = BASE_DIR / "feature_repo"
MODEL_DIR = BASE_DIR / "models"

store = None
model = None
imputer_values = {}

FEATURES_MODEL = [
    "DESTAQUE_IEG", "CG", "CT", "DESTAQUE_IPV", "DESTAQUE_IDA",
    "CF", "IDADE", "FASE_IDEAL", "FASE", "ANO_INGRESSO"
]

class PredictRequest(BaseModel):
    ra: str

@app.on_event("startup")
def load_artifacts():
    global store, model
    try:
        store = FeatureStore(repo_path=str(REPO_PATH))
        model_files = list(MODEL_DIR.glob("*.joblib"))
        if not model_files:
            raise RuntimeError("Nenhum modelo encontrado na pasta /models")

        latest_model = max(model_files, key=os.path.getctime)
        model = joblib.load(latest_model)
        print(f"Artefatos carregados: Modelo {latest_model.name}")
        try:
            df_offline = pd.read_parquet(REPO_PATH / "data" / "df_evasao_escolar.parquet")
            for col in FEATURES_MODEL:
                if col in df_offline.columns:
                    imputer_values[col] = df_offline[col].median()
                else:
                    imputer_values[col] = 0
            print("Imputer values carregados para as features do modelo.")
        except Exception as ie:
            print(f"Aviso: não foi possível carregar dados off-line para imputação: {ie}")
    except Exception as e:
        print(f"Erro no startup: {e}")

@app.get("/")
def health_check():
    return {"status": "online", "model_loaded": model is not None}

@app.post("/predict")
async def predict(request: PredictRequest):
    if model is None or store is None:
        raise HTTPException(status_code=503, detail="Serviço indisponível: artefatos não carregados.")

    try:
        feature_vector = store.get_online_features(
            features=store.get_feature_service("aluno_service"),
            entity_rows=[{"RA": request.ra}]
        ).to_dict()

        input_df = pd.DataFrame.from_dict(feature_vector)

        features_model = [
            "DESTAQUE_IEG", "CG", "CT", "DESTAQUE_IPV", "DESTAQUE_IDA",
            "CF", "IDADE", "FASE_IDEAL", "FASE", "ANO_INGRESSO"
        ]

        X = input_df[features_model]

        missing_cols = X.columns[X.isnull().any()].tolist()
        imputed_cols = []
        if missing_cols:
            for col in missing_cols:
                fill_value = imputer_values.get(col, 0)
                X[col] = X[col].fillna(fill_value)
                imputed_cols.append(col)

        prediction = model.predict(X)[0]
        probability = model.predict_proba(X)[0].tolist()

        return {
            "ra": request.ra,
            "evasao_prediction": int(prediction),
            "probability": probability,
            "status": "sucesso"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na predição: {str(e)}")