import io
import os
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from feast import FeatureStore
from pathlib import Path
from mangum import Mangum
import boto3
import shutil

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
    ra: str = Field(example="RA-23", description="RA do aluno (deve começar com RA-)")

handler = Mangum(app)

def get_latest_model_s3(bucket_name):
    s3_client = boto3.client('s3')
    
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="models/")
    files = response.get('Contents', [])
    
    if not files:
        raise RuntimeError("Nenhum modelo encontrado no S3!")

    model_files = [f for f in files if f['Key'].endswith('.joblib')]
    
    latest_file = max(model_files, key=lambda x: x['LastModified'])
    return latest_file['Key']

@app.on_event("startup")
def load_artifacts():
    global model, store
    
    source_repo = "/var/task/feature_repo"
    temp_repo = "/tmp/feature_repo"
    
    try:
        if os.path.exists(temp_repo):
            shutil.rmtree(temp_repo)
        shutil.copytree(source_repo, temp_repo)
        
        store = FeatureStore(repo_path=temp_repo)
        print("✅ Feast inicializado no /tmp")
        
        bucket_name = os.environ.get("S3_BUCKET_NAME", "tc5-mlops-artifacts-f4d7a3e1")
        s3_client = boto3.client('s3')
        
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="models/")
        model_files = [f for f in response.get('Contents', []) if f['Key'].endswith('.joblib')]
        
        if not model_files:
            raise Exception("Nenhum modelo encontrado no S3")
            
        latest_file = max(model_files, key=lambda x: x['LastModified'])['Key']
        print(f"Baixando modelo: {latest_file}")
        
        model_obj = s3_client.get_object(Bucket=bucket_name, Key=latest_file)
        model = joblib.load(io.BytesIO(model_obj['Body'].read()))
        
    except Exception as e:
        # Se falhar aqui, o log aparecerá agora porque estamos dentro do startup
        print(f"ERRO NO STARTUP: {str(e)}")
        raise e
    
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