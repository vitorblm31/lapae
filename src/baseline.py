"""Baselines e métricas. Todo ajuste usa apenas o conjunto de treino.

Métrica principal: MAE do total mensal (soma de todas as séries em cada mês), em exames, porque a
decisão de capacidade do laboratório é tomada sobre o volume total. Secundárias: WAPE por série e
viés do total mensal (previsto - real; negativo = subestima)."""
import numpy as np
import pandas as pd

from src.config import COL_ALVO, COL_MES, COL_ORIGEM


def mae(y, p):
    return float(np.mean(np.abs(np.asarray(y, dtype=float) - np.asarray(p, dtype=float))))


def wape(y, p):
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    return float(np.abs(y - p).sum() / y.sum())


def vies(y, p):
    return float(np.mean(np.asarray(p, dtype=float) - np.asarray(y, dtype=float)))


def prever_media_treino(treino: pd.DataFrame, alvo_df: pd.DataFrame, funcao="mean") -> pd.Series:
    """Baseline trivial: média (ou mediana) do treino por série; série nova recebe a estatística global."""
    por_serie = treino.groupby(COL_ORIGEM)[COL_ALVO].agg(funcao)
    global_ = getattr(treino[COL_ALVO], funcao)()
    return alvo_df[COL_ORIGEM].map(por_serie).fillna(global_).astype(float)


def prever_ultimo_valor(treino: pd.DataFrame, alvo_df: pd.DataFrame) -> pd.Series:
    """Baseline operacional (hipótese): todo mês futuro repete o último mês observado da série."""
    ordenado = treino.sort_values([COL_ORIGEM, COL_MES])
    ultimo = ordenado.groupby(COL_ORIGEM)[COL_ALVO].last()
    return alvo_df[COL_ORIGEM].map(ultimo).fillna(treino[COL_ALVO].mean()).astype(float)


def tabela_metricas(alvo_df: pd.DataFrame, previsoes: dict) -> pd.DataFrame:
    """Mesma partição, mesmas linhas e mesmas métricas para todas as abordagens."""
    linhas = []
    for nome, p in previsoes.items():
        d = alvo_df[[COL_MES, COL_ALVO]].copy()
        d["previsto"] = np.asarray(p, dtype=float)
        total = d.groupby(COL_MES)[[COL_ALVO, "previsto"]].sum()
        linhas.append({
            "abordagem": nome,
            "MAE do total mensal (principal)": mae(total[COL_ALVO], total["previsto"]),
            "WAPE por série (secundária)": wape(d[COL_ALVO], d["previsto"]),
            "viés do total mensal": vies(total[COL_ALVO], total["previsto"]),
        })
    return pd.DataFrame(linhas)
