"""Testes do pipeline com dados SINTÉTICOS. Verificam o código, não os dados reais do projeto."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.baseline import prever_media_treino, prever_ultimo_valor, tabela_metricas  # noqa: E402
from src.config import ATRIBUTOS, COL_ALVO, COL_MES, COL_ORIGEM, MESES_PREVISAO  # noqa: E402
from src.dados import (limpar, preparar_base_mensal, validar_esquema, validar_totais)  # noqa: E402
from src.demo import gerar_registros_sinteticos  # noqa: E402
from src.diagnostico import autocorrelacao_total_mensal, residuos  # noqa: E402
from src.modelo import ModeloRelativo, ajustar_modelo, prever  # noqa: E402
from src.backtest import backtest  # noqa: E402
from src.dados import padronizar_largo, eh_planilha_larga  # noqa: E402
from src.particao import particionar_temporal, splits_por_mes  # noqa: E402
from src.preprocessamento import construir_preprocessador, resumo_do_fit  # noqa: E402
from src.variaveis import criar_variaveis, meses_futuros  # noqa: E402


@pytest.fixture(scope="module")
def d():
    bruto = gerar_registros_sinteticos()
    mensal, log, total = preparar_base_mensal(bruto)
    feats, _ = criar_variaveis(mensal)
    treino, valid, teste = particionar_temporal(feats)
    return dict(bruto=bruto, mensal=mensal, log=log, total=total, feats=feats,
                treino=treino, valid=valid, teste=teste)


def test_contagens_antes_e_depois_conferem(d):
    log = d["log"]
    assert (log["linhas_depois"] <= log["linhas_antes"]).all()
    assert validar_totais(d["total"], d["mensal"])["totais_conferem"]


def test_limpeza_remove_duplicatas_e_unifica_grafias(d):
    limpo, _ = limpar(d["bruto"])
    assert limpo["id_registro"].is_unique
    assert limpo[COL_ORIGEM].nunique() == 5


def test_formato_agregado_tambem_funciona():
    agregado = pd.DataFrame({
        "origem": ["sus", "SUS ", "Particular"],
        "mes": ["2026-01-15", "2026-02-01", "2026-01-01"], "exames": [10, 20, 5]})
    base, _, total = preparar_base_mensal(agregado)
    assert total == 35 and validar_totais(total, base)["totais_conferem"]
    assert base[COL_ORIGEM].nunique() == 2
    assert base[COL_ALVO].isna().sum() == 1  # Particular sem fevereiro: ausência não vira zero


def test_esquema_aprova_base_valida_e_reprova_chave_repetida(d):
    assert validar_esquema(d["mensal"])["ok"].all()
    ruim = pd.concat([d["mensal"], d["mensal"].iloc[[0]]], ignore_index=True)
    r = validar_esquema(ruim)
    assert not r.loc[r["verificação"].str.contains("chave"), "ok"].all()


def test_particao_temporal_sem_sobreposicao(d):
    t, v, e = d["treino"], d["valid"], d["teste"]
    assert t[COL_MES].max() < v[COL_MES].min() and v[COL_MES].max() < e[COL_MES].min()
    assert len(t) + len(v) + len(e) == len(d["feats"])


def test_validacao_cruzada_separa_por_mes_inteiro(d):
    X = d["treino"].reset_index(drop=True)
    for tr, va in splits_por_mes(X):
        meses_tr, meses_va = set(X.loc[tr, COL_MES]), set(X.loc[va, COL_MES])
        assert len(meses_va) == 1 and max(meses_tr) < min(meses_va)


def test_variaveis_nao_dependem_do_alvo(d):
    """Alterar o alvo não pode mudar nenhuma variável: elas só vêm da série e do calendário."""
    mensal = d["mensal"].copy()
    original, _ = criar_variaveis(mensal)
    alterado_df = mensal.copy()
    alterado_df[COL_ALVO] = alterado_df[COL_ALVO] + 1000
    alterado, _ = criar_variaveis(alterado_df)
    pd.testing.assert_frame_equal(original[ATRIBUTOS], alterado[ATRIBUTOS])


def test_fit_do_preprocessador_usa_somente_o_treino(d):
    pre = construir_preprocessador().fit(d["treino"][ATRIBUTOS])
    r = resumo_do_fit(pre)
    np.testing.assert_allclose(r["medias"], d["treino"][["tendencia", "dias_uteis"]].mean().values)
    assert not np.allclose(r["medias"], d["feats"][["tendencia", "dias_uteis"]].mean().values)


def test_categoria_nova_no_teste_nao_quebra_nem_refaz_o_ajuste(d):
    pre = construir_preprocessador().fit(d["treino"][ATRIBUTOS])
    antes = resumo_do_fit(pre)["categorias"]
    novo = d["teste"].copy()
    novo.loc[novo.index[0], COL_ORIGEM] = "ORIGEM NOVA"
    assert pre.transform(novo[ATRIBUTOS]).shape[0] == len(novo)
    assert resumo_do_fit(pre)["categorias"] == antes


def test_treino_validacao_e_teste_tem_os_mesmos_atributos(d):
    pre = construir_preprocessador().fit(d["treino"][ATRIBUTOS])
    formas = [pre.transform(x[ATRIBUTOS]).shape[1] for x in (d["treino"], d["valid"], d["teste"])]
    assert len(set(formas)) == 1 and len(pre.get_feature_names_out()) == formas[0]


def test_modelo_baselines_e_comparacao_nas_mesmas_condicoes(d):
    modelo = ModeloRelativo(alpha=30.0).fit(d["treino"], d["treino"][COL_ALVO])
    previsoes = {
        "trivial": prever_media_treino(d["treino"], d["valid"]),
        "operacional": prever_ultimo_valor(d["treino"], d["valid"]),
        "modelo": prever(modelo, d["valid"]),
    }
    assert all(len(p) == len(d["valid"]) for p in previsoes.values())
    tabela = tabela_metricas(d["valid"], previsoes)
    assert len(tabela) == 3 and tabela.iloc[:, 1:].notna().all().all()


def test_resultado_reprodutivel_com_semente_fixa(d):
    a = ajustar_modelo(d["treino"]).predict(d["valid"])
    b = ajustar_modelo(d["treino"]).predict(d["valid"])
    np.testing.assert_allclose(a, b)


def test_previsao_dos_meses_pedidos(d):
    futuro = meses_futuros(d["mensal"], MESES_PREVISAO)
    assert futuro[COL_MES].nunique() == 5 and futuro[COL_MES].min() > d["mensal"][COL_MES].max()
    assert futuro[ATRIBUTOS].notna().all().all()
    modelo = ModeloRelativo(alpha=30.0).fit(d["feats"], d["feats"][COL_ALVO])
    assert len(prever(modelo, futuro)) == len(futuro)


def test_residuos_e_autocorrelacao(d):
    modelo = ModeloRelativo(alpha=30.0).fit(d["treino"], d["treino"][COL_ALVO])
    res = residuos(d["valid"], prever(modelo, d["valid"]))
    assert {"residuo", "previsto"} <= set(res.columns)
    assert autocorrelacao_total_mensal(res) is None  # só 3 meses de validação


def test_planilha_larga_do_lapae_e_lida_e_confere():
    larga = pd.DataFrame({"Unnamed: 0": ["São Lucas", "SUS"], "Agosto(2025)": [24, 552],
                          "Setembro(2025)": [82, 483], "Março(2026)": [123, 689]})
    assert eh_planilha_larga(larga)
    base, _, total = padronizar_largo(larga)
    assert total == 24 + 552 + 82 + 483 + 123 + 689 and validar_totais(total, base)["totais_conferem"]
    assert base[COL_ORIGEM].nunique() == 2 and base[COL_MES].nunique() == 8  # grade preenche meses sem coluna com NaN
    assert base[COL_ALVO].isna().sum() == 10


def test_backtest_usa_so_o_passado(d):
    bt = backtest(d["feats"], min_treino=6, h_max=2)
    assert {"média por origem", "último valor", "Ridge relativo"} <= set(bt["abordagem"])
    assert bt["corte"].min() >= 6


def test_sem_caminhos_absolutos_no_codigo():
    padrao = re.compile(r"(/home/|/Users/|[A-Za-z]:\\\\|/root/|/mnt/)")
    achados = []
    for pasta in ("src", "notebooks", "tests"):
        for arq in list((RAIZ / pasta).rglob("*.py")) + list((RAIZ / pasta).rglob("*.ipynb")):
            if arq.name == "test_pipeline.py":
                continue
            if padrao.search(arq.read_text(encoding="utf-8")):
                achados.append(str(arq.relative_to(RAIZ)))
    assert not achados, f"Caminhos absolutos em: {achados}"
