import pytest

import src.training.Train as train_module


def test_model_params_contains_expected_models():
    assert "knn" in train_module.model_params
    assert "logistic_regression" in train_module.model_params
    assert "random_forest" in train_module.model_params


def test_save_model_to_s3_uses_expected_bucket_and_prefix(monkeypatch):
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

