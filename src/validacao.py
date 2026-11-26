"""Validação cruzada temporal com janela expansiva (origem móvel).

Cada dobra prevê um mês usando só meses anteriores. Isso protege contra dois erros: (1) treinar com o futuro
e (2) escolher hiperparâmetros olhando para o conjunto de teste. A validação cruzada roda DENTRO do treino."""
import numpy as np
import pandas as pd

from src.config import COL_MES, MIN_MESES_TREINO_CV


def splits_expansivos(df: pd.DataFrame, min_meses_treino: int = MIN_MESES_TREINO_CV):
    """Lista de (idx_treino, idx_validacao) posicionais. Dobra k: treina nos meses 1..m_k-1 e valida em m_k."""
    meses = sorted(df[COL_MES].unique())
    if len(meses) <= min_meses_treino:
        raise ValueError(f"Meses insuficientes ({len(meses)}) para validação cruzada com mínimo de {min_meses_treino} no treino.")
    col = df[COL_MES].to_numpy()
    splits = []
    for k in range(min_meses_treino, len(meses)):
        idx_tr = np.flatnonzero(col < meses[k])
        idx_va = np.flatnonzero(col == meses[k])
        assert col[idx_tr].max() < col[idx_va].min()
        splits.append((idx_tr, idx_va))
    return splits


def descrever_splits(df: pd.DataFrame, splits) -> pd.DataFrame:
    col = df[COL_MES].to_numpy()
    linhas = []
    for i, (tr, va) in enumerate(splits, 1):
        linhas.append({"dobra": i, "treino_de": pd.Timestamp(col[tr].min()).strftime("%Y-%m"),
                       "treino_ate": pd.Timestamp(col[tr].max()).strftime("%Y-%m"),
                       "valida_em": pd.Timestamp(col[va].min()).strftime("%Y-%m"),
                       "linhas_treino": len(tr), "linhas_validacao": len(va)})
    return pd.DataFrame(linhas)
