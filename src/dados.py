"""Carga, limpeza, agregação e validação de contagens (etapas 1 a 6 do fluxo mínimo)."""
from pathlib import Path

import pandas as pd

from src.config import (BRUTO, COL_DATA, COL_ID, COL_MES, COL_MUNICIPIO, COL_ALVO,
                        COL_UNIDADE)

COLUNAS_OBRIGATORIAS = [COL_UNIDADE, COL_MUNICIPIO, COL_DATA]


def carregar_bruto(pasta: Path = BRUTO):
    """Lê todos os .csv e .xlsx de dados/bruto/ sem alterá-los. Devolve None se não houver arquivos.

    ATENÇÃO: o formato real dos relatórios do demandante ainda não é conhecido. Quando eles
    chegarem, ajustar o mapeamento de colunas aqui e registrar em docs/dicionario_dados.md."""
    arquivos = sorted(list(pasta.glob("*.csv")) + list(pasta.glob("*.xlsx")))
    if carregar_mensal_agregado(pasta) is not None:  # planilha já agregada por mês: usar carregar_mensal_agregado
        return None
    if not arquivos:
        return None
    partes = []
    for a in arquivos:
        df = pd.read_csv(a) if a.suffix == ".csv" else pd.read_excel(a)
        df["arquivo_origem"] = a.name
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def _registro(log, etapa, antes, depois, chave=None):
    item = {"etapa": etapa, "linhas_antes": len(antes), "linhas_depois": len(depois)}
    if chave is not None:
        item["chaves_unicas_antes"] = antes[chave].nunique(dropna=True)
        item["chaves_unicas_depois"] = depois[chave].nunique(dropna=True)
    log.append(item)


def limpar(df: pd.DataFrame):
    """Normaliza unidade e data, remove duplicatas por id_registro e datas inválidas.
    Devolve (df_limpo, log), com contagens e chaves únicas antes e depois de cada etapa."""
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes: {faltando}")
    log = []
    x = df.copy()

    antes = x
    x[COL_UNIDADE] = x[COL_UNIDADE].astype("string").str.strip().str.title()
    x[COL_MUNICIPIO] = x[COL_MUNICIPIO].astype("string").str.strip().str.title()
    _registro(log, "normalizar unidade e município", antes, x, COL_UNIDADE)

    antes = x
    x[COL_DATA] = pd.to_datetime(x[COL_DATA], errors="coerce")
    x = x[x[COL_DATA].notna()].copy()
    _registro(log, "descartar datas inválidas ou ausentes", antes, x, COL_UNIDADE)

    if COL_ID in x.columns:
        antes = x
        x = x.drop_duplicates(subset=[COL_ID], keep="first").copy()
        _registro(log, "remover duplicatas por id_registro", antes, x, COL_ID)

    return x.reset_index(drop=True), pd.DataFrame(log)


def agregar_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega para unidade x mês e monta a grade completa. Mês sem registro fica NaN
    (ausência não é convertida em zero antes de o demandante explicar o que ela significa)."""
    x = df.copy()
    x[COL_MES] = x[COL_DATA].dt.to_period("M").dt.to_timestamp()
    cont = x.groupby([COL_UNIDADE, COL_MES]).size().rename(COL_ALVO).reset_index()
    meses = pd.date_range(cont[COL_MES].min(), cont[COL_MES].max(), freq="MS")
    unidades = sorted(cont[COL_UNIDADE].unique())
    grade = pd.MultiIndex.from_product([unidades, meses], names=[COL_UNIDADE, COL_MES]).to_frame(index=False)
    base = grade.merge(cont, on=[COL_UNIDADE, COL_MES], how="left")
    cad = df[[COL_UNIDADE, COL_MUNICIPIO]].drop_duplicates(subset=[COL_UNIDADE])
    base = base.merge(cad, on=COL_UNIDADE, how="left", validate="many_to_one")
    return base


def validar_totais(df_limpo: pd.DataFrame, base_mensal: pd.DataFrame) -> dict:
    """Compara o total de registros limpos com a soma da base mensal e a cobertura da grade."""
    total_registros = len(df_limpo)
    soma_mensal = int(base_mensal[COL_ALVO].sum(skipna=True))
    return {
        "registros_limpos": total_registros,
        "soma_base_mensal": soma_mensal,
        "totais_conferem": total_registros == soma_mensal,
        "celulas_grade": len(base_mensal),
        "celulas_ausentes": int(base_mensal[COL_ALVO].isna().sum()),
        "unidades": base_mensal[COL_UNIDADE].nunique(),
        "meses": base_mensal[COL_MES].nunique(),
        "unidades_sem_municipio": int(base_mensal[COL_MUNICIPIO].isna().sum()),
    }


# ---- Relatório já agregado: planilha larga (uma linha por unidade/segmento, uma coluna por mês) ----
_MESES_PT = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
             "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def _mes_de_cabecalho(txt):
    """'Agosto(2025)' -> Timestamp('2025-08-01'); devolve None se não for um mês."""
    import re
    m = re.match(r"\s*([A-Za-zÀ-ÿ]+)\s*\(?\s*(\d{4})\s*\)?\s*$", str(txt))
    if not m or m.group(1).lower() not in _MESES_PT:
        return None
    return pd.Timestamp(year=int(m.group(2)), month=_MESES_PT[m.group(1).lower()], day=1)


def carregar_mensal_agregado(pasta: Path = BRUTO):
    """Lê planilhas .xlsx em formato largo (linhas = unidade ou segmento; colunas = 'Mês(ano)') e devolve a base
    longa (unidade, mes, exames, municipio) já na grade completa. Devolve None se não houver planilha nesse formato.
    Não altera o arquivo original. O município não vem nessa planilha: fica ausente (NaN) [L]."""
    for a in sorted(pasta.glob("*.xlsx")):
        df = pd.read_excel(a, index_col=0)
        meses = {c: _mes_de_cabecalho(c) for c in df.columns}
        if not meses or any(v is None for v in meses.values()):
            continue
        longo = (df.rename(columns=meses).rename_axis(COL_UNIDADE).reset_index()
                 .melt(id_vars=COL_UNIDADE, var_name=COL_MES, value_name=COL_ALVO))
        longo[COL_UNIDADE] = longo[COL_UNIDADE].astype("string").str.strip()
        longo[COL_MES] = pd.to_datetime(longo[COL_MES])
        longo[COL_ALVO] = pd.to_numeric(longo[COL_ALVO], errors="coerce")
        longo[COL_MUNICIPIO] = pd.NA
        longo = longo.sort_values([COL_UNIDADE, COL_MES]).reset_index(drop=True)
        longo.attrs["arquivo_origem"] = a.name
        longo.attrs["total_planilha"] = float(df.sum(numeric_only=True).sum())
        return longo[[COL_UNIDADE, COL_MES, COL_ALVO, COL_MUNICIPIO]]
    return None
