from feast import Entity, FeatureView, Field, FileSource, ValueType
from feast.types import Int64, Float32, String
from feast import FeatureService

aluno_schema = [
    Field(name="ANO_INGRESSO", dtype=Float32),
    Field(name="ATINGIU_PV", dtype=Float32),
    Field(name="CF", dtype=Float32),
    Field(name="CG", dtype=Float32),
    Field(name="CT", dtype=Float32),
    Field(name="DATA_NASCIMENTO", dtype=Float32),
    Field(name="DEFASAGEM", dtype=Float32),
    Field(name="DESTAQUE_IDA", dtype=Float32),
    Field(name="DESTAQUE_IEG", dtype=Float32),
    Field(name="DESTAQUE_IPV", dtype=Float32),
    Field(name="EVASAO", dtype=Float32),
    Field(name="FASE", dtype=Float32),
    Field(name="FASE_IDEAL", dtype=Float32),
    Field(name="GENERO", dtype=Float32),
    Field(name="IAA", dtype=Float32),
    Field(name="IAN", dtype=Float32),
    Field(name="IDA", dtype=Float32),
    Field(name="IDADE", dtype=Float32),
    Field(name="IEG", dtype=Float32),
    Field(name="INDE", dtype=Float32),
    Field(name="INDICADO", dtype=Float32),
    Field(name="INGLES", dtype=Float32),
    Field(name="INSTITUICAO_ENSINO", dtype=Float32),
    Field(name="IPS", dtype=Float32),
    Field(name="IPV", dtype=Float32),
    Field(name="MATEMATICA", dtype=Float32),
    Field(name="PEDRA", dtype=Float32),
    Field(name="PORTUGUES", dtype=Float32),
    Field(name="REC_PSICOLOGIA", dtype=Float32),
    Field(name="TURMA", dtype=Float32),
]

# Entity (chave do aluno)
aluno = Entity(
    name="aluno",
    join_keys=["RA"],
    value_type=ValueType.STRING,    
)

# Data source
aluno_source = FileSource(
    path="data/df_evasao_escolar.parquet",
    timestamp_field="DATA_REGISTRO",
)

# Feature View com Features para Train / Predict
aluno_features = FeatureView(
    name="aluno_features",
    entities=[aluno],
    schema=aluno_schema,
    source=aluno_source,
)

aluno_service = FeatureService(
    name="aluno_service",
    features=[aluno_features],
)