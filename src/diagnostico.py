"""Diagnóstico de resíduos: olhar além da média."""
import numpy as np
import pandas as pd

from src.config import COL_ALVO, COL_MES, COL_ORIGEM


def residuos(df: pd.DataFrame, previsto) -> pd.DataFrame:
    r = df[[COL_ORIGEM, COL_MES, COL_ALVO]].copy()
    r["previsto"] = np.asarray(previsto, dtype=float)
    r["residuo"] = r[COL_ALVO] - r["previsto"]  # real - previsto: positivo = modelo subestimou
    return r


def resumo_por(res: pd.DataFrame, coluna: str) -> pd.DataFrame:
    g = res.groupby(coluna)["residuo"]
    return pd.DataFrame({"n": g.size(), "residuo_medio": g.mean(), "residuo_abs_medio": res.assign(a=res["residuo"].abs()).groupby(coluna)["a"].mean()})


def autocorrelacao_total_mensal(res: pd.DataFrame):
    """Autocorrelação de ordem 1 dos resíduos do total mensal (None se houver menos de 4 meses)."""
    total = res.groupby(COL_MES)["residuo"].sum().sort_index()
    if len(total) < 4:
        return None
    return float(total.autocorr(lag=1))


def maiores_residuos(res: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    return res.reindex(res["residuo"].abs().sort_values(ascending=False).index).head(n)
