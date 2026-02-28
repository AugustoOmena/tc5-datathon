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

### 📊 Monitoramento com MLflow
Além do dashboard em CloudWatch, o projeto agora registra **predições e características** em um experimento do MLflow. Isso permite analisar deriva de distribuição usando a UI do MLflow ou integrá‑la a ferramentas externas.

- O tracking URI é configurado pela variável de ambiente `MLFLOW_TRACKING_URI` (ex.: `http://<seu-servidor>:5000` ou `sqlite:///mlflow.db`).
- Artefatos (modelos, arquivos) podem ser armazenados em S3; o bucket criado durante o provisionamento (`mlflow_bucket_name` no `terraform output`) serve como `--default-artifact-root`.
- Na API Lambda, a cada requisição `/predict` uma *run* aninhada é criada e os valores das features + previsão são logados como métricas.
- No treinamento (`src/training/train.py`) o experimento armazena hiperparâmetros, F1 dos modelos, o pipeline final e um painel de drift com PSI.

Para visualizar:

```bash
# iniciar servidor MLflow local apontando para bucket S3 de artifacts
mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root s3://$(terraform -chdir=terraform output -raw mlflow_bucket_name) \
    --host 0.0.0.0 --port 5000
```

ou monte o servidor dentro da própria AWS (ex.: ECS/Fargate, EC2) usando as mesmas URIs. em qualquer caso o bucket retornado por `terraform output` servirá como destino de artefatos.

> **Exemplo de implantação na nuvem (ECS / Fargate)**
>
> 1. **Criar imagem Docker** com MLflow:
>    ```dockerfile
>    FROM python:3.11-slim
>    RUN pip install mlflow boto3
>    # opcional: inclua awscli ou outras dependências
>    CMD ["mlflow", "server", "--backend-store-uri", "sqlite:///mlflow.db", \
>           "--default-artifact-root", "s3://<BUCKET>", "--host", "0.0.0.0", "--port", "5000"]
>    ```
>
> 2. **Push da imagem** para o ECR na conta 488081132204 (região sa-east-1):
>    ```bash
>    aws ecr create-repository --repository-name mlflow-server --region sa-east-1
>    $(aws ecr get-login-password --region sa-east-1 | docker login --username AWS --password-stdin 488081132204.dkr.ecr.sa-east-1.amazonaws.com)
>    docker build -t mlflow-server:latest .
>    docker tag mlflow-server:latest 488081132204.dkr.ecr.sa-east-1.amazonaws.com/mlflow-server:latest
>    docker push 488081132204.dkr.ecr.sa-east-1.amazonaws.com/mlflow-server:latest
>    ```
>
> 3. **Criar cluster ECS/Fargate** (Terraform ou Console) e uma task definition usando a imagem acima, reservando porta 5000. Configure IAM role que permita `s3:GetObject/PutObject` no bucket `mlflow_bucket_name`.
>
> 4. **Provisionar um Application Load Balancer** apontando para o serviço, com listeners em 80/443 e regras para encaminhar ao container.
>
> 5. **Configurar variáveis de ambiente** na task: `AWS_REGION=sa-east-1`, `MLFLOW_S3_ENDPOINT_URL=https://s3.sa-east-1.amazonaws.com` (se necessário).
>
> 6. **Acessar a interface** via ALB DNS (ex.: `http://mlflow.example.com`) e use as credenciais IAM/Federation se quiser restringir.
>
> 7. **Opcional:** automatize o deploy com Terraform e `aws_ecs_service`, `aws_ecs_task_definition`, `aws_lb`, etc. A infra do projeto já contém providers e variáveis de região/conta.
>
> Em ambiente EC2 a ideia é semelhante: suba instância com a imagem acima ou instale MLflow, configure as mesmas URIs e vincule o bucket, abrindo porta 5000 no SG.

### 📌 Exemplo de Terraform para ECS/Fargate + ALB (porta 5000)

Se quiser automatizar todo o deploy na AWS, inclua um arquivo extra (`terraform/ecs_mlflow.tf`) parecido com este:

```hcl
provider "aws" {
  region = var.aws_region
}

resource "aws_ecs_cluster" "mlflow" {
  name = "mlflow-cluster"
}

resource "aws_ecs_task_definition" "mlflow" {
  family                   = "mlflow-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([{
    name      = "mlflow-server"
    image     = "488081132204.dkr.ecr.sa-east-1.amazonaws.com/mlflow-server:latest"
    essential = true
    portMappings = [{
      containerPort = 5000
      hostPort      = 5000
      protocol      = "tcp"
    }]
  }])
}

resource "aws_lb" "mlflow" {
  name               = "mlflow-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnets
}

resource "aws_lb_target_group" "mlflow" {
  name     = "mlflow-tg"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.mlflow.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mlflow.arn
  }
}

resource "aws_ecs_service" "mlflow" {
  name            = "mlflow-service"
  cluster         = aws_ecs_cluster.mlflow.id
  task_definition = aws_ecs_task_definition.mlflow.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  network_configuration {
    subnets         = var.private_subnets
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.mlflow.arn
    container_name   = "mlflow-server"
    container_port   = 5000
  }

  depends_on = [aws_lb_listener.http]
}
```

Esses recursos criam o cluster, a task com a imagem ECR, o ALB público (listener porta 80) e o serviço que registra o container no target group. Ajuste as variáveis `vpc_id`, `public_subnets`, `private_subnets` e os grupos de segurança conforme sua rede.

Depois de aplicar o Terraform, obtenha o DNS do ALB (`aws lb describe-load-balancers`) e acesse-o no navegador. Qualquer requisição HTTP será roteada à porta 5000 do container.

---
>
Em seguida acesse `http://localhost:5000` ou o endereço público e abra o experimento `evasao_experiment` (ou o nome definido via `MLFLOW_EXPERIMENT`).

O painel de **drift** já é gerado no treino e publicado no próprio run do MLflow em `Artifacts > drift`:

- `drift_panel.html`: tabela visual com PSI por feature e nível (`baixo`, `moderado`, `alto`)
- `drift_summary.csv`: dados tabulares para análises adicionais

Além dos artifacts, as métricas também ficam em `Metrics` no run (`drift_avg_psi`, `drift_max_psi`, `drift_psi_<feature>`).

> ⚠️ **Conta AWS / Região**: use as credenciais da conta `488081132204` e configure a região `us-east-1` antes de rodar o Terraform ou qualquer comando AWS. Por exemplo:
>
> ```bash
> export AWS_PROFILE=datathon
> export AWS_REGION=us-east-1
> terraform -chdir=terraform apply -var="aws_region=us-east-1"
> ```

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

## 📊 Monitoramento Contínuo

A aplicação publica logs e métricas para facilitar o acompanhamento e
identificação de drift do modelo. Tudo é enviado para a conta AWS **488081132204**
na região **sa-east-1** (Brasil).

1. **Logs**
   - O Lambda utiliza o `logging` padrão do Python; mensagens de `logger.info`/
     `logger.error` aparecem automaticamente no *CloudWatch Logs* no grupo
     `/aws/lambda/tc5-prediction-api`.
   - O Terraform já cria o grupo e define retenção de 7 dias.

2. **Métricas customizadas**
   - A cada chamada ao endpoint `/predict` são enviados dados para o namespace
     `TC5/Model` (valor da predição e contagem) e `TC5/ModelFeatures`
     (valores de entrada) usando `cloudwatch.put_metric_data`.
   - Essas métricas permitem montar gráficos simples e detectar mudanças na
     distribuição ao longo do tempo.

3. **Dashboard de drift**
   - O `terraform` provisiona um *CloudWatch Dashboard* chamado
     `tc5-model-monitoring` com um widget para visualizar a média e o volume de
     previsões.
   - A qualquer momento acesse
     `https://console.aws.amazon.com/cloudwatch/home?region=sa-east-1#dashboards:
     name=tc5-model-monitoring` (ajuste a conta/URL conforme necessário).

4. **Extensões e melhorias**
   - É possível adicionar um *CloudWatch Event Rule* / *Lambda agendado* para
     calcular métricas de drift mais sofisticadas (p.ex. Kullback‑Leibler ou
     KS) a partir das métricas já publicadas.
   - Qualquer alarme ou *dashboard* adicional pode ser definido via Terraform
     ou manualmente na console.

---

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
