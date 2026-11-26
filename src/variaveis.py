"""Variáveis derivadas, construídas só com informação anterior ao mês-alvo (regra do corte)."""
import numpy as np
import pandas as pd

from src.config import COL_ALVO, COL_MES, COL_UNIDADE


def _dias_uteis(mes: pd.Timestamp) -> int:
    inicio = mes.to_datetime64().astype("datetime64[D]")
    fim = (mes + pd.offsets.MonthBegin(1)).to_datetime64().astype("datetime64[D]")
    return int(np.busday_count(inicio, fim))  # sem feriados; refinar quando houver calendário local


def criar_variaveis(base: pd.DataFrame, n_lags: int = 3):
    """Cria defasagens 1..n, média móvel dos 3 meses anteriores, mês do ano e dias úteis.

    Todas usam apenas meses anteriores ao mês-alvo (shift antes de qualquer janela).
    Devolve (base_com_variaveis, n_linhas_sem_historico), em que o segundo valor é o
    número de linhas descartadas por não terem passado suficiente."""
    x = base.sort_values([COL_UNIDADE, COL_MES]).reset_index(drop=True).copy()
    g = x.groupby(COL_UNIDADE)[COL_ALVO]
    for k in range(1, n_lags + 1):
        x[f"lag_{k}"] = g.shift(k)
    x["media_movel_3"] = g.transform(lambda s: s.shift(1).rolling(3, min_periods=3).mean())
    x["mes_do_ano"] = x[COL_MES].dt.month.astype(str)
    x["dias_uteis"] = x[COL_MES].map(_dias_uteis)
    exigidas = [f"lag_{k}" for k in range(1, n_lags + 1)] + ["media_movel_3"]
    completos = x[exigidas].notna().all(axis=1) & x[COL_ALVO].notna()
    return x[completos].reset_index(drop=True), int((~completos).sum())
