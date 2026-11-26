"""Testes da Entrega 6 com dados SINTÉTICOS. Verificam o código (validação, limiar, equidade), não os dados do projeto."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.config import COL_ALVO, COL_MES, COL_UNIDADE  # noqa: E402
from src.dados import agregar_mensal, limpar  # noqa: E402
from src.demo import gerar_registros_sinteticos  # noqa: E402
from src.equidade import classificar_porte, desempenho_por_grupo, resumo_de_diferenca  # noqa: E402
from src.limiar import limiar_efetivo, limiar_otimo, previsto_limiar_em_exames, prob_estouro  # noqa: E402
from src.modelos import candidatos  # noqa: E402
from src.particao import particionar_temporal  # noqa: E402
from src.validacao import splits_expansivos  # noqa: E402
from src.variaveis import criar_variaveis  # noqa: E402


@pytest.fixture(scope="module")
def partes():
    limpo, _ = limpar(gerar_registros_sinteticos())
    feats, _ = criar_variaveis(agregar_mensal(limpo))
    return particionar_temporal(feats)


def test_cv_so_dentro_do_treino_e_sem_olhar_o_futuro(partes):
    treino, valid, teste = (d.reset_index(drop=True) for d in partes)
    splits = splits_expansivos(treino)
    assert len(splits) >= 2
    for tr, va in splits:
        assert treino.loc[tr, COL_MES].max() < treino.loc[va, COL_MES].min()
        assert treino.loc[va, COL_MES].max() <= treino[COL_MES].max()
        assert treino.loc[va, COL_MES].max() < valid[COL_MES].min() < teste[COL_MES].min()


def test_cv_falha_com_poucos_meses(partes):
    treino = partes[0][partes[0][COL_MES] <= partes[0][COL_MES].min()]
    with pytest.raises(ValueError):
        splits_expansivos(treino)


def test_limiar_otimo_formula():
    assert limiar_otimo(2, 1) == pytest.approx(1 / 3)
    assert limiar_otimo(1, 1) == 0.5
    assert limiar_otimo(1, 4) == pytest.approx(0.8)
    with pytest.raises(ValueError):
        limiar_otimo(0, 1)


def test_limiar_em_exames_coerente_com_probabilidade():
    k, sigma = 1850, 60
    for t in (0.2, 0.5, 0.8):
        mu = previsto_limiar_em_exames(k, sigma, t)
        assert prob_estouro([mu], k, sigma)[0] == pytest.approx(t, abs=1e-6)
    assert limiar_efetivo(k, sigma, 0.2, 1900)["restricao_que_morde_primeiro"].startswith("econômica")
    assert limiar_efetivo(k, sigma, 0.8, 1900)["restricao_que_morde_primeiro"].startswith("capacidade")


def test_hiperparametros_e_candidatos_cobrem_as_tres_familias():
    nomes = " ".join(candidatos())
    assert "Ridge" in nomes and "Árvore" in nomes and ("forest" in nomes or "boosting" in nomes)
    for _, (_, grade, _, minimiza) in candidatos().items():
        assert grade and minimiza


def test_equidade_porte_usa_so_o_treino(partes):
    treino, valid, teste = partes
    porte = classificar_porte(treino, teste)
    assert set(porte.unique()) <= {"pequena", "média", "grande", "sem histórico"}
    inedita = teste.copy()
    inedita.loc[inedita.index[0], COL_UNIDADE] = "Unidade Inédita"
    assert classificar_porte(treino, inedita).iloc[0] == "sem histórico"


def test_equidade_sinaliza_diferenca_grande():
    df = pd.DataFrame({COL_ALVO: [100.0] * 8, COL_UNIDADE: list("AAAABBBB")})
    prev = [100, 100, 100, 100, 70, 130, 70, 130]
    t = desempenho_por_grupo(df, prev, df[COL_UNIDADE], "unidade")
    r = resumo_de_diferenca(t)
    assert r["pior_grupo"] == "B" and r["sinalizado"] is True


def test_execucao_ponta_a_ponta_demo_e_deterministica():
    from src.executar import executar
    a = executar(salvar=False, verbose=False, forcar_demo=True)
    b = executar(salvar=False, verbose=False, forcar_demo=True)
    assert a["modo"] == "demo"
    pd.testing.assert_frame_equal(a["comparacao_validacao"].drop(columns="custo/tempo"), b["comparacao_validacao"].drop(columns="custo/tempo"))
    # todos os candidatos e o baseline na mesma partição e com a mesma métrica
    assert {"MAE", "WAPE", "viés"} <= set(a["comparacao_validacao"].columns)
    assert (a["comparacao_validacao"]["tipo"] == "modelo").sum() >= 3
    assert a["comparacao_validacao"]["abordagem"].str.contains("operacional").any()


def test_planilha_larga_vira_base_longa(tmp_path):
    from src.dados import _mes_de_cabecalho, carregar_mensal_agregado
    assert _mes_de_cabecalho("Agosto(2025)") == pd.Timestamp("2025-08-01")
    assert _mes_de_cabecalho("Março(2026)") == pd.Timestamp("2026-03-01")
    assert _mes_de_cabecalho("Total") is None
    df = pd.DataFrame({"Agosto(2025)": [10, 5], "Setembro(2025)": [12, 7]}, index=["A", "B"])
    df.to_excel(tmp_path / "x.xlsx")
    longo = carregar_mensal_agregado(tmp_path)
    assert len(longo) == 4 and longo["exames"].sum() == 34 == longo.attrs["total_planilha"]
    assert pd.api.types.is_datetime64_any_dtype(longo["mes"])
    assert carregar_mensal_agregado(tmp_path / "vazio") is None
