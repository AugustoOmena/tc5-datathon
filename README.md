# 🎓 Projeto MLOps: Predição de Evasão Escolar (FIAP TC5)

Este projeto implementa uma arquitetura de MLOps de ponta a ponta para **predição de evasão escolar**. O sistema utiliza uma abordagem serverless escalável, integrando uma Feature Store para gestão de dados e um Model Registry dinâmico no S3.

---

## 📁 Estrutura do Projeto

Visão geral do que cada diretório contém:

| Diretório           | Descrição                                                                                                                                                      |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`src/`**          | Código-fonte da aplicação.                                                                                                                                     |
| **`src/api/`**      | API FastAPI (predição de evasão). Endpoints `/predict` e `/docs`, adaptada para AWS Lambda via Mangum.                                                         |
| **`src/training/`** | Pipeline de treinamento: consome dados via Feast, executa GridSearchCV e envia o melhor modelo (.joblib) para o S3.                                            |
| **`feature_repo/`** | Repositório do **Feast** (Feature Store): definições de features, `feature_store.yaml`, dados e registros (SQLite). Clonado em runtime no Lambda para escrita. |
| **`terraform/`**    | Infraestrutura como Código (IaC): provisionamento AWS (Lambda, API Gateway, ECR, S3, IAM, etc.) e estado remoto no S3.                                         |
| **`notebooks/`**    | Jupyter notebooks para exploração e experimentos.                                                                                                              |
| **`models/`**       | Diretório local para artefatos de modelo (em produção o modelo vem do S3).                                                                                     |

Arquivos na raiz: `Dockerfile` (imagem Lambda), `requirements.txt` (dependências Python) e `.gitignore`.

---

## 🏗️ Arquitetura e Tecnologias

- **Feature Store:** [Feast](https://feast.dev/) — gerenciamento de features históricas e online.
- **Model Registry:** AWS S3 — armazenamento versionado de artefatos `.joblib`.
- **API:** FastAPI + Mangum — adaptador para AWS Lambda.
- **Infraestrutura:** Terraform (IaC).
- **Containerização:** Docker — imagem otimizada `linux/amd64` para AWS Lambda.
- **Modelagem:** Scikit-Learn — pipelines de pré-processamento e modelos de classificação.

---

## 🚀 Fluxo de Operação

### 1. Infraestrutura (Terraform)

O provisionamento da AWS é automatizado. O estado do Terraform (`tfstate`) é armazenado remotamente no S3 para permitir colaboração e segurança.

```bash
cd terraform
terraform init -migrate-state
terraform apply
```

### 2. Pipeline de Treinamento & Upload

O script de treino consome dados via Feast, executa GridSearchCV e envia o melhor modelo (`.joblib`) automaticamente para o bucket S3.

**Diferencial:** o melhor modelo é selecionado via **F1-Score** em um set de validação real.

```bash
python src/training/train.py
```

### 3. Deploy da API (Serverless Docker)

A API é empacotada em um container Docker e enviada para o AWS ECR.

```bash
# Build focado na arquitetura do Lambda (AMD64)
docker build --platform linux/amd64 --provenance=false -t [ECR_URI]:latest .
docker push [ECR_URI]:latest

# Atualização da função
aws lambda update-function-code --function-name tc5-prediction-api --image-uri [ECR_URI]:latest --region us-east-1
```

### 4. Funcionamento da API na Nuvem

- **Startup dinâmico:** ao iniciar, a API lista o bucket S3, identifica o modelo mais recente e o carrega em memória.
- **Escrita em runtime:** para contornar a natureza read-only do Lambda, a API clona o repositório do Feast para a pasta `/tmp` no boot, garantindo permissão de escrita para locks do SQLite.

---

## 📈 Resultados do Modelo

O pipeline de treinamento avaliou múltiplos modelos, obtendo o seguinte desempenho na validação real:

| Modelo                  | F1-Score | Observação                       |
| ----------------------- | -------- | -------------------------------- |
| **Regressão Logística** | ~0,73    | Modelo selecionado para produção |
| KNN                     | ~0,52    | —                                |
| Random Forest           | ~0,44    | —                                |

---

## 🛠️ Endpoints Principais

| Método   | Endpoint   | Descrição                                                              |
| -------- | ---------- | ---------------------------------------------------------------------- |
| **POST** | `/predict` | Envia o RA do aluno e recebe a predição de evasão e as probabilidades. |
| **GET**  | `/docs`    | Documentação interativa Swagger (acessível via API Gateway).           |

---

## 🤖 Automação CI/CD (GitHub Actions)

O projeto está configurado para deploy automático via GitHub Actions sempre que houver um push na branch `main`, automatizando o ciclo de **Build**, **Push** e **Update** no ambiente AWS.

---

## ✅ Testes Automatizados

- **Rodar testes unitários e de integração básica**:

```bash
pytest
```

- **Rodar testes com cobertura de código**:

```bash
pytest --cov=src --cov=feature_repo
```

Observações:

- Os testes usam `pytest` e estão organizados em `tests/unit` e `tests/integration`.
- O teste de integração da API (`tests/integration/test_api_predict_integration.py`) fica marcado como `skip` por padrão, pois depende de acesso real ao S3 e ao Feast configurado. Remova o `@pytest.mark.skip` quando o ambiente estiver pronto.
