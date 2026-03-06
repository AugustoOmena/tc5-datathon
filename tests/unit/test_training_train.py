import io
import builtins
import os
import joblib
import pandas as pd
import numpy as np
import pytest

from src.training import train as train_module


# Module-level estimator used by FakeGridSearch to remain picklable
class ModuleLevelEstimator:
    def __init__(self, n_features):
        self.feature_importances_ = np.array([1.0] * n_features)

    def predict(self, Xp):
        return np.zeros(len(Xp), dtype=int)


# Module-level FakeGridSearch to avoid creating local classes in .fit()
class FakeGridSearch:
    def __init__(self, model, params, cv, scoring, n_jobs):
        self.model = model
        self.params = params
        self.best_score_ = None
        self.best_params_ = None
        self.best_estimator_ = None

    def fit(self, X, y):
        self.best_score_ = 0.9
        self.best_params_ = {"dummy": 1}
        self.best_estimator_ = ModuleLevelEstimator(X.shape[1])
        return self

    def predict(self, X):
        return self.best_estimator_.predict(X)


def test_save_model_to_s3_success(monkeypatch, capsys):
    # Fake boto3 client that captures upload_fileobj calls
    class FakeS3Client:
        def upload_fileobj(self, fileobj, bucket, key):
            # read bytes to ensure buffer is valid
            data = fileobj.read()
            assert len(data) > 0

    monkeypatch.setattr(train_module, "boto3", type("B", (), {"client": lambda *a, **k: FakeS3Client()}))

    # Create a simple object to save
    pipeline = {"a": 1}
    train_module.save_model_to_s3(pipeline, "testmodel")

    captured = capsys.readouterr()
    assert "Sucesso! Melhor modelo (testmodel) salvo no S3" in captured.out


def test_save_model_to_s3_failure(monkeypatch, capsys):
    class FailingS3Client:
        def upload_fileobj(self, fileobj, bucket, key):
            raise RuntimeError("boom")

    monkeypatch.setattr(train_module, "boto3", type("B", (), {"client": lambda *a, **k: FailingS3Client()}))

    pipeline = {"a": 1}
    train_module.save_model_to_s3(pipeline, "badmodel")

    captured = capsys.readouterr()
    assert "Erro ao salvar no S3" in captured.out


def test_run_training_with_mocks(monkeypatch, tmp_path, capsys):
    # Prepare a fake read_parquet that returns a small DF with the target date
    df_parquet = pd.DataFrame({
        "RA": [1, 2, 3],
        "DATA_REGISTRO": pd.to_datetime(["2022-01-01", "2022-01-01", "2022-01-01"]),
    })

    monkeypatch.setattr(train_module.pd, "read_parquet", lambda *a, **k: df_parquet)

    # Fake FeatureStore
    class FakeHistorical:
        def __init__(self, df):
            self._df = df

        def to_df(self):
            return self._df

    class FakeFeatureStore:
        def __init__(self, repo_path=None):
            pass

        def get_feature_service(self, name):
            return None

        def get_historical_features(self, entity_df, features):
            # Create retrieval DF with the expected features
            n = 12
            data = {
                "EVASAO": [0, 1] * (n // 2),
                "DESTAQUE_IEG": np.random.rand(n),
                "CG": np.random.rand(n),
                "CT": np.random.rand(n),
                "DESTAQUE_IPV": np.random.rand(n),
                "DESTAQUE_IDA": np.random.rand(n),
                "CF": np.random.rand(n),
                "IDADE": np.random.randint(14, 25, size=n),
                "FASE_IDEAL": np.random.randint(1, 10, size=n),
                "FASE": np.random.randint(1, 10, size=n),
                "ANO_INGRESSO": np.random.randint(2015, 2023, size=n),
            }
            df = pd.DataFrame(data)
            return FakeHistorical(df)

    monkeypatch.setattr(train_module, "FeatureStore", FakeFeatureStore)

    # Fake SMOTE to return a balanced small dataset
    class FakeSMOTE:
        def __init__(self, sampling_strategy=None, random_state=None):
            pass

        def fit_resample(self, X, y):
            # produce 10 samples
            n = 10
            Xr = pd.DataFrame(np.tile(X.iloc[:1].values, (n, 1)), columns=X.columns)
            yr = pd.Series([0, 1] * (n // 2))
            return Xr, yr

    monkeypatch.setattr(train_module, "SMOTE", FakeSMOTE)

    monkeypatch.setattr(train_module, "GridSearchCV", FakeGridSearch)

    # Prevent actual S3 upload in the training run
    monkeypatch.setattr(train_module, "save_model_to_s3", lambda pipeline, name: None)

    # Run training - should complete without raising
    train_module.run_training()

    captured = capsys.readouterr()
    assert "RESULTADOS FINAIS NA VALIDAÇÃO REAL" in captured.out
    assert os.path.exists("models")
