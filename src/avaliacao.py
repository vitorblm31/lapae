"""Métricas na mesma partição e conversão do ganho para unidade do demandante (exames por mês)."""
import numpy as np
import pandas as pd

from src.baseline import mae, vies, wape
from src.config import COL_ALVO, COL_MES


def metricas(y, p) -> dict:
    return {"MAE": mae(y, p), "WAPE": wape(y, p), "viés": vies(y, p)}


def totais_mensais(df: pd.DataFrame, previsto) -> pd.DataFrame:
    """Soma por mês do real e do previsto. Só faz sentido quando o mesmo conjunto de unidades está em todos os meses."""
    x = df[[COL_MES, COL_ALVO]].copy()
    x["previsto"] = np.asarray(previsto, dtype=float)
    t = x.groupby(COL_MES).sum().reset_index().rename(columns={COL_ALVO: "real"})
    t["erro"] = t["previsto"] - t["real"]
    t["erro_abs"] = t["erro"].abs()
    return t


def erro_total_medio(df: pd.DataFrame, previsto) -> float:
    """Erro absoluto médio do TOTAL mensal (exames/mês): é o erro que a decisão de capacidade sente."""
    return float(totais_mensais(df, previsto)["erro_abs"].mean())


def ganho_sobre_baseline(df: pd.DataFrame, prev_modelo, prev_base) -> dict:
    """Ganho em unidades do demandante: exames/mês de erro a menos, por unidade e no total mensal."""
    y = df[COL_ALVO].to_numpy()
    mae_m, mae_b = mae(y, prev_modelo), mae(y, prev_base)
    tot_m, tot_b = erro_total_medio(df, prev_modelo), erro_total_medio(df, prev_base)
    return {
        "mae_baseline": mae_b, "mae_modelo": mae_m,
        "reducao_relativa_mae": (mae_b - mae_m) / mae_b if mae_b else np.nan,
        "exames_por_unidade_mes_evitados": mae_b - mae_m,
        "erro_total_mes_baseline": tot_b, "erro_total_mes_modelo": tot_m,
        "exames_por_mes_no_total_evitados": tot_b - tot_m,
    }
