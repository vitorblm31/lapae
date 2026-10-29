"""Variáveis conhecidas de antemão: dependem só da origem e do calendário, nunca do alvo.

Como a previsão é feita 11 a 15 meses à frente (agosto a dezembro de 2027, a partir do último mês
observado), defasagens do alvo não existem para os meses-alvo. Por isso o modelo usa tendência,
calendário e identificação da origem."""
import numpy as np
import pandas as pd

from src.config import COL_ALVO, COL_MES, COL_ORIGEM


def _dias_uteis(mes: pd.Timestamp) -> int:
    inicio = mes.to_datetime64().astype("datetime64[D]")
    fim = (mes + pd.offsets.MonthBegin(1)).to_datetime64().astype("datetime64[D]")
    return int(np.busday_count(inicio, fim))  # sem feriados; refinar com calendário local


def criar_variaveis(base: pd.DataFrame, mes_inicial=None, descartar_sem_alvo=True):
    """Cria tendência (meses desde o início da série), mês do ano e dias úteis.
    Devolve (base_com_variaveis, n_linhas_sem_alvo). `mes_inicial` fixa a origem da tendência,
    para que meses futuros usem a mesma escala do treino."""
    x = base.sort_values([COL_ORIGEM, COL_MES]).reset_index(drop=True).copy()
    m0 = pd.Timestamp(mes_inicial) if mes_inicial is not None else x[COL_MES].min()
    x["tendencia"] = (x[COL_MES].dt.year - m0.year) * 12 + (x[COL_MES].dt.month - m0.month)
    x["mes_do_ano"] = x[COL_MES].dt.month.astype(str)
    x["dias_uteis"] = x[COL_MES].map(_dias_uteis)
    sem_alvo = int(x[COL_ALVO].isna().sum()) if COL_ALVO in x.columns else 0
    if descartar_sem_alvo and COL_ALVO in x.columns:
        x = x[x[COL_ALVO].notna()].reset_index(drop=True)
    return x, sem_alvo


def meses_futuros(base: pd.DataFrame, meses_alvo) -> pd.DataFrame:
    """Grade origem x mês-alvo (alvo desconhecido) para os meses pedidos."""
    meses = pd.DataFrame({COL_MES: pd.to_datetime(list(meses_alvo))})
    origens = base[[COL_ORIGEM]].drop_duplicates()
    grade = origens.merge(meses, how="cross")
    grade[COL_ALVO] = np.nan
    x, _ = criar_variaveis(grade, mes_inicial=base[COL_MES].min(), descartar_sem_alvo=False)
    return x
