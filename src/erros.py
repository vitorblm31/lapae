"""Análise de erros: onde, em quem e quanto o modelo erra, e quais erros podem ser problema de dado."""
import numpy as np
import pandas as pd

from src.baseline import mae, vies, wape
from src.config import COL_ALVO, COL_MES, COL_MUNICIPIO, COL_UNIDADE


def _linha(g: pd.DataFrame) -> pd.Series:
    y, p = g[COL_ALVO].to_numpy(), g["previsto"].to_numpy()
    sub = np.clip(y - p, 0, None).sum()   # subestimou: faltou previsão -> falta de tempo
    sup = np.clip(p - y, 0, None).sum()   # superestimou: capacidade ociosa
    return pd.Series({"n": len(g), "MAE": mae(y, p), "WAPE": wape(y, p), "viés": vies(y, p),
                      "exames subestimados": sub, "exames superestimados": sup})


def por_faixa_do_escore(df: pd.DataFrame, previsto, n_faixas: int = 3) -> pd.DataFrame:
    """Em que faixa do escore (volume previsto) os erros se concentram."""
    x = df.assign(previsto=np.asarray(previsto, dtype=float))
    x["faixa do previsto"] = pd.qcut(x["previsto"], q=n_faixas, duplicates="drop", precision=0).astype(str)
    return x.groupby("faixa do previsto").apply(_linha, include_groups=False).reset_index()


def por_grupo(df: pd.DataFrame, previsto, coluna: str) -> pd.DataFrame:
    x = df.assign(previsto=np.asarray(previsto, dtype=float))
    return x.groupby(coluna).apply(_linha, include_groups=False).reset_index().sort_values("WAPE", ascending=False)


def casos_problematicos(df: pd.DataFrame, previsto, n: int = 8, salto_suspeito: float = 0.5) -> pd.DataFrame:
    """Maiores erros absolutos, com indício de causa: salto brusco frente ao mês anterior (dado ou evento real?)
    ou unidade/mês com pouco histórico. A causa só se confirma com o demandante [L]."""
    x = df.assign(previsto=np.asarray(previsto, dtype=float))
    x["erro"] = x["previsto"] - x[COL_ALVO]
    x["erro_abs"] = x["erro"].abs()
    x["variação real vs mês anterior"] = x[COL_ALVO] / x["lag_1"] - 1
    x["indício"] = np.where(x["variação real vs mês anterior"].abs() > salto_suspeito,
                            "salto brusco no real: checar registro/retificação (dado) ou evento real", "sem salto: erro do modelo")
    cols = [c for c in (COL_UNIDADE, COL_MUNICIPIO) if c in x.columns and x[c].notna().any()] + [COL_MES, COL_ALVO, "previsto", "erro", "lag_1", "variação real vs mês anterior", "indício"]
    return x.sort_values("erro_abs", ascending=False).head(n)[cols].reset_index(drop=True)


def problemas_de_dado(mensal: pd.DataFrame, descartadas_sem_historico: int) -> dict:
    """Quanto do universo ficou fora do modelo por causa do dado (não do algoritmo)."""
    return {"celulas_unidade_mes": int(len(mensal)),
            "celulas_sem_registro (NaN)": int(mensal[COL_ALVO].isna().sum()),
            "linhas_descartadas_sem_historico_ou_alvo": int(descartadas_sem_historico),
            "unidades_com_algum_mes_ausente": int(mensal.groupby(COL_UNIDADE)[COL_ALVO].apply(lambda s: s.isna().any()).sum())}
