"""Backtest com origem móvel: a cada origem k ajusta com os meses até k e prevê os h meses seguintes.
Serve para comparar abordagens em vários cortes, não só na partição única treino/validação/teste."""
import numpy as np
import pandas as pd

from src.baseline import prever_media_treino, prever_ultimo_valor
from src.config import COL_ALVO, COL_MES
from src.modelo import ModeloRelativo


def backtest(feats: pd.DataFrame, min_treino: int = 6, h_max: int = 3, alpha: float = 30.0) -> pd.DataFrame:
    """Devolve uma linha por (origem do corte, horizonte, abordagem) com o erro do TOTAL mensal e a
    soma dos erros absolutos por série (para o WAPE)."""
    meses = sorted(feats[COL_MES].unique())
    linhas = []
    for i in range(min_treino, len(meses)):
        treino = feats[feats[COL_MES].isin(meses[:i])]
        for h in range(1, h_max + 1):
            if i + h - 1 >= len(meses):
                break
            alvo = feats[feats[COL_MES] == meses[i + h - 1]]
            prev = {
                "média por origem": prever_media_treino(treino, alvo, "mean"),
                "mediana por origem": prever_media_treino(treino, alvo, "median"),
                "último valor": prever_ultimo_valor(treino, alvo),
                "Ridge relativo": ModeloRelativo(alpha=alpha).fit(treino, treino[COL_ALVO]).predict(alvo),
            }
            for nome, p in prev.items():
                p = np.asarray(p, dtype=float)
                linhas.append({"corte": i, "horizonte": h, "abordagem": nome,
                               "erro_total": float(p.sum() - alvo[COL_ALVO].sum()),
                               "erro_abs_series": float(np.abs(p - alvo[COL_ALVO].to_numpy()).sum()),
                               "real_total": float(alvo[COL_ALVO].sum())})
    return pd.DataFrame(linhas)


def resumo_backtest(bt: pd.DataFrame) -> pd.DataFrame:
    g = bt.groupby("abordagem")
    return pd.DataFrame({
        "MAE do total mensal": g["erro_total"].apply(lambda e: e.abs().mean()),
        "WAPE por origem": g["erro_abs_series"].sum() / g["real_total"].sum(),
        "viés do total (previsto - real)": g["erro_total"].mean(),
        "n previsões": g.size(),
    }).sort_values("MAE do total mensal")
