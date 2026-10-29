"""Pré-processador dentro de um Pipeline: tudo é ajustado (fit) só no treino."""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import CATEGORICAS, NUMERICAS


def construir_preprocessador(numericas=None, categoricas=None) -> ColumnTransformer:
    numericas = numericas or NUMERICAS
    categoricas = categoricas or CATEGORICAS
    num = Pipeline([("imputacao", SimpleImputer(strategy="median")), ("escala", StandardScaler())])
    cat = OneHotEncoder(handle_unknown="ignore")  # categoria nova no teste vira vetor zerado
    return ColumnTransformer([("num", num, numericas), ("cat", cat, categoricas)], remainder="drop")


def construir_pipeline(modelo, numericas=None, categoricas=None) -> Pipeline:
    return Pipeline([("pre", construir_preprocessador(numericas, categoricas)), ("modelo", modelo)])


def resumo_do_fit(preprocessador: ColumnTransformer) -> dict:
    """O que o fit aprendeu no treino: medianas, médias, desvios e categorias."""
    num = preprocessador.named_transformers_["num"]
    cat = preprocessador.named_transformers_["cat"]
    return {
        "medianas": num.named_steps["imputacao"].statistics_.tolist(),
        "medias": num.named_steps["escala"].mean_.tolist(),
        "desvios": num.named_steps["escala"].scale_.tolist(),
        "categorias": {c: list(v) for c, v in zip(cat.feature_names_in_, cat.categories_)},
    }
