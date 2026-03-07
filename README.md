# MLOPS Datathon (Fase 5) : Predição de Evação Escolar - Case Passos Mágicos

Para o Datathon, o desafio proposto foi o seguinte:


📢 **Problema:**

A Associação Passos Mágicos atua na transformação de vidas de crianças e jovens em vulnerabilidade social por meio de um modelo que integra educação de qualidade, apoio psicossocial e desenvolvimento pessoal. No entanto, essa missão enfrenta barreiras severas como a insegurança alimentar, o trabalho precoce e a defasagem idade-série, fatores que historicamente alimentam a evasão escolar no Brasil. A saída prematura do estudante não representa apenas uma perda estatística, mas a interrupção de um ciclo de aceleração do conhecimento e o distanciamento de oportunidades que poderiam romper a barreira da desigualdade social.

Nesse cenário, o desenvolvimento de um modelo preditivo torna-se uma ferramenta estratégica para a sustentabilidade do impacto social da organização. Ao analisar indicadores críticos como o INDE (Índice de Desenvolvimento Educacional) e suas dimensões de desempenho acadêmico e engajamento (IDA e IEG) — que juntos explicam cerca de 90% da variação do desenvolvimento dos alunos —, o modelo permite uma atuação preventiva. Identificar antecipadamente os perfis com maior risco de abandono possibilita que a equipe direcione intervenções personalizadas, garantindo que o suporte da Passos Mágicos não seja interrompido antes da transformação completa da realidade do aluno.

## 📌 Objetivos


Desenvolver e operacionalizar um ecossistema de Machine Learning capaz de prever o risco de evasão escolar, permitindo intervenções preventivas e baseadas em dados. Para isso, os objetivos específicos incluem:

- **Engenharia de Dados e Governança:** Estruturar um pipeline de ingestão para organizar, tratar e normalizar os dados históricos da Passos Mágicos, implementando um Feature Store para garantir a consistência e a disponibilidade dos dados tanto para o treinamento quanto para a inferência.

- **Desenvolvimento do Modelo Preditivo:** Treinar e otimizar modelos de classificação, com foco no ajuste de hiperparâmetros e na utilização da métrica F1-Score, priorizando a precisão na identificação de alunos em risco real de evasão no ciclo seguinte.

- **Implementação de MLOps e Deploy:** Realizar o deploy do modelo de melhor desempenho em ambiente de nuvem (AWS), utilizando FastAPI para a interface de consumo e GitHub Actions para a automação do fluxo de CI/CD (integração e entrega contínua).

- **Monitoramento e Escalabilidade:** Estabelecer ferramentas de monitoramento para rastrear a saúde da aplicação em produção, acompanhando métricas de performance técnica, tempos de resposta e o consumo de recursos computacionais.

- **Reprodutibilidade e Storytelling:** Documentar todo o ciclo de vida do projeto, desde a análise exploratória até o deploy final, garantindo que a solução seja auditável e apresentando os resultados de forma estratégica para os stakeholders.


## 📌 Entregáveis


- **Repositório de Código-Fonte:** Ambiente no GitHub com a estrutura completa do projeto, seguindo boas práticas de organização, versionamento e documentação do código (scripts de treinamento, processamento e infraestrutura).

- **Documentação Técnica (README):** Guia detalhado abrangendo desde a análise exploratória e lógica de negócio até as instruções de execução e arquitetura da solução.

- **Infraestrutura de Ingestão e Feature Store:** Implementação do pipeline de dados que garante a persistência e o consumo de atributos tratados para o modelo.

- **API de Inferência em Produção:** Endpoint desenvolvido em FastAPI e hospedado em nuvem (AWS), permitindo a integração do modelo com outras aplicações em tempo real.

- **Pipeline de CI/CD:** Automação do deploy via GitHub Actions, garantindo a entrega contínua e a integridade do ambiente produtivo.

- **Apresentação Executiva (Vídeo):** Pitch de até cinco minutos com foco gerencial, apresentando o storytelling do problema, a arquitetura da solução e os resultados alcançados pelo modelo.
  

## 📌 Desafios


O desenvolvimento desta solução enfrentou desafios críticos inerentes a projetos de impacto social e engenharia de ML:

- **Qualidade e Consistência de Dados Históricos:** Lidar com dados provenientes de diferentes edições da pesquisa (PEDE 2020, 2021, 2022) exigiu um rigoroso processo de limpeza para tratar valores ausentes (missing values) e padronizar registros inconsistentes entre os anos.

- **Engenharia de Atributos (Feature Engineering):** A dificuldade de transformar indicadores multidimensionais e subjetivos (como os indicadores psicossociais e psicopedagógicos) em variáveis numéricas de alta qualidade que realmente possuam poder preditivo para o modelo.

- **Escalabilidade e Custo Computacional:** O processamento de grandes volumes de dados brutos exigiu a estruturação de um pipeline eficiente para evitar latência e custos excessivos de nuvem durante o treinamento e a inferência.

- **Orquestração do Deploy:** Configurar um fluxo de CI/CD via GitHub Actions para a AWS que garanta que o modelo em produção seja sempre o de melhor performance, sem interromper a disponibilidade da API.
  

## 📌 Proposta de solução


A solução proposta consiste no desenvolvimento de um ecossistema de Machine Learning de ponta a ponta (end-to-end), projetado para identificar precocemente alunos com alto risco de evasão escolar. A inteligência do modelo baseia-se em uma arquitetura de dados temporal, permitindo que a organização atue de forma preventiva antes que o desligamento do aluno se concretize.

A solução está estruturada nos seguintes pilares técnicos:

- **Engenharia de Dados e Janelas Temporais:** O dataset foi construído utilizando uma lógica de Janelas de Dados (Rolling Windows). Em vez de registros estáticos, o modelo analisa "ciclos anuais" de desempenho (Ano N) para prever a permanência ou evasão no ano subsequente (Ano N+1). Foram consolidadas janelas de treinamento (Ex: 2022 -> 2023 e 2023 -> 2024), permitindo que o algoritmo aprenda padrões de comportamento que precedem o abandono.

- **Estratégia de Rotulagem (Labeling) e Tratamento de Exceções:** Implementamos uma regra de negócio rigorosa para a definição do Target. Foram classificados como Evasão (Classe 1) os alunos ausentes no ano seguinte, com a exclusão automática de casos de "Conclusão" (Fase 8/Universitários e Formados). Isso garante que o modelo não confunda o sucesso acadêmico com a evasão escolar, aumentando a precisão da ferramenta.

- **Governança com Feature Store:** Utilização de um repositório centralizado (feature_repo) para gerenciar indicadores multidimensionais (INDE, notas de Português/Matemática e indicadores psicossociais). O uso do Feast garante que as mesmas definições de variáveis sejam usadas de forma consistente no treinamento e na inferência via API.

- **Infraestrutura Cloud e MLOps:** Provisionamento de recursos na AWS via Terraform, utilizando AWS Lambda e FastAPI para servir as predições. O ciclo de vida é automatizado por um pipeline de CI/CD no GitHub Actions, que realiza testes de integração e o deploy contínuo da solução em containers Docker.

Com essa abordagem, a Passos Mágicos obtém uma ferramenta capaz de correlacionar oscilações em indicadores críticos (como a mudança na cor da "Pedra" ou queda no INDE) com o risco iminente de evasão, transformando dados históricos em ações preventivas de impacto social.


**Importante**

Os arquivos **Datathon - Anotações Importantes.docx** e **Construção do Dataset para Modelo de Classificação de Evasão.docx** anexos a este repositório possuem uma série de informações compiladadas sobre a metodologia abordada pela Passos Mágicos, bem como, a lógica pensada para a construção do Dataset de treinamento dos modelos de Machine Learning.

Além disso, toda a implementação foi feita usando **Python e bibliotecas**, tais como:

- **Feature Store:** [Feast](https://feast.dev/) — gerenciamento de features históricas e online.
- **Model Registry:** AWS S3 — armazenamento versionado de artefatos `.joblib`.
- **API:** FastAPI + Mangum — adaptador para AWS Lambda.
- **Infraestrutura:** Terraform (IaC).
- **Containerização:** Docker — imagem otimizada `linux/amd64` para AWS Lambda.
- **Modelagem:** Scikit-Learn — pipelines de pré-processamento e modelos de classificação.


### 📂 Estrutura do projeto

```
TC5-DATATHON-MAIN
├── .github/workflows/       # Automação de CI/CD (GitHub Actions)
│   └── ci-cd.yml            # Pipeline de integração e entrega contínua
├── feature_repo/            # Repositório do Feature Store (Feast)
│   ├── data/                # Armazenamento local de dados/parquets
│   ├── feature_definitions.py # Definição de entidades e visualizações de features
│   └── feature_store.yaml   # Configuração do ambiente do Feature Store
├── notebooks/               # Documentação exploratória e prototipagem
│   ├── EDA_DataPrep.ipynb   # Análise exploratória e preparação de dados
│   ├── Train.ipynb          # Experimentação de treinamento do modelo
│   └── Predict.ipynb        # Testes de inferência e validação
├── src/                     # Código-fonte da aplicação e do modelo
│   ├── api/                 # Endpoint de serviço (FastAPI)
│   │   └── main.py          # Script principal da API
│   └── training/            # Scripts de treinamento produtivo
│       └── train.py         # Lógica de treinamento e versionamento do modelo
├── terraform/               # Infraestrutura como Código (IaC) na AWS
│   ├── ecr.tf               # Repositório de imagens Docker (Elastic Container Registry)
│   ├── lambda.tf            # Configuração do processamento Serverless
│   ├── gateway.tf           # Configuração do API Gateway para acesso externo
│   └── mlflow.tf            # Infraestrutura para rastreamento de experimentos
├── tests/                   # Suíte de testes automatizados
│   ├── unit/                # Testes de funções e componentes isolados
│   └── integration/         # Testes de fluxo ponta a ponta (E2E)
├── Dockerfile               # Configuração da imagem para deploy do container
├── requirements.txt         # Dependências do projeto (Python)
└── README.md                # Documentação principal do projeto
```

## 🛠️ Pré-processamento e engenharia de features

Pipeline de Tratamento e Padronização

O processo de limpeza e normalização foi centralizado no notebook EDA_DataPrep.ipynb, envolvendo as seguintes operações:

- **Saneamento de Dados:** Implementação de funções baseadas em Regex para remoção de acentos e caracteres especiais, além da normalização de colunas de texto (como "Nome").
- **Tipagem e Codificação** Conversão de tipos primitivos para float e aplicação de técnicas de encoding para variáveis categóricas.
- **Governança de Colunas:** Utilização de mapeamento "de-para" para garantir a consistência das features entre diferentes anos letivos.
- **Otimização de Armazenamento:** Persistência dos dados em formato Parquet, otimizando a leitura colunar e reduzindo o consumo de memória durante o treinamento.

Análise Estatística e Seleção

Para validar a relevância das variáveis em relação ao alvo (EVASAO), foram aplicados métodos de análise de dependência:

- **Correlação de Pearson:** Utilizada para avaliar a relação linear entre as features numéricas.
- **Correlação Point-Biserial:** Aplicada para medir a associação entre variáveis contínuas e o target binário de evasão.

Governança com Feature Store (Feast)

Para garantir a consistência entre o treinamento e a inferência, implementamos um Feature Store utilizando a biblioteca Feast:

- **Feature View (aluno_features):** Centraliza as definições do esquema de dados, servindo como a "fonte da verdade" para o projeto.
- **Offline Store:** Utilizada pelo script train.py para recuperação de dados históricos de forma organizada.
- **Online Store:** Utilizada pelo predict.py para servir as features com baixa latência durante a inferência na API.
- **Arquivos de Configuração:** A implementação completa está disponível no diretório feature_repo/ através dos arquivos feature_store.yaml e feature_definitions.py.


## 🚀 Treinamento e experimentação de modelos


O processo de treinamento foi desenhado para ser robusto, auditável e automatizado, garantindo que o melhor modelo seja selecionado com base em dados de validação reais e não apenas em dados sintéticos.

## 1. Preparação e Balanceamento de Dados
Para lidar com o desbalanceamento inerente ao problema de evasão, o pipeline executa os seguintes passos:

- **Recuperação via Feast:** As features históricas são recuperadas do Feature Store utilizando o RA e a data de registro como chaves de entidade.
- **Separação de Validação Real:** Reservamos 10% dos dados originais (não balanceados) para compor um conjunto de Validação Real. Isso garante que a métrica final reflita o desempenho do modelo no cenário real da Associação.
- **Data Augmentation (SMOTE):** Aplicamos a técnica Synthetic Minority Over-sampling Technique para balancear as classes no conjunto de treino, gerando um dataset equilibrado de 10.000 registros (50% evasão / 50% permanência).

## 2. Ciclo de Experimentação (GridSearchCV)
Implementamos uma rotina de busca de hiperparâmetros para três diferentes algoritmos, buscando a melhor performance em F1-Score:

- **K-Nearest Neighbors (KNN):** Ajuste de vizinhos e pesos.
- **Regressão Logística:** Otimização de regularização (L1/L2) e penalidades.
- **Random Forest:** Ajuste de profundidade, número de árvores e amostras por folha.

## 3. Rastreamento e MLOps com MLflow
O projeto utiliza o MLflow para governança completa do ciclo de vida:

- **Tracking:** Registro automático de parâmetros, métricas de cada modelo e artefatos gerados.
- **Model Registry:** O melhor modelo é encapsulado em um Pipeline (contendo o scaler e o estimador) e registrado como um artefato pronto para produção.
- **Monitoramento de Data Drift:** Implementamos o cálculo do PSI (Population Stability Index). O pipeline compara a distribuição dos dados de treino (referência) com os de validação (atual) e gera um Painel de Drift HTML dentro do MLflow para alertar sobre mudanças no comportamento das features ao longo do tempo.

## 4. Persistência em Nuvem (AWS S3)
Após a validação, o melhor estimador é serializado com joblib e enviado automaticamente para um bucket no Amazon S3 (tc5-mlops-artifacts). Este artefato é o que será consumido pela API no momento do deploy, garantindo o desacoplamento entre o treinamento e a inferência.


## 🧪 Testes

Rodar testes unitários e de integração básica:

      pytest

Rodar testes com cobertura de código:

      pytest --cov=src --cov=feature_repo

Observações:

Os testes usam pytest e estão organizados em tests/unit e tests/integration.

## 📊 Monitoramento com MLflow

Para a rastreabilidade e governança do ciclo de vida do modelo, foi utilizado MLflow com registro de métricas, parâmetros e artefatos integrados com CloudWatch AWS, com isso registra a **predições e características** para monitoramento Real Time Data e Smoke.

**Etapas:**

1. **Configuração do tracking:** definir `MLFLOW_TRACKING_URI` e conectar o armazenamento de artefatos.
2. **Execução do treino:** iniciar o pipeline (`src/training/train.py`) para registrar hiperparâmetros, F1-score e o melhor pipeline treinado.
3. **Registro de drift:** publicar artefatos de monitoramento (`drift_panel.html` e `drift_summary.csv`)
4. **Acompanhamento contínuo:** abrir a UI do MLflow e validar runs, métricas de desempenho e sinais de desvio de distribuição. As métricas ficam em `Metrics` no run (`drift_avg_psi`, `drift_max_psi`, `drift_psi_<feature>`).

5. **Logs:** 
   - Coletados os logs no *CloudWatch Logs* no grupo
     `/aws/lambda/tc5-prediction-api`.
   - O Terraform provisiona o grupo com definição de retenção de 30 dias.

6. **Métricas customizadas**
   - A cada chamada ao endpoint `/predict` são enviados dados para o namespace
     `TC5/Model` (valor da predição e contagem) e `TC5/ModelFeatures`
     (valores de entrada) usando `cloudwatch.put_metric_data`.
   - Essas métricas permitem montar gráficos simples e detectar mudanças na
     distribuição ao longo do tempo.

3. **Dashboard de CloudWatch**
   - O `tc5-model-monitoring` com um widget para visualizar a média e o volume de
     previsões.
   -  `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
     name=tc5-model-monitoring`

**Ferramentas utilizadas:** MLflow,CloudWatch, Scikit-Learn, Python, AWS S3 (artefatos),IAM role.

**Link de acesso:** [evasao_experiment](http://tc5-mlflow-alb-936417363.us-east-1.elb.amazonaws.com/#/experiments/1/runs?searchFilter=&orderByKey=attributes.start_time&orderByAsc=false&startTime=ALL&lifecycleFilter=Active&modelVersionFilter=All+Runs&datasetsFilter=W10%3D)

## 📈 Observabilidade com Grafana

O monitoramento operacional da API é realizado com Grafana integrado com Loki e Promtail (via Docker Compose)

**Provisionamento:** criado infraestrutura com Terraform e habilitar o Grafana.

**Ferramentas utilizadas:** Grafana, Terraform,metrics e Logs Insights.
- Login Grafana OSS

**Link de acesso:** ([tc5-api-observability](http://localhost:3000/d/tc5-api-observability/tc5-api-observability?orgId=1&refresh=30s))

### Observabilidade via Docker Compose (Loki + Promtail)

Stack para monitorar logs da API em tempo real:

- `docker-compose.yml` com serviços `api`, `loki`, `promtail` e `grafana`
- `monitoring/loki/config.yaml`
- `monitoring/promtail/config.yaml`
- `monitoring/grafana/provisioning/datasources/datasource.yaml`
- `monitoring/grafana/provisioning/dashboards/dashboards.yaml`
- `monitoring/grafana/dashboards/tc5-api-observability.json`

#### Provisionar

1. Crie o arquivo de ambiente local com as credenciais mascaradas no repositório:

```bash
cp .env.example .env
```

2. `.env` com:
- `GRAFANA_ADMIN_PASSWORD`
- credenciais AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e opcionalmente `AWS_SESSION_TOKEN`) com acesso ao bucket de artefatos
- `ALLOW_STARTUP_WITHOUT_ARTIFACTS=false` para o endpoint `/predict` funcionar carregando modelo

3. Suba a stack:
```bash
docker compose up -d --build
```

O dashboard provisionado `TC5 API Observability` paineis 
- `Erros HTTP 503 (5m)`
- `Stream De Erros 503`
- `Latencia API`
- `Stream De logs`


## 📊 Resultados

O projeto consolidou um ecossistema **MLOps ponta a ponta**. No aspecto de modelagem, a combinação de janelas temporais com a técnica de balanceamento **SMOTE** e a otimização de hiperparâmetros (via `GridSearchCV`) resultou em um modelo classificador com **alto F1-Score**. A otimização desta métrica garante um equilíbrio ideal entre *Precision* e *Recall*, minimizando falsos positivos e maximizando a detecção de alunos com probabilidade real de evasão.

Do ponto de vista de arquitetura de produção e engenharia:
- **Inferência Escalável e de Baixa Latência:** O deploy via AWS Lambda com FastAPI e Docker garante que as predições ocorram em tempo real, cobrando apenas pelo tempo de computação estritamente utilizado.
- **Governança de Features:** A integração e centralização utilizando **Feast** (Feature Store) padroniza a entrega de informações tanto para treinamento quanto para inferência.
- **Monitoramento e Observabilidade:** O pipeline automatizado usando **MLflow** para detectar mudanças de distribuição (*Data Drift* via PSI) aliado ao **Grafana / CloudWatch** assegura visibilidade contínua sobre a saúde técnica e estatística da solução.

O resultado final não é apenas um modelo preditivo robusto; é uma ferramenta estratégica e sustentável que identifica rapidamente quem está em vulnerabilidade educacional. Isso otimiza o direcionamento de recursos da Passos Mágicos para onde eles são mais necessários: no futuro desses jovens. Transformamos dados em ação social.

## 🚀 Como Executar (Reprodução)

O projeto está configurado para deploy automático da infraestrutura via GitHub Actions usando Terraform. Abaixo o guia rápido para você executar via CI/CD no Mac ou Windows:

### 1. Clone o projeto

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd tc5-datathon
```

### 2. Crie as variáveis no GitHub Actions

O pipeline automatizado do GitHub necessita de credenciais de um usuário IAM com acesso administrador (ou permissões para Lambda, ECR, API Gateway, S3, IAM, CloudWatch).
Vá em `Settings > Secrets and variables > Actions > New repository secret` no GitHub e crie os seguintes "secrets":
- `AWS_ACCESS_KEY_ID`: Sua Access Key Account principal.
- `AWS_SECRET_ACCESS_KEY`: Sua Secret Key.

*(O deploy está por padrão apontando para a região `us-east-1` e os recursos ECS usam contas da região `sa-east-1` conforme script de infraestrutura.)*

### 3. Suba a Infraestrutura (Push para a nuvem ou roteamento local com `act`)

**Push para Branch Principal**
Faça push de qualquer atualização diretamente no GitHub:
```bash
git switch main
git push origin main
```
Isso acionará os jobs automatizados de Testes -> Treino (envio pro S3) -> Terraform (Criação Lambda + API).

### 4. Acesse o link (Swagger API)

Após a etapa do Actions ser concluída com sucesso (seja via web ou act local), o Terraform terá disponibilizado a URL do API Gateway. 
Você pode visualizá-la diretamente checando o painel do API Gateway na nuvem AWS, ou pelo console, através do output:

```bash
cd terraform
terraform output 
```

Encontre a URL base da API e acesse-a no navegador através da raiz terminada em `/docs` para abrir o Swagger Serverless (Exemplo: `https://[ID].execute-api.us-east-1.amazonaws.com/docs`). 



## Vídeo de Apresentação no Youtube (Modelo LSTM)
Para melhor compreensão da entrega , foi produzido um vídeo de apresentação no Youtube:

[Link para a Vídeo](https://link.com.br)


## ✒️ Autores

| Nome                            |   RM    | Link do GitHub                                      |
|---------------------------------|---------|-----------------------------------------------------|
| Ana Paula de Almeida            | 363602  | [GitHub](https://github.com/Ana9873P)               |
| Augusto do Nascimento Omena     | 363185  | [GitHub](https://github.com/AugustoOmena)           |
| Bruno Gabriel de Oliveira       | 361248  | [GitHub](https://github.com/brunogabrieldeoliveira) |
| José Walmir Gonçalves Duque     | 363196  | [GitHub](https://github.com/WALMIRDUQUE)            |

## 📄 Licença

Este projeto está licenciado sob a Licença MIT.  
Consulte o arquivo [license](docs/license/license.txt)  para mais detalhes.
