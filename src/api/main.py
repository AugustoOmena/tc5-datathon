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
import logging

# basic logger which will be captured by CloudWatch Logs when running in Lambda
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tc5_api")

# CloudWatch client for custom metrics
cw_client = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "sa-east-1"))

# MLflow tracking
import mlflow

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI")
if MLFLOW_URI:
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT", "evasao_api"))

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
        logger.info("✅ Feast inicializado no /tmp")
        
        bucket_name = os.environ.get("S3_BUCKET_NAME", "tc5-mlops-artifacts-f4d7a3e1")
        s3_client = boto3.client('s3')
        
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="models/")
        model_files = [f for f in response.get('Contents', []) if f['Key'].endswith('.joblib')]
        
        if not model_files:
            raise Exception("Nenhum modelo encontrado no S3")
            
        latest_file = max(model_files, key=lambda x: x['LastModified'])['Key']
        logger.info(f"Baixando modelo: {latest_file}")
        
        model_obj = s3_client.get_object(Bucket=bucket_name, Key=latest_file)
        model = joblib.load(io.BytesIO(model_obj['Body'].read()))
        
    except Exception as e:
        # Se falhar aqui, o log aparecerá agora porque estamos dentro do startup
        logger.error(f"ERRO NO STARTUP: {str(e)}")
        raise e
    
@app.get("/")
def health_check():
    return {"status": "online", "model_loaded": model is not None}

@app.post("/predict")
async def predict(request: PredictRequest):
    if model is None or store is None:
        raise HTTPException(status_code=503, detail="Serviço indisponível: artefatos não carregados.")

    try:
        # tenta obter as features pelo Feast; se não existir a FeatureService/FeatureView,
        # cai para um fallback que lê o parquet local em feature_repo/data
        try:
            try:
                feature_refs = store.get_feature_service("aluno_service")
            except Exception as fs_err:
                logger.warning(f"Feature service 'aluno_service' não encontrada; usando referências explícitas de features. Detalhe: {fs_err}")
                feature_refs = [f"aluno_features:{f}" for f in FEATURES_MODEL]

            feature_vector = store.get_online_features(
                features=feature_refs,
                entity_rows=[{"RA": request.ra}]
            ).to_dict()

            input_df = pd.DataFrame.from_dict(feature_vector)

        except Exception as fe_err:
            # fallback: ler parquet local do feature_repo
            logger.warning(f"Falha ao obter features via Feast: {fe_err}. Tentando fallback local (parquet).")
            parquet_path = REPO_PATH / "data" / "df_evasao_escolar.parquet"
            if not parquet_path.exists():
                raise HTTPException(status_code=500, detail=f"Erro na predição: Falha ao obter features via Feast e arquivo local não encontrado ({parquet_path})")

            df_all = pd.read_parquet(parquet_path)
            if "RA" not in df_all.columns:
                raise HTTPException(status_code=500, detail="Erro na predição: arquivo local de features não contém a coluna 'RA'.")

            rows = df_all[df_all["RA"] == request.ra]
            if rows.empty:
                raise HTTPException(status_code=404, detail=f"Aluno {request.ra} não encontrado no Feature Store local.")

            # selecionar a linha mais recente se houver campo de timestamp
            if "DATA_REGISTRO" in rows.columns:
                row = rows.sort_values("DATA_REGISTRO").iloc[-1]
            else:
                row = rows.iloc[-1]

            available_feats = [f for f in FEATURES_MODEL if f in row.index]
            if not available_feats:
                raise HTTPException(status_code=500, detail="Erro na predição: nenhuma das features esperadas foi encontrada no registro local.")

            input_df = pd.DataFrame([row[available_feats]])

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

        # log information for monitoring
        logger.info(f"predicted ra={request.ra} value={prediction} prob={probability}")

        # push custom metrics to CloudWatch so dashboard can track drift
        try:
            cw_client.put_metric_data(
                Namespace="TC5/Model",
                MetricData=[
                    {"MetricName": "PredictionValue", "Value": float(prediction)},
                    {"MetricName": "PredictionCount", "Value": 1},
                ],
            )
            # also send feature values (first record) for drift analysis
            feature_metrics = []
            for col in X.columns:
                # flatten numpy types
                feature_metrics.append({"MetricName": col, "Value": float(X[col].iloc[0])})
            if feature_metrics:
                cw_client.put_metric_data(Namespace="TC5/ModelFeatures", MetricData=feature_metrics)
        except Exception as cw_err:
            logger.warning(f"falha ao enviar métricas para CloudWatch: {cw_err}")

        # record the prediction and features in MLflow if configured
        if MLFLOW_URI:
            try:
                with mlflow.start_run(nested=True):
                    mlflow.log_metric("prediction", float(prediction))
                    for col in X.columns:
                        mlflow.log_metric(col, float(X[col].iloc[0]))
            except Exception as m_err:
                logger.warning(f"falha ao enviar métricas para MLflow: {m_err}")

        return {
            "ra": request.ra,
            "evasao_prediction": int(prediction),
            "probability": probability,
            "status": "sucesso"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na predição: {str(e)}")