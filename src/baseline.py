"""Baselines e métricas iniciais. Todo ajuste usa apenas o conjunto de treino."""
import numpy as np
import pandas as pd

from src.config import COL_ALVO, COL_UNIDADE


def mae(y, p):
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(p))))


def wape(y, p):
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    return float(np.abs(y - p).sum() / y.sum())


def vies(y, p):
    """Erro médio com sinal (previsto - real). Positivo = superestima; negativo = subestima."""
    return float(np.mean(np.asarray(p) - np.asarray(y)))


def prever_persistencia(valid: pd.DataFrame) -> pd.Series:
    """Baseline operacional (hipótese): o mês repete o mês anterior da mesma unidade."""
    return valid["lag_1"]


def prever_estatistica_treino(treino: pd.DataFrame, valid: pd.DataFrame, funcao="mean") -> pd.Series:
    """Média ou mediana do treino por unidade; unidade ausente no treino recebe a estatística global."""
    por_unidade = treino.groupby(COL_UNIDADE)[COL_ALVO].agg(funcao)
    global_ = getattr(treino[COL_ALVO], funcao)()
    return valid[COL_UNIDADE].map(por_unidade).fillna(global_)


def prever_media_movel(valid: pd.DataFrame) -> pd.Series:
    return valid["media_movel_3"]


def avaliar_baselines(treino: pd.DataFrame, valid: pd.DataFrame) -> pd.DataFrame:
    previsoes = {
        "Persistência (operacional)": prever_persistencia(valid),
        "Média do treino": prever_estatistica_treino(treino, valid, "mean"),
        "Mediana do treino": prever_estatistica_treino(treino, valid, "median"),
        "Média móvel de 3 meses": prever_media_movel(valid),
    }
    y = valid[COL_ALVO]
    linhas = [{"baseline": n, "MAE": mae(y, p), "WAPE": wape(y, p), "viés": vies(y, p)} for n, p in previsoes.items()]
    return pd.DataFrame(linhas)
