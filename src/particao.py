"""Partição temporal e validação cruzada por origem móvel, sempre separando por mês inteiro."""
import numpy as np
import pandas as pd

from src.config import COL_MES, N_MESES_TESTE, N_MESES_VALIDACAO


def particionar_temporal(df: pd.DataFrame, n_validacao: int = N_MESES_VALIDACAO, n_teste: int = N_MESES_TESTE):
    """Treino no passado; validação e teste em meses posteriores, sem sobreposição."""
    meses = sorted(df[COL_MES].unique())
    if len(meses) <= n_validacao + n_teste:
        raise ValueError(f"Meses insuficientes ({len(meses)}) para validação={n_validacao} e teste={n_teste}.")
    m_teste = meses[-n_teste:]
    m_valid = meses[-(n_teste + n_validacao):-n_teste]
    m_treino = meses[:-(n_teste + n_validacao)]
    treino = df[df[COL_MES].isin(m_treino)].copy()
    valid = df[df[COL_MES].isin(m_valid)].copy()
    teste = df[df[COL_MES].isin(m_teste)].copy()
    assert treino[COL_MES].max() < valid[COL_MES].min() <= valid[COL_MES].max() < teste[COL_MES].min()
    return treino, valid, teste


def splits_por_mes(df: pd.DataFrame, n_splits: int = 2, min_meses_treino: int = 3):
    """Origem móvel: cada dobra treina com os meses até k e valida no mês k+1. Devolve índices
    posicionais de `df` (que deve ter índice 0..n-1), compatíveis com GridSearchCV(cv=...)."""
    meses = sorted(df[COL_MES].unique())
    if len(meses) < min_meses_treino + 1:
        raise ValueError("Meses insuficientes para validação cruzada temporal.")
    ultimos = meses[-n_splits:] if len(meses) - n_splits >= min_meses_treino else meses[min_meses_treino:]
    pos = np.arange(len(df))
    mes = df[COL_MES].to_numpy()
    return [(pos[mes < m], pos[mes == m]) for m in ultimos]
