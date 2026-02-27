from feature_repo import feature_definitions as fd


def test_aluno_entity_has_expected_name_and_join_key():
    assert fd.aluno.name == "aluno"
    assert fd.aluno.join_key == "RA"


def test_aluno_feature_view_has_expected_name():
    assert fd.aluno_features.name == "aluno_features"


def test_aluno_service_has_expected_name():
    assert fd.aluno_service.name == "aluno_service"

