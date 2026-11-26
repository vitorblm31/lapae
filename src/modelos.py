"""Modelos candidatos, grades de hiperparâmetros e busca por validação cruzada temporal.

Família        | O que minimiza                                            | O que os hiperparâmetros controlam
Ridge          | soma dos erros quadráticos + alfa * soma dos coef. quadrados | alfa: quanto encolher os coeficientes (variância x viés)
Árvore         | impureza (erro quadrático) em cada divisão               | profundidade e tamanho mínimo da folha: complexidade
Random forest  | erro quadrático de cada árvore; média reduz variância    | profundidade, folha mínima, variáveis por divisão
Gradient boost | erro quadrático, corrigindo resíduos passo a passo       | nº de árvores, taxa de aprendizado, profundidade
"""
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV
from sklearn.tree import DecisionTreeRegressor

from src.config import CATEGORICAS, COL_ALVO, NUMERICAS, SEMENTE
from src.preprocessamento import construir_pipeline
from src.validacao import splits_expansivos

COLUNAS = NUMERICAS + CATEGORICAS


def candidatos(semente: int = SEMENTE) -> dict:
    """Nome -> (estimador, grade, escalar, descrição do que minimiza)."""
    return {
        "Linear (Ridge)": (
            Ridge(random_state=semente),
            {"modelo__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
            True, "erro quadrático + penalização L2 dos coeficientes"),
        "Árvore de decisão": (
            DecisionTreeRegressor(random_state=semente),
            {"modelo__max_depth": [2, 3, 4, 6], "modelo__min_samples_leaf": [2, 5, 10]},
            False, "erro quadrático (impureza) em cada divisão"),
        "Random forest": (
            RandomForestRegressor(n_estimators=200, random_state=semente, n_jobs=1),
            {"modelo__max_depth": [3, 6, None], "modelo__min_samples_leaf": [2, 5], "modelo__max_features": [0.5, 1.0]},
            False, "erro quadrático por árvore; a média das árvores reduz a variância"),
        "Gradient boosting": (
            GradientBoostingRegressor(random_state=semente),
            {"modelo__n_estimators": [100, 300], "modelo__learning_rate": [0.03, 0.1], "modelo__max_depth": [2, 3]},
            False, "erro quadrático, corrigindo os resíduos das árvores anteriores"),
    }


def buscar(nome: str, treino: pd.DataFrame, semente: int = SEMENTE, colunas=None):
    """Escolhe hiperparâmetros por validação cruzada temporal DENTRO do treino (métrica: MAE).
    Devolve (busca_ajustada, tempo_da_busca_em_segundos)."""
    est, grade, escalar, _ = candidatos(semente)[nome]
    cols = colunas or COLUNAS
    num = [c for c in NUMERICAS if c in cols]
    cat = [c for c in CATEGORICAS if c in cols]
    pipe = construir_pipeline(est, num, cat, escalar=escalar)
    treino = treino.reset_index(drop=True)
    busca = GridSearchCV(pipe, grade, cv=splits_expansivos(treino), scoring="neg_mean_absolute_error",
                         refit=True, n_jobs=1)
    t0 = time.perf_counter()
    busca.fit(treino[cols], treino[COL_ALVO])
    return busca, time.perf_counter() - t0


def previsoes_fora_da_amostra(melhor_pipeline, treino: pd.DataFrame, colunas=None) -> pd.DataFrame:
    """Previsões da validação cruzada temporal (cada mês previsto sem ter sido visto) com os melhores hiperparâmetros.
    Usadas para estimar a dispersão do erro, sem tocar na validação nem no teste."""
    from sklearn.base import clone
    cols = colunas or COLUNAS
    treino = treino.reset_index(drop=True)
    partes = []
    for tr, va in splits_expansivos(treino):
        m = clone(melhor_pipeline).fit(treino.loc[tr, cols], treino.loc[tr, COL_ALVO])
        d = treino.loc[va].copy()
        d["previsto"] = m.predict(treino.loc[va, cols])
        partes.append(d)
    return pd.concat(partes, ignore_index=True)


def tempo_de_previsao(pipeline, X: pd.DataFrame, repeticoes: int = 20) -> float:
    t0 = time.perf_counter()
    for _ in range(repeticoes):
        pipeline.predict(X)
    return (time.perf_counter() - t0) / repeticoes
