"""Carga, limpeza, agregação e validação (etapas 1 a 6 do fluxo mínimo).

Formatos de entrada aceitos:
  (a) registros por exame: origem, data_chegada [, id_registro];
  (b) contagens mensais em formato longo: origem, mes, exames;
  (c) planilha larga (formato do arquivo do LAPAE): primeira coluna = origem e uma coluna por mês,
      com cabeçalhos como "Agosto(2025)"."""
import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.config import BRUTO, CHAVE, COL_ALVO, COL_DATA, COL_ID, COL_MES, COL_ORIGEM

MESES_PT = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
            "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
PADRAO_COLUNA_MES = re.compile(r"^\s*([A-Za-zçÇãÃéÉ]+)\s*\(\s*(\d{4})\s*\)\s*$")


def carregar_bruto(pasta: Path = BRUTO):
    """Lê todos os .csv e .xlsx de dados/bruto/ sem alterá-los. Devolve None se não houver arquivos."""
    arquivos = sorted(list(pasta.glob("*.csv")) + list(pasta.glob("*.xlsx")))
    if not arquivos:
        return None
    partes = []
    for a in arquivos:
        df = pd.read_csv(a) if a.suffix == ".csv" else pd.read_excel(a)
        df["arquivo_origem"] = a.name
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def normalizar_texto(s: pd.Series) -> pd.Series:
    """Remove espaços das pontas e duplicados, tira acentos e passa para maiúsculas."""
    def f(v):
        if pd.isna(v):
            return v
        v = unicodedata.normalize("NFKD", str(v))
        v = "".join(c for c in v if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", v).strip().upper()
    return s.map(f).astype("string")


def _registro(log, etapa, antes, depois, chave=None):
    item = {"etapa": etapa, "linhas_antes": len(antes), "linhas_depois": len(depois)}
    if chave is not None:
        item["chaves_unicas_antes"] = antes[chave].nunique(dropna=True)
        item["chaves_unicas_depois"] = depois[chave].nunique(dropna=True)
    log.append(item)


def _grade_completa(cont: pd.DataFrame) -> pd.DataFrame:
    """Monta a grade origem x mês. Mês sem registro fica NaN: ausência não é convertida em zero
    antes de o demandante explicar o que ela significa."""
    origens = cont[[COL_ORIGEM]].drop_duplicates()
    meses = pd.DataFrame({COL_MES: pd.date_range(cont[COL_MES].min(), cont[COL_MES].max(), freq="MS")})
    base = origens.merge(meses, how="cross").merge(cont, on=CHAVE, how="left", validate="one_to_one")
    return base.sort_values(CHAVE).reset_index(drop=True)


def limpar(df: pd.DataFrame):
    """Formato (a): normaliza texto, descarta datas inválidas e remove duplicatas por id_registro."""
    faltando = [c for c in (COL_ORIGEM, COL_DATA) if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes: {faltando}")
    log = []
    x = df.copy()
    antes = x
    x[COL_ORIGEM] = normalizar_texto(x[COL_ORIGEM])
    _registro(log, "normalizar origem", antes, x, COL_ORIGEM)
    antes = x
    x[COL_DATA] = pd.to_datetime(x[COL_DATA], errors="coerce")
    x = x[x[COL_DATA].notna() & x[COL_ORIGEM].notna()].copy()
    _registro(log, "descartar datas ou origens ausentes", antes, x, COL_ORIGEM)
    if COL_ID in x.columns:
        antes = x
        x = x.drop_duplicates(subset=[COL_ID], keep="first").copy()
        _registro(log, "remover duplicatas por id_registro", antes, x, COL_ID)
    return x.reset_index(drop=True), pd.DataFrame(log)


def agregar_mensal(df_limpo: pd.DataFrame) -> pd.DataFrame:
    """Formato (a) -> origem x mês."""
    x = df_limpo.copy()
    x[COL_MES] = x[COL_DATA].dt.to_period("M").dt.to_timestamp()
    cont = x.groupby(CHAVE).size().rename(COL_ALVO).reset_index()
    return _grade_completa(cont)


def padronizar_longo(df: pd.DataFrame):
    """Formato (b): contagens mensais já agregadas, uma linha por origem e mês."""
    faltando = [c for c in (COL_ORIGEM, COL_MES, COL_ALVO) if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes: {faltando}")
    x = df[[COL_ORIGEM, COL_MES, COL_ALVO]].copy()
    x[COL_ORIGEM] = normalizar_texto(x[COL_ORIGEM])
    x[COL_MES] = pd.to_datetime(x[COL_MES], errors="coerce").dt.to_period("M").dt.to_timestamp()
    x[COL_ALVO] = pd.to_numeric(x[COL_ALVO], errors="coerce")
    validas = x[COL_MES].notna() & x[COL_ORIGEM].notna()
    log = pd.DataFrame([{"etapa": "descartar mês ou origem ausentes", "linhas_antes": len(x), "linhas_depois": int(validas.sum())}])
    x = x[validas]
    cont = x.groupby(CHAVE)[COL_ALVO].sum(min_count=1).reset_index()
    return _grade_completa(cont), log, float(x[COL_ALVO].sum())


def _converter_coluna_mes(nome: str):
    m = PADRAO_COLUNA_MES.match(str(nome))
    if not m:
        return None
    mes = unicodedata.normalize("NFKD", m.group(1)).encode("ascii", "ignore").decode().lower()
    if mes not in MESES_PT:
        return None
    return pd.Timestamp(int(m.group(2)), MESES_PT[mes], 1)


def eh_planilha_larga(df: pd.DataFrame) -> bool:
    return sum(_converter_coluna_mes(c) is not None for c in df.columns) >= 2


def padronizar_largo(df: pd.DataFrame):
    """Formato (c): primeira coluna = origem; demais colunas = meses ("Agosto(2025)")."""
    primeira = df.columns[0]
    colunas_mes = {c: _converter_coluna_mes(c) for c in df.columns[1:] if _converter_coluna_mes(c) is not None}
    longo = df.melt(id_vars=[primeira], value_vars=list(colunas_mes), var_name="coluna", value_name=COL_ALVO)
    longo[COL_MES] = longo["coluna"].map(colunas_mes)
    longo = longo.rename(columns={primeira: COL_ORIGEM})
    longo = longo[longo[COL_ORIGEM].notna()]
    return padronizar_longo(longo[[COL_ORIGEM, COL_MES, COL_ALVO]])


def preparar_base_mensal(bruto: pd.DataFrame):
    """Escolhe o caminho conforme o formato. Devolve (base_mensal, log, total_de_exames_de_entrada)."""
    if eh_planilha_larga(bruto):
        return padronizar_largo(bruto)
    if COL_ALVO in bruto.columns and COL_DATA not in bruto.columns:
        return padronizar_longo(bruto)
    limpo, log = limpar(bruto)
    return agregar_mensal(limpo), log, float(len(limpo))


def validar_totais(total_entrada: float, base_mensal: pd.DataFrame) -> dict:
    """Compara o total que entrou na agregação com a soma da base mensal e a cobertura da grade."""
    soma = float(base_mensal[COL_ALVO].sum(skipna=True))
    return {
        "total_de_entrada": total_entrada,
        "soma_base_mensal": soma,
        "totais_conferem": abs(total_entrada - soma) < 1e-9,
        "celulas_grade": len(base_mensal),
        "celulas_ausentes": int(base_mensal[COL_ALVO].isna().sum()),
        "origens": base_mensal[COL_ORIGEM].nunique(),
        "meses": base_mensal[COL_MES].nunique(),
    }


def validar_esquema(base: pd.DataFrame) -> pd.DataFrame:
    """Verifica tipos, unidades, categorias e chaves da base mensal.
    Devolve uma tabela (verificação, ok, detalhe); o notebook interrompe se alguma falhar."""
    linhas = []

    def add(nome, ok, detalhe=""):
        linhas.append({"verificação": nome, "ok": bool(ok), "detalhe": detalhe})

    faltando = [c for c in (COL_ORIGEM, COL_MES, COL_ALVO) if c not in base.columns]
    add("colunas obrigatórias presentes", not faltando, f"faltando: {faltando}" if faltando else "")
    if faltando:
        return pd.DataFrame(linhas)
    add("mês é do tipo data", pd.api.types.is_datetime64_any_dtype(base[COL_MES]))
    add("mês é sempre o 1º dia do mês", bool((base[COL_MES].dt.day == 1).all()))
    add("exames é numérico", pd.api.types.is_numeric_dtype(base[COL_ALVO]))
    add("exames não é negativo", bool((base[COL_ALVO].dropna() >= 0).all()))
    add("exames é inteiro (quando presente)", bool((base[COL_ALVO].dropna() % 1 == 0).all()))
    dup = int(base.duplicated(CHAVE).sum())
    add("chave (origem, mês) é única", dup == 0, f"{dup} linhas repetidas")
    t = base[COL_ORIGEM].astype("string")
    add("origem sem espaços nas pontas", bool((t == t.str.strip()).all()))
    canon = normalizar_texto(t)
    add("origem sem grafias duplicadas", t.nunique() == canon.nunique(), f"{t.nunique()} grafias para {canon.nunique()} origens")
    meses = pd.date_range(base[COL_MES].min(), base[COL_MES].max(), freq="MS")
    add("meses consecutivos, sem buracos", base[COL_MES].nunique() == len(meses), f"{base[COL_MES].nunique()} de {len(meses)} meses")
    esperado = base[COL_ORIGEM].nunique() * base[COL_MES].nunique()
    add("grade completa origem × mês", len(base) == esperado, f"{len(base)} de {esperado} células")
    return pd.DataFrame(linhas)
