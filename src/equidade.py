"""Verificação de equidade entre grupos relevantes.

Aqui os grupos são unidades, municípios e porte da unidade (volume típico no treino). O modelo prevê volume e orienta
a alocação de tempo de uma equipe finita; subestimar sistematicamente um grupo significa que o trabalho dele fica
para trás primeiro. Os dados são agregados (sem pacientes): a equidade é entre origens do exame, não entre pessoas."""
import numpy as np
import pandas as pd

from src.baseline import mae, vies, wape
from src.config import (COL_ALVO, COL_MUNICIPIO, COL_UNIDADE, LIMITE_RAZAO_WAPE_GRUPOS, MIN_LINHAS_GRUPO)


def classificar_porte(treino: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
    """Porte por tercil do volume médio da unidade NO TREINO (sem olhar o futuro). Unidade sem treino fica 'sem histórico'."""
    media = treino.groupby(COL_UNIDADE)[COL_ALVO].mean()
    cortes = media.quantile([1 / 3, 2 / 3]).to_numpy()
    def f(u):
        if u not in media.index:
            return "sem histórico"
        v = media[u]
        return "pequena" if v <= cortes[0] else ("média" if v <= cortes[1] else "grande")
    return df[COL_UNIDADE].map(f)


def desempenho_por_grupo(df: pd.DataFrame, previsto, grupo: pd.Series, nome: str) -> pd.DataFrame:
    x = df.assign(previsto=np.asarray(previsto, dtype=float), grupo=grupo.to_numpy())
    linhas = []
    for g, d in x.groupby("grupo"):
        y, p = d[COL_ALVO].to_numpy(), d["previsto"].to_numpy()
        linhas.append({"critério": nome, "grupo": g, "n": len(d), "WAPE": wape(y, p), "MAE": mae(y, p),
                       "viés": vies(y, p), "viés relativo": vies(y, p) / y.mean() if y.mean() else np.nan,
                       "amostra pequena": len(d) < MIN_LINHAS_GRUPO})
    return pd.DataFrame(linhas)


def resumo_de_diferenca(tabela: pd.DataFrame, limite: float = LIMITE_RAZAO_WAPE_GRUPOS) -> dict:
    t = tabela[~tabela["amostra pequena"]]
    if len(t) < 2:
        return {"conclusao": "grupos insuficientes ou amostra pequena demais para comparar", "razao_wape": np.nan}
    pior, melhor = t.loc[t["WAPE"].idxmax()], t.loc[t["WAPE"].idxmin()]
    razao = pior["WAPE"] / melhor["WAPE"] if melhor["WAPE"] > 0 else np.inf
    return {"pior_grupo": pior["grupo"], "melhor_grupo": melhor["grupo"], "wape_pior": float(pior["WAPE"]),
            "wape_melhor": float(melhor["WAPE"]), "razao_wape": float(razao),
            "diferenca_pontos_percentuais": float((pior["WAPE"] - melhor["WAPE"]) * 100),
            "sinalizado": bool(razao > limite),
            "conclusao": ("diferença acima do limite combinado [H]: reportar e discutir com o demandante" if razao > limite
                          else "diferença dentro do limite combinado [H]")}
