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


def test_run_training_logs_to_mlflow(monkeypatch):
    train_module = _import_train_module(monkeypatch)

    # stub out pandas read_parquet to return minimal dataframe
    import pandas as pd
    monkeypatch.setattr(pd, "read_parquet", lambda path: pd.DataFrame({
        "RA": ["A"],
        "DATA_REGISTRO": [pd.Timestamp("2022-01-01")],
        "EVASAO": [0],
    }))

    # prepare dummy mlflow collector
    logs = []
    class DummyRun:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): pass
    class DummyMLflow:
        def start_run(self, nested=False):
            logs.append(("start", nested))
            return DummyRun()
        def log_metric(self, name, value):
            logs.append(("metric", name, value))
        def log_param(self, name, value):
            logs.append(("param", name, value))
        def log_artifact(self, path, artifact_path=None):
            logs.append(("artifact", path, artifact_path))
        class sklearn:
            @staticmethod
            def log_model(model, artifact_path):
                logs.append(("skmodel", artifact_path))
    class DummySCV:
        def __init__(self, *args, **kwargs):
            self.best_params_ = {}
            self.best_score_ = 1.0
            
            class DummyEstimator:
                def predict(self, X):
                    import numpy as np
                    return np.zeros(len(X))
                @property
                def feature_importances_(self):
                    import numpy as np
                    return np.zeros(10)
            self.best_estimator_ = DummyEstimator()

        def fit(self, X, y):
            return self

        def predict(self, X):
            return self.best_estimator_.predict(X)

    monkeypatch.setattr(train_module, "GridSearchCV", DummySCV)
    monkeypatch.setattr(train_module.joblib, "dump", lambda obj, path: None)
    monkeypatch.setattr(train_module, "save_model_to_s3", lambda p, n: None)
    monkeypatch.setattr(train_module, "mlflow", DummyMLflow())

    # run training (should not error with minimal data)
    train_module.run_training()

    assert any(l[0] == "metric" for l in logs), "expected mlflow metrics to be logged"
    assert any(l[0] in ("artifact","skmodel") for l in logs), "expected mlflow model/artifact to be logged"

