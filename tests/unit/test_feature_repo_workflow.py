import pandas as pd

from feature_repo import test_workflow as tw


def test_fetch_historical_features_entity_df_calls_store(monkeypatch):
    class DummyResult:
        def to_df(self):
            return pd.DataFrame({"x": [1]})

    class DummyStore:
        def __init__(self):
            self.called = False
            self.entity_df = None
            self.features = None

        def get_historical_features(self, entity_df, features):
            self.called = True
            self.entity_df = entity_df
            self.features = features
            return DummyResult()

    store = DummyStore()
    tw.fetch_historical_features_entity_df(store, for_batch_scoring=False)
    assert store.called is True
    assert "driver_id" in store.entity_df.columns

    store2 = DummyStore()
    tw.fetch_historical_features_entity_df(store2, for_batch_scoring=True)
    assert store2.called is True
    assert "event_timestamp" in store2.entity_df.columns


def test_fetch_online_features_selects_correct_feature_source(monkeypatch):
    class DummyStore:
        def __init__(self):
            self.last_features = None
            self.last_entity_rows = None
            self.last_service_requested = None

        def get_feature_service(self, name: str):
            self.last_service_requested = name
            return f"service-{name}"

        def get_online_features(self, features, entity_rows):
            self.last_features = features
            self.last_entity_rows = entity_rows

            class DummyResult(dict):
                def to_dict(self_inner):
                    return {"dummy": [1]}

            return DummyResult()

    store = DummyStore()

    tw.fetch_online_features(store)
    assert isinstance(store.last_features, list)
    assert len(store.last_features) > 0

    tw.fetch_online_features(store, source="feature_service")
    assert store.last_service_requested == "driver_activity_v1"

    tw.fetch_online_features(store, source="push")
    assert store.last_service_requested == "driver_activity_v3"


def test_run_demo_happy_path(monkeypatch):
    calls = {"subprocess": [], "materialize": 0, "push": 0}
    created_stores = []

    def fake_run(cmd):
        calls["subprocess"].append(cmd)

    monkeypatch.setattr(tw.subprocess, "run", fake_run)

    class DummyResult:
        def to_df(self):
            return pd.DataFrame({"x": [1]})

        def to_dict(self):
            return {"dummy": [1]}

    class DummyStore:
        def __init__(self, repo_path):
            self.repo_path = repo_path
            created_stores.append(self)

        def get_historical_features(self, entity_df, features):
            return DummyResult()

        def materialize_incremental(self, end_date):
            calls["materialize"] += 1

        def get_feature_service(self, name: str):
            return f"service-{name}"

        def get_online_features(self, features, entity_rows):
            return DummyResult()

        def push(self, name, df, to):
            calls["push"] += 1

    monkeypatch.setattr(tw, "FeatureStore", DummyStore)

    tw.run_demo()

    assert created_stores and created_stores[0].repo_path == "."

    assert any("feast" in cmd for cmd in calls["subprocess"])
    assert len(calls["subprocess"]) >= 2

    assert calls["materialize"] >= 1
    assert calls["push"] >= 1

