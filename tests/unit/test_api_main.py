import asyncio
from datetime import datetime, timedelta

import numpy as np
import pytest
from fastapi import HTTPException

from src.api import main


@pytest.fixture(autouse=True)
def reset_globals():
    main.store = None
    main.model = None
    main.imputer_values = {}
    yield
    main.store = None
    main.model = None
    main.imputer_values = {}


def test_health_check_returns_online_status():
    response = main.health_check()
    assert response["status"] == "online"
    assert isinstance(response["model_loaded"], bool)


def test_predict_returns_503_when_artifacts_not_loaded():
    main.store = None
    main.model = None

    async def _call():
        return await main.predict(main.PredictRequest(ra="RA-123"))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_call())

    assert exc.value.status_code == 503
    assert "artefatos não carregados" in exc.value.detail


def test_predict_happy_path_with_stubbed_dependencies():
    class DummyStore:
        def get_feature_service(self, name: str):
            return "dummy_service"

        def get_online_features(self, features, entity_rows):
            # Simula retorno no formato esperado por to_dict()
            data = {
                "DESTAQUE_IEG": [1.0],
                "CG": [2.0],
                "CT": [3.0],
                "DESTAQUE_IPV": [4.0],
                "DESTAQUE_IDA": [5.0],
                "CF": [6.0],
                "IDADE": [18.0],
                "FASE_IDEAL": [1.0],
                "FASE": [1.0],
                "ANO_INGRESSO": [2024.0],
            }

            class DummyFeatures(dict):
                def to_dict(self_inner):
                    return data

            return DummyFeatures()

    class DummyModel:
        def predict(self, X):
            # Retorna sempre previsão de evasão = 1
            return [1]

        def predict_proba(self, X):
            # Probabilidades dummy [p_nao_evasao, p_evasao] como ndarray (compatível com .tolist())
            return np.array([[0.3, 0.7]])

    main.store = DummyStore()
    main.model = DummyModel()
    main.imputer_values = {}

    async def _call():
        return await main.predict(main.PredictRequest(ra="RA-999"))

    response = asyncio.run(_call())

    assert response["ra"] == "RA-999"
    assert response["evasao_prediction"] == 1
    assert response["probability"] == [0.3, 0.7]
    assert response["status"] == "sucesso"


def test_predict_handles_internal_exception():
    class DummyStore:
        def get_feature_service(self, name: str):
            return "dummy_service"

        def get_online_features(self, features, entity_rows):
            class DummyFeatures(dict):
                def to_dict(self_inner):
                    return {
                        "DESTAQUE_IEG": [1.0],
                        "CG": [2.0],
                        "CT": [3.0],
                        "DESTAQUE_IPV": [4.0],
                        "DESTAQUE_IDA": [5.0],
                        "CF": [6.0],
                        "IDADE": [18.0],
                        "FASE_IDEAL": [1.0],
                        "FASE": [1.0],
                        "ANO_INGRESSO": [2024.0],
                    }

            return DummyFeatures()

    class FailingModel:
        def predict(self, X):
            raise ValueError("falha interna")

        def predict_proba(self, X):
            return np.array([[0.3, 0.7]])

    main.store = DummyStore()
    main.model = FailingModel()

    async def _call():
        return await main.predict(main.PredictRequest(ra="RA-999"))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_call())

    assert exc.value.status_code == 500
    assert "falha interna" in exc.value.detail


def test_get_latest_model_s3_returns_latest(monkeypatch):
    """
    Verifica se a função seleciona o modelo mais recente pelo LastModified.
    """

    class DummyS3Client:
        def list_objects_v2(self, Bucket, Prefix):
            now = datetime.now()
            return {
                "Contents": [
                    {"Key": "models/model_old.joblib", "LastModified": now - timedelta(days=1)},
                    {"Key": "models/model_new.joblib", "LastModified": now},
                ]
            }

    monkeypatch.setattr(main.boto3, "client", lambda service: DummyS3Client())

    key = main.get_latest_model_s3("dummy-bucket")
    assert key == "models/model_new.joblib"


def test_get_latest_model_s3_raises_when_no_files(monkeypatch):
    class EmptyS3Client:
        def list_objects_v2(self, Bucket, Prefix):
            return {"Contents": []}

    monkeypatch.setattr(main.boto3, "client", lambda service: EmptyS3Client())

    with pytest.raises(RuntimeError):
        main.get_latest_model_s3("dummy-bucket")


def test_load_artifacts_success(monkeypatch):
    calls = {"copytree": False, "feature_store_repo_path": None, "joblib_loaded": False}

    monkeypatch.setattr(main.os.path, "exists", lambda path: True)
    monkeypatch.setattr(main.shutil, "rmtree", lambda path: None)

    def fake_copytree(src, dst):
        calls["copytree"] = True

    monkeypatch.setattr(main.shutil, "copytree", fake_copytree)

    class DummyStore:
        def __init__(self, repo_path):
            calls["feature_store_repo_path"] = repo_path

    monkeypatch.setattr(main, "FeatureStore", DummyStore)

    class DummyBody:
        def read(self):
            return b"dummy-bytes"

    class DummyS3Client:
        def list_objects_v2(self, Bucket, Prefix):
            now = datetime.now()
            return {
                "Contents": [
                    {"Key": "models/model_dummy.joblib", "LastModified": now},
                ]
            }

        def get_object(self, Bucket, Key):
            return {"Body": DummyBody()}

    monkeypatch.setattr(main.boto3, "client", lambda service: DummyS3Client())

    def fake_joblib_load(buffer):
        calls["joblib_loaded"] = True
        return "dummy-model"

    monkeypatch.setattr(main.joblib, "load", fake_joblib_load)

    # Força o bucket via env var
    monkeypatch.setenv("S3_BUCKET_NAME", "dummy-bucket")

    main.load_artifacts()

    assert isinstance(main.store, DummyStore)
    assert main.model == "dummy-model"
    assert calls["copytree"] is True
    assert calls["feature_store_repo_path"] == "/tmp/feature_repo"
    assert calls["joblib_loaded"] is True


def test_load_artifacts_propagates_exception(monkeypatch):
    monkeypatch.setattr(main.os.path, "exists", lambda path: False)
    monkeypatch.setattr(main.shutil, "copytree", lambda src, dst: None)

    def failing_feature_store(repo_path):
        raise RuntimeError("erro ao inicializar FeatureStore")

    monkeypatch.setattr(main, "FeatureStore", failing_feature_store)

    with pytest.raises(RuntimeError):
        main.load_artifacts()

