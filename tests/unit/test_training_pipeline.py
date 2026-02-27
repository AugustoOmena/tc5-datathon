import importlib
import sys
import types
import pytest


def _inject_dummy_feast_and_smote(monkeypatch):
    # Dummy feast module with a FeatureStore that returns a small DataFrame
    feast_mod = types.ModuleType("feast")

    class DummyFeatureStore:
        def __init__(self, repo_path=None):
            pass

        def get_feature_service(self, name):
            return None

        def get_historical_features(self, entity_df=None, features=None):
            class DummyRetrieval:
                def to_df(self):
                    import pandas as pd
                    return pd.DataFrame({
                        "RA": [1, 2, 3, 4],
                        "DATA_REGISTRO": [pd.Timestamp("2022-01-01")] * 4,
                        "EVASAO": [0, 1, 0, 1],
                        "DESTAQUE_IEG": [0, 0, 0, 0],
                        "CG": [0, 0, 0, 0],
                        "CT": [0, 0, 0, 0],
                        "DESTAQUE_IPV": [0, 0, 0, 0],
                        "DESTAQUE_IDA": [0, 0, 0, 0],
                        "CF": [0, 0, 0, 0],
                        "IDADE": [20, 21, 22, 23],
                        "FASE_IDEAL": [1, 1, 1, 1],
                        "FASE": [1, 1, 1, 1],
                        "ANO_INGRESSO": [2020, 2021, 2022, 2023],
                    })

            return DummyRetrieval()

    feast_mod.FeatureStore = DummyFeatureStore
    monkeypatch.setitem(sys.modules, "feast", feast_mod)

    # Dummy SMOTE to avoid heavy resampling during import
    imblearn_mod = types.ModuleType("imblearn.over_sampling")

    class DummySMOTE:
        def __init__(self, *args, **kwargs):
            pass

        def fit_resample(self, X, y):
            return X, y

    imblearn_mod.SMOTE = DummySMOTE
    monkeypatch.setitem(sys.modules, "imblearn.over_sampling", imblearn_mod)


def _import_train_module(monkeypatch):
    _inject_dummy_feast_and_smote(monkeypatch)
    # Ensure a fresh import in case tests run in same session
    if "src.training.train" in sys.modules:
        del sys.modules["src.training.train"]
    return importlib.import_module("src.training.train")


def test_model_params_contains_expected_models(monkeypatch):
    train_module = _import_train_module(monkeypatch)

    assert "knn" in train_module.model_params
    assert "logistic_regression" in train_module.model_params
    assert "random_forest" in train_module.model_params


def test_save_model_to_s3_uses_expected_bucket_and_prefix(monkeypatch):
    train_module = _import_train_module(monkeypatch)

    calls = {}

    class DummyS3Client:
        def upload_fileobj(self, buffer, bucket, key):
            calls["bucket"] = bucket
            calls["key"] = key

    def dummy_client(name):
        assert name == "s3"
        return DummyS3Client()

    monkeypatch.setattr(train_module.boto3, "client", dummy_client)

    dummy_pipeline = object()
    train_module.save_model_to_s3(dummy_pipeline, "logistic_regression")

    assert calls["bucket"] == "tc5-mlops-artifacts-f4d7a3e1"
    assert calls["key"].startswith("models/model_logistic_regression_")
    assert calls["key"].endswith(".joblib")

