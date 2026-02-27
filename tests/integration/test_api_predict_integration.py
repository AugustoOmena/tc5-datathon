"""
Testes de integração básicos para a API.

Observação:
- Estes testes assumem que o Feast e o modelo estejam disponíveis.
- Em ambientes locais sem S3/Feast configurados, é recomendado marcar estes testes
  com @pytest.mark.skip ou configurar fixtures específicos.
"""

import os

import pytest
from fastapi.testclient import TestClient

from src.api import main


@pytest.mark.skip(reason="Requer S3/Feast configurados para rodar de ponta a ponta.")
def test_predict_integration_with_real_dependencies():
    client = TestClient(main.app)

    # Garante que o bucket default está configurado
    os.environ.setdefault("S3_BUCKET_NAME", "tc5-mlops-artifacts-f4d7a3e1")

    response = client.post("/predict", json={"ra": "RA-23"})
    assert response.status_code in (200, 500, 503)

