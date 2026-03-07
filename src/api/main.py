import io
import os
import time
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from feast import FeatureStore
from pathlib import Path
from mangum import Mangum
import boto3
import shutil
import logging
import subprocess

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


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    # Log in logfmt to simplify Loki parsing and aggregations.
    logger.info(
        "api_request method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

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
    allow_startup_without_artifacts = os.environ.get("ALLOW_STARTUP_WITHOUT_ARTIFACTS", "false").lower() in {
        "1", "true", "yes"
    }
    
    try:
        if os.path.exists(temp_repo):
            shutil.rmtree(temp_repo)
        shutil.copytree(source_repo, temp_repo)
        
        store = FeatureStore(repo_path=temp_repo)
        # Ensure registry is populated in fresh containers.
        try:
            store.get_feature_service("aluno_service")
        except Exception:
            logger.info("Feature service ausente no registry; executando feast apply")
            subprocess.run(["feast", "apply"], cwd=temp_repo, check=True)
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
        # Optional local mode: keep API online for observability even without S3/Feast.
        logger.error(f"ERRO NO STARTUP: {str(e)}")
        if allow_startup_without_artifacts:
            model = None
            store = None
            logger.warning("API iniciada sem artefatos por ALLOW_STARTUP_WITHOUT_ARTIFACTS=true")
            return
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