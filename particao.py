"""Partição temporal: treino no passado, validação e teste em meses posteriores, sem sobreposição."""
import pandas as pd

from src.config import COL_MES, N_MESES_TESTE, N_MESES_VALIDACAO


def particionar_temporal(df: pd.DataFrame, n_validacao: int = N_MESES_VALIDACAO, n_teste: int = N_MESES_TESTE):
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
