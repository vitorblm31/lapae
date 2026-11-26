"""Pipeline completo da Entrega 6, do dado processado ao quadro de comparação, limiar, erros e equidade.

Uso:  python -m src.executar          (a partir da raiz do repositório)
Sem dados reais em dados/processado/base_mensal.csv, roda em MODO DEMONSTRAÇÃO (dados sintéticos): nenhum número
desse modo é resultado do projeto. Resultados vão para resultados/demo/ ou resultados/real/."""
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone

from src import config
from src.avaliacao import erro_total_medio, ganho_sobre_baseline, metricas, totais_mensais
from src.baseline import prever_estatistica_treino, prever_media_movel, prever_persistencia
from src.config import COL_ALVO, COL_MES, COL_MUNICIPIO, COL_UNIDADE
from src.dados import agregar_mensal, carregar_mensal_agregado, limpar
from src.demo import ROTULO_DEMO, gerar_registros_sinteticos
from src.equidade import classificar_porte, desempenho_por_grupo, resumo_de_diferenca
from src.erros import casos_problematicos, por_faixa_do_escore, por_grupo, problemas_de_dado
from src.limiar import (calibracao, cobertura_intervalo, frase_limiar, limiar_efetivo, limiar_otimo, prob_estouro,
                        sigma_do_total, tabela_limiar)
from src.modelos import COLUNAS, buscar, candidatos, previsoes_fora_da_amostra, tempo_de_previsao
from src.particao import particionar_temporal
from src.validacao import descrever_splits, splits_expansivos
from src.variaveis import criar_variaveis

warnings.filterwarnings("ignore", category=FutureWarning)
BASELINE_OPERACIONAL = "Persistência (operacional)"


def carregar_mensal(forcar_demo: bool = False):
    if forcar_demo:
        limpo, _ = limpar(gerar_registros_sinteticos())
        return agregar_mensal(limpo), True
    real = config.PROCESSADO / "base_mensal.csv"
    demo = config.PROCESSADO / "base_mensal_DEMO.csv"
    agregado = carregar_mensal_agregado()
    if agregado is not None:  # relatório do demandante já agregado por mês: grava a base analítica real
        agregado.to_csv(real, index=False)
        return agregado, False
    if real.exists():
        return pd.read_csv(real, parse_dates=[COL_MES]), False
    if demo.exists():
        return pd.read_csv(demo, parse_dates=[COL_MES]), True
    limpo, _ = limpar(gerar_registros_sinteticos())
    return agregar_mensal(limpo), True


def previsoes_baseline(treino, df):
    return {BASELINE_OPERACIONAL: prever_persistencia(df).to_numpy(),
            "Média do treino": prever_estatistica_treino(treino, df, "mean").to_numpy(),
            "Mediana do treino": prever_estatistica_treino(treino, df, "median").to_numpy(),
            "Média móvel de 3 meses": prever_media_movel(df).to_numpy()}


def verificar_sem_vazamento(treino, valid, teste):
    assert treino[COL_MES].max() < valid[COL_MES].min() <= valid[COL_MES].max() < teste[COL_MES].min()
    for _, tr, va in [("cv", treino, treino)]:
        for a, b in splits_expansivos(tr):
            assert tr.iloc[a][COL_MES].max() < tr.iloc[b][COL_MES].min()


def executar(salvar: bool = True, verbose: bool = True, forcar_demo: bool = False) -> dict:
    log = print if verbose else (lambda *a, **k: None)
    mensal, demo = carregar_mensal(forcar_demo)
    rotulo = "demo" if demo else "real"
    if demo:
        log(ROTULO_DEMO)

    tem_municipio = mensal[COL_MUNICIPIO].notna().any()
    cols = COLUNAS if tem_municipio else [c for c in COLUNAS if c != COL_MUNICIPIO]
    feats, descartadas = criar_variaveis(mensal)
    treino, valid, teste = particionar_temporal(feats)
    verificar_sem_vazamento(treino, valid, teste)
    treino, valid, teste = (d.reset_index(drop=True) for d in (treino, valid, teste))
    treino_valid = pd.concat([treino, valid], ignore_index=True)
    R = {"modo": rotulo, "aviso": ROTULO_DEMO if demo else "", "semente": config.SEMENTE}
    R["particao"] = pd.DataFrame([{"conjunto": n, "de": f"{d[COL_MES].min():%Y-%m}", "ate": f"{d[COL_MES].max():%Y-%m}",
                                   "meses": d[COL_MES].nunique(), "linhas": len(d)}
                                  for n, d in [("treino", treino), ("validação", valid), ("teste", teste)]])
    R["dobras_cv"] = descrever_splits(treino, splits_expansivos(treino))
    R["dados"] = problemas_de_dado(mensal, descartadas)
    R["dados"]["tem_municipio"] = bool(tem_municipio)
    R["dados"]["n_unidades"] = int(mensal[COL_UNIDADE].nunique())
    R["dados"]["n_meses"] = int(mensal[COL_MES].nunique())

    # ---- baselines recalculados na mesma partição ----
    base_v, base_t = previsoes_baseline(treino, valid), previsoes_baseline(treino_valid, teste)

    # ---- candidatos: hiperparâmetros por validação cruzada temporal dentro do treino ----
    buscas, tempos, prev_v = {}, {}, {}
    for nome in candidatos():
        log(f"Buscando hiperparâmetros: {nome}")
        b, seg = buscar(nome, treino, colunas=cols)
        buscas[nome] = b
        prev_v[nome] = b.predict(valid[cols])
        tempos[nome] = {"busca_s": seg, "prever_ms": 1000 * tempo_de_previsao(b.best_estimator_, valid[cols])}

    # ---- quadro de comparação (validação) ----
    y_v = valid[COL_ALVO].to_numpy()
    linhas = []
    for n, p in base_v.items():
        m = metricas(y_v, p)
        linhas.append({"abordagem": n, "tipo": "baseline", "hiperparâmetros": "—", "MAE (CV treino)": np.nan,
                       "MAE": m["MAE"], "WAPE": m["WAPE"], "viés": m["viés"], "erro do total mensal": erro_total_medio(valid, p),
                       "custo/tempo": "desprezível"})
    for n, b in buscas.items():
        m = metricas(y_v, prev_v[n])
        hp = ", ".join(f"{k.split('__')[1]}={v}" for k, v in b.best_params_.items())
        linhas.append({"abordagem": n, "tipo": "modelo", "hiperparâmetros": hp, "MAE (CV treino)": -b.best_score_,
                       "MAE": m["MAE"], "WAPE": m["WAPE"], "viés": m["viés"], "erro do total mensal": erro_total_medio(valid, prev_v[n]),
                       "custo/tempo": f"busca {tempos[n]['busca_s']:.1f} s; previsão {tempos[n]['prever_ms']:.1f} ms"})
    comp = pd.DataFrame(linhas)
    R["comparacao_validacao"] = comp
    R["grades"] = pd.DataFrame([{"modelo": n, "o que minimiza": c[3], "grade": json.dumps({k.split('__')[1]: v for k, v in c[1].items()}, ensure_ascii=False)}
                                for n, c in candidatos().items()])

    # ---- escolha (regra: complexidade precisa se pagar) ----
    modelos = comp[comp["tipo"] == "modelo"]
    melhor_modelo = modelos.loc[modelos["MAE"].idxmin(), "abordagem"]
    bases = comp[comp["tipo"] == "baseline"]
    melhor_base = bases.loc[bases["MAE"].idxmin(), "abordagem"]
    ganho_rel = (bases["MAE"].min() - modelos["MAE"].min()) / bases["MAE"].min()
    R["ganho_validacao"] = ganho_sobre_baseline(valid, prev_v[melhor_modelo], base_v[melhor_base])
    # Regra [H]: o modelo só se justifica se (1) reduz o MAE por unidade em pelo menos GANHO_MINIMO_RELATIVO e
    # (2) não piora o erro do total mensal, que é o número que a decisão de capacidade usa.
    total_ok = R["ganho_validacao"]["exames_por_mes_no_total_evitados"] >= 0
    recomenda_modelo = bool(ganho_rel >= config.GANHO_MINIMO_RELATIVO and total_ok)
    escolhido = melhor_modelo if recomenda_modelo else melhor_base
    R["escolha"] = {"melhor_modelo_na_validacao": melhor_modelo, "melhor_baseline_na_validacao": melhor_base,
                    "ganho_relativo_mae": float(ganho_rel), "ganho_minimo_exigido": config.GANHO_MINIMO_RELATIVO,
                    "total_mensal_nao_piora": bool(total_ok), "recomenda_modelo": recomenda_modelo, "escolhido": escolhido}

    # ---- teste, avaliado uma única vez: reajusta com treino+validação, mesmos hiperparâmetros ----
    prev_t = {}
    for n, b in buscas.items():
        prev_t[n] = clone(b.best_estimator_).fit(treino_valid[cols], treino_valid[COL_ALVO]).predict(teste[cols])
    y_t = teste[COL_ALVO].to_numpy()
    lt = []
    for n, p in {**base_t, **prev_t}.items():
        m = metricas(y_t, p)
        lt.append({"abordagem": n, "tipo": "baseline" if n in base_t else "modelo", "MAE": m["MAE"], "WAPE": m["WAPE"],
                   "viés": m["viés"], "erro do total mensal": erro_total_medio(teste, p)})
    R["comparacao_teste"] = pd.DataFrame(lt)
    R["ganho_teste"] = ganho_sobre_baseline(teste, prev_t[melhor_modelo], base_t[melhor_base])
    # ganho também contra o baseline OPERACIONAL (persistência), que é o que o demandante faria hoje
    R["ganho_operacional_validacao"] = ganho_sobre_baseline(valid, prev_v[melhor_modelo], base_v[BASELINE_OPERACIONAL])
    R["ganho_operacional_teste"] = ganho_sobre_baseline(teste, prev_t[melhor_modelo], base_t[BASELINE_OPERACIONAL])
    R["escolha"]["teste_confirma_ganho"] = bool(R["ganho_teste"]["reducao_relativa_mae"] >= config.GANHO_MINIMO_RELATIVO
                                                and R["ganho_teste"]["exames_por_mes_no_total_evitados"] >= 0)

    # ---- previsões fora da amostra (validação + teste) do modelo melhor, para erros, equidade e limiar ----
    oos = pd.concat([valid.assign(previsto=prev_v[melhor_modelo], conjunto="validação"),
                     teste.assign(previsto=prev_t[melhor_modelo], conjunto="teste")], ignore_index=True)
    oos_base = np.concatenate([base_v[melhor_base], base_t[melhor_base]])
    R["fora_da_amostra"] = oos

    # ---- limiar, capacidade e calibração ----
    oof = previsoes_fora_da_amostra(buscas[melhor_modelo].best_estimator_, treino, colunas=cols)
    sig = sigma_do_total(oof)
    tot = totais_mensais(oos, oos["previsto"])
    if demo:
        k = float(np.percentile(totais_mensais(treino_valid, treino_valid[COL_ALVO])["real"], 75))
        k_origem = "DEMO: percentil 75 dos totais mensais sintéticos (a capacidade real de 1.850 não se aplica a dados sintéticos)"
    else:
        k, k_origem = float(config.CAPACIDADE_K), "[F] média informada pelo demandante; [L] unidade de tempo a confirmar"
    B, C = config.B_HIPOTESE, config.C_HIPOTESE
    t_star = limiar_otimo(B, C)
    R["limiar"] = {"B": B, "C": C, "origem_BC": "[H] hipótese da equipe, não estimada com o demandante", "t_estrela": t_star,
                   "frase": frase_limiar(B, C), "k": k, "k_origem": k_origem, "sigma": sig,
                   "efetivo": limiar_efetivo(k, sig["sigma"], t_star, float(tot["previsto"].max())),
                   "meses_acima_de_k_no_real": int((tot["real"] > k).sum()), "meses_avaliados": int(len(tot))}
    serie = mensal.groupby(COL_MES)[COL_ALVO].sum(min_count=1)
    R["limiar"]["meses_acima_de_k_na_serie"] = [f"{m:%Y-%m}" for m in serie[serie > k].index]
    R["limiar"]["total_mensal_maximo_na_serie"] = float(serie.max())
    tot["prob_estouro"] = prob_estouro(tot["previsto"], k, sig["sigma"])
    tot["estourou_k"] = tot["real"] > k
    R["totais_mensais"] = tot
    R["tabela_limiar"] = tabela_limiar(tot, k, sig["sigma"], config.RAZOES_C_SOBRE_B)
    R["calibracao"] = calibracao(oos, oos["previsto"])
    R["cobertura"] = cobertura_intervalo(oos, oos["previsto"], sig["sigma_unidade"], config.NIVEL_INTERVALO)

    # ---- erros ----
    R["erro_faixa"] = por_faixa_do_escore(oos, oos["previsto"])
    R["erro_unidade"] = por_grupo(oos, oos["previsto"], COL_UNIDADE)
    if tem_municipio:
        R["erro_municipio"] = por_grupo(oos, oos["previsto"], COL_MUNICIPIO)
    R["erro_mes"] = por_grupo(oos, oos["previsto"], COL_MES)
    R["casos_problematicos"] = casos_problematicos(oos, oos["previsto"])

    # ---- equidade ----
    oos["porte"] = classificar_porte(treino, oos)
    partes_eq = ([desempenho_por_grupo(oos, oos["previsto"], oos[COL_MUNICIPIO], "município")] if tem_municipio else [])
    partes_eq += [desempenho_por_grupo(oos, oos["previsto"], oos["porte"], "porte da unidade"),
                  desempenho_por_grupo(oos, oos["previsto"], oos[COL_UNIDADE], "unidade")]
    eq = pd.concat(partes_eq, ignore_index=True)
    R["equidade"] = eq
    R["equidade_resumo"] = {c: resumo_de_diferenca(eq[eq["critério"] == c]) for c in eq["critério"].unique()}
    base_eq = desempenho_por_grupo(oos, oos_base, oos["porte"], "porte da unidade (baseline)")
    R["equidade_baseline_porte"] = base_eq

    # ---- proxies: o modelo piora sem identificadores de unidade e município? ----
    sem_id = [c for c in cols if c not in (COL_UNIDADE, COL_MUNICIPIO)]
    b2, _ = buscar(melhor_modelo, treino, colunas=sem_id)
    p2 = b2.predict(valid[sem_id])
    R["ablação_identificadores"] = {"modelo": melhor_modelo, "WAPE_com": metricas(y_v, prev_v[melhor_modelo])["WAPE"],
                                    "WAPE_sem_unidade_e_municipio": metricas(y_v, p2)["WAPE"]}

    # ---- importância (explicabilidade) ----
    R["escolha"]["parametros_escolhidos"] = {n: {k.split("__")[1]: (v if not isinstance(v, np.generic) else v.item()) for k, v in b.best_params_.items()} for n, b in buscas.items()}

    if salvar:
        _salvar(R, rotulo)
    return R


def _salvar(R, rotulo):
    pasta = config.RESULTADOS / rotulo
    pasta.mkdir(parents=True, exist_ok=True)
    resumo = {}
    for k, v in R.items():
        if isinstance(v, pd.DataFrame):
            v.to_csv(pasta / f"{k}.csv", index=False)
        else:
            resumo[k] = v
    with open(pasta / "resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=lambda o: o.item() if isinstance(o, np.generic) else str(o))


if __name__ == "__main__":
    executar()


def ler_resultados(rotulo: str | None = None) -> dict:
    """Relê o que `executar` gravou (para os notebooks 04 e 05 e para o gerador do relatório)."""
    if rotulo is None:
        rotulo = "real" if (config.RESULTADOS / "real" / "resumo.json").exists() else "demo"
    pasta = config.RESULTADOS / rotulo
    R = json.loads((pasta / "resumo.json").read_text(encoding="utf-8"))
    for f in pasta.glob("*.csv"):
        R[f.stem] = pd.read_csv(f)
    return R
