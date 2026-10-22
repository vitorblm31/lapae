"""Testes do pipeline com dados SINTÉTICOS. Verificam o código, não os dados reais do projeto."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.config import CATEGORICAS, COL_ALVO, COL_MES, COL_UNIDADE, NUMERICAS  # noqa: E402
from src.dados import agregar_mensal, limpar, validar_totais  # noqa: E402
from src.demo import gerar_registros_sinteticos  # noqa: E402
from src.particao import particionar_temporal  # noqa: E402
from src.preprocessamento import construir_preprocessador, resumo_do_fit  # noqa: E402
from src.variaveis import criar_variaveis  # noqa: E402


@pytest.fixture(scope="module")
def base():
    bruto = gerar_registros_sinteticos()
    limpo, log = limpar(bruto)
    mensal = agregar_mensal(limpo)
    feats, _ = criar_variaveis(mensal)
    return {"bruto": bruto, "limpo": limpo, "log": log, "mensal": mensal, "feats": feats}


def test_contagens_antes_e_depois_conferem(base):
    log = base["log"]
    assert (log["linhas_depois"] <= log["linhas_antes"]).all()
    assert log["linhas_depois"].iloc[-1] == len(base["limpo"])
    res = validar_totais(base["limpo"], base["mensal"])
    assert res["totais_conferem"], res


def test_limpeza_remove_duplicatas_e_normaliza_unidade(base):
    assert base["limpo"]["id_registro"].is_unique
    assert base["limpo"][COL_UNIDADE].nunique() == 10  # grafias diferentes unificadas


def test_particao_temporal_sem_sobreposicao(base):
    treino, valid, teste = particionar_temporal(base["feats"])
    assert treino[COL_MES].max() < valid[COL_MES].min()
    assert valid[COL_MES].max() < teste[COL_MES].min()
    assert len(treino) + len(valid) + len(teste) == len(base["feats"])


def test_variaveis_nao_usam_o_mes_alvo(base):
    """Altera o alvo de um mês: as variáveis desse mês não podem mudar; as do mês seguinte devem mudar."""
    mensal = base["mensal"].copy()
    meses = sorted(mensal[COL_MES].unique())
    alvo_m, seguinte = meses[7], meses[8]
    original, _ = criar_variaveis(mensal)
    alterado_df = mensal.copy()
    alterado_df.loc[alterado_df[COL_MES] == alvo_m, COL_ALVO] += 1000
    alterado, _ = criar_variaveis(alterado_df)
    cols = ["lag_1", "lag_2", "lag_3", "media_movel_3"]
    a = original[original[COL_MES] == alvo_m].set_index(COL_UNIDADE)[cols]
    b = alterado[alterado[COL_MES] == alvo_m].set_index(COL_UNIDADE)[cols]
    pd.testing.assert_frame_equal(a, b)
    c = original[original[COL_MES] == seguinte].set_index(COL_UNIDADE)["lag_1"]
    d = alterado[alterado[COL_MES] == seguinte].set_index(COL_UNIDADE)["lag_1"]
    assert not np.allclose(c.values, d.values)


def test_fit_do_preprocessador_usa_somente_o_treino(base):
    treino, valid, teste = particionar_temporal(base["feats"])
    pre = construir_preprocessador().fit(treino[NUMERICAS + CATEGORICAS])
    r = resumo_do_fit(pre)
    media_treino = treino[NUMERICAS].mean().values
    media_tudo = base["feats"][NUMERICAS].mean().values
    np.testing.assert_allclose(r["medias"], media_treino)
    assert not np.allclose(r["medias"], media_tudo)  # se usasse todos os dados, seria igual a media_tudo


def test_categoria_nova_no_teste_nao_quebra_nem_refaz_o_ajuste(base):
    treino, valid, teste = particionar_temporal(base["feats"])
    pre = construir_preprocessador().fit(treino[NUMERICAS + CATEGORICAS])
    categorias_antes = resumo_do_fit(pre)["categorias"]
    novo = teste.copy()
    novo.loc[novo.index[0], COL_UNIDADE] = "Unidade Inédita"
    saida = pre.transform(novo[NUMERICAS + CATEGORICAS])
    assert saida.shape[0] == len(novo)
    assert resumo_do_fit(pre)["categorias"] == categorias_antes  # nada foi reajustado


def test_treino_validacao_e_teste_tem_os_mesmos_atributos(base):
    treino, valid, teste = particionar_temporal(base["feats"])
    pre = construir_preprocessador().fit(treino[NUMERICAS + CATEGORICAS])
    a, b, c = (pre.transform(d[NUMERICAS + CATEGORICAS]) for d in (treino, valid, teste))
    assert a.shape[1] == b.shape[1] == c.shape[1]
    nomes = pre.get_feature_names_out()
    assert len(nomes) == a.shape[1]


def test_sem_caminhos_absolutos_no_codigo():
    padrao = re.compile(r"(/home/|/Users/|[A-Za-z]:\\\\|/root/|/mnt/)")
    achados = []
    for pasta in ("src", "notebooks"):
        for arq in list((RAIZ / pasta).rglob("*.py")) + list((RAIZ / pasta).rglob("*.ipynb")):
            texto = arq.read_text(encoding="utf-8")
            if padrao.search(texto):
                achados.append(str(arq.relative_to(RAIZ)))
    assert not achados, f"Caminhos absolutos em: {achados}"
