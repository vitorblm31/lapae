"""Gera o rascunho do relatório preliminar (Entrega 6) a partir de resultados/<modo>/.

Uso:  python -m src.relatorio            -> docs/E06_equipeXX_relatorio_preliminar.md
Texto fixo = decisões e fatos já registrados nas Entregas 3 e 4 (marcados [F] fato, [H] hipótese, [L] lacuna).
Números = lidos de resultados/. Em modo demonstração, todo número aparece com aviso e NÃO é resultado do projeto."""
import pandas as pd

from src import config
from src.executar import ler_resultados


def n(x, d=1):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return "—" if x is None or pd.isna(x) else n(100 * x, d) + "%"


def tabela(df: pd.DataFrame, formatos: dict | None = None) -> str:
    formatos = formatos or {}
    cab = "| " + " | ".join(df.columns) + " |\n|" + "|".join("---" for _ in df.columns) + "|\n"
    linhas = []
    for _, r in df.iterrows():
        cel = []
        for c in df.columns:
            v = r[c]
            f = formatos.get(c)
            if f:
                cel.append(f(v))
            elif isinstance(v, float) and not pd.isna(v) and float(v).is_integer():
                cel.append(n(v, 0))
            else:
                cel.append(n(v, 1) if isinstance(v, float) else str(v))
        linhas.append("| " + " | ".join(cel) + " |")
    return cab + "\n".join(linhas) + "\n"


def gerar(rotulo=None) -> str:
    R = ler_resultados(rotulo)
    demo = R["modo"] == "demo"
    E, L = R["escolha"], R["limiar"]
    cv, ct = R["comparacao_validacao"], R["comparacao_teste"]
    gv, gt = R["ganho_validacao"], R["ganho_teste"]
    aviso = ("> **MODO DEMONSTRAÇÃO.** Os números deste rascunho vêm de dados sintéticos (`src/demo.py`) e servem só para provar que o pipeline "
             "executa. **Não são resultado do projeto.** Quando os relatórios do LAPAE chegarem a `dados/bruto/`, rode `python -m src.executar` "
             "e `python -m src.relatorio` e revise os textos interpretativos.\n\n") if demo else ""
    marca = " *(demonstração)*" if demo else ""

    # Quadro de comparação obrigatório
    q = pd.DataFrame({
        "Abordagem": cv["abordagem"], "Hiperparâmetros": cv["hiperparâmetros"],
        "Métrica principal: MAE (exames/unidade·mês)": cv["MAE"].map(lambda v: n(v, 2)),
        "Métrica secundária: WAPE; viés; erro do total mensal": [f"{pct(w)}; {n(b, 1)}; {n(t, 1)}" for w, b, t in zip(cv["WAPE"], cv["viés"], cv["erro do total mensal"])],
        "Custo/tempo": cv["custo/tempo"].str.replace(".", ",", regex=False)})
    qt = pd.DataFrame({"Abordagem": ct["abordagem"], "MAE": ct["MAE"].map(lambda v: n(v, 2)), "WAPE": ct["WAPE"].map(pct),
                       "Viés": ct["viés"].map(lambda v: n(v, 1)), "Erro do total mensal": ct["erro do total mensal"].map(lambda v: n(v, 1))})

    melhor_base_nao_op = (not E["recomenda_modelo"]) and E["melhor_baseline_na_validacao"] != "Persistência (operacional)" and R["ganho_operacional_validacao"]["reducao_relativa_mae"] > 0
    if E["recomenda_modelo"]:
        rec = (f"Recomendação preliminar: adotar **{E['escolhido']}**, que reduziu o MAE em {pct(E['ganho_relativo_mae'])} sobre o baseline operacional na validação "
               f"e não piorou o erro do total mensal.")
    else:
        motivos = []
        if E["ganho_relativo_mae"] < E["ganho_minimo_exigido"]:
            motivos.append(f"o ganho de MAE ({pct(E['ganho_relativo_mae'])}) ficou abaixo do mínimo de {pct(E['ganho_minimo_exigido'], 0)}")
        if not E["total_mensal_nao_piora"]:
            motivos.append("o erro do total mensal piorou em relação ao baseline")
        rec = (f"Recomendação preliminar: **manter {E['melhor_baseline_na_validacao']}** como regra operacional. O melhor candidato ({E['melhor_modelo_na_validacao']}) "
               f"não se paga: " + " e ".join(motivos) + ". " +
               ("Essa é a regra mais exigente: contra a persistência, que é a hipótese de baseline operacional, o candidato ganha com folga (ver seção 6)." if melhor_base_nao_op else ""))
    confirma = ("O teste, avaliado uma única vez, **confirmou** o ganho da validação." if E["teste_confirma_ganho"]
                else "O teste, avaliado uma única vez, **não confirmou** o ganho observado na validação: com tão poucos meses, a escolha entre modelos é instável e isso entra como limite do resultado.")

    go_v, go_t = R["ganho_operacional_validacao"], R["ganho_operacional_teste"]
    d0 = R["dados"]
    tem_mun = d0["tem_municipio"]
    acima = L.get("meses_acima_de_k_na_serie", [])
    ef = L["efetivo"]
    eq = R["equidade_resumo"]
    eq_txt = "\n".join(f"- **{c}**: pior grupo `{v.get('pior_grupo', '—')}` (WAPE {pct(v.get('wape_pior'))}) contra melhor `{v.get('melhor_grupo', '—')}` "
                       f"(WAPE {pct(v.get('wape_melhor'))}); razão {n(v.get('razao_wape'), 1)}x. {v['conclusao'][0].upper() + v['conclusao'][1:]}." for c, v in eq.items())
    eqt = R["equidade"][R["equidade"]["critério"].isin(["município", "porte da unidade"])][["critério", "grupo", "n", "WAPE", "viés relativo"]]
    ab = R["ablação_identificadores"]
    sig = L["sigma"]
    d = R["dados"]
    params = "; ".join(f"{k} ({', '.join(f'{a}={b}' for a, b in v.items())})" for k, v in E["parametros_escolhidos"].items())
    faixa = R["erro_faixa"][["faixa do previsto", "n", "MAE", "WAPE", "viés", "exames subestimados", "exames superestimados"]]
    casos = R["casos_problematicos"].head(5)[["unidade", "mes", "exames", "previsto", "erro", "indício"]]
    casos["mes"] = casos["mes"].astype(str).str[:7]

    return f"""# E06 | Relatório preliminar: previsão mensal de exames do LAPAE

**Equipe XX:** Vítor Batista, Marcello Siqueira e Ricardo César. **Demandante:** Frederico Torres (LAPAE, João Pessoa/PB).
**Repositório:** https://github.com/vitorblm31/lapae. **Disciplina:** Aprendizagem de Máquina Supervisionada, UFPB/CCSA, 2026.2.

{aviso}Legenda: **[F]** fato relatado pelo demandante, **[H]** hipótese da equipe, **[L]** lacuna ou pendência.

## 1. Resumo executivo (esboço)

O LAPAE registra o volume mensal de exames, mas não o usa no planejamento, e às vezes falta tempo para dar conta de tudo [F]. Prevemos, no início de cada mês, quantos exames cada policlínica ou USF vai enviar naquele mês, para que o demandante organize o trabalho. {rec} Contra o baseline operacional (repetir o mês anterior), o melhor candidato ({E['melhor_modelo_na_validacao']}) reduz o erro em {n(go_v['exames_por_unidade_mes_evitados'], 1)} exames por unidade e mês na validação e {n(go_t['exames_por_unidade_mes_evitados'], 1)} no teste{marca}; no erro do total mensal, {n(go_v['exames_por_mes_no_total_evitados'], 0)} e {n(go_t['exames_por_mes_no_total_evitados'], 0)} exames por mês, respectivamente (negativo = piora). Principal limite: apenas {d0['n_meses']} meses de histórico por unidade impedem separar sazonalidade de tendência, inclusive o pico de outubro [F][H]. Custos B e C ainda não foram estimados com o demandante [L].

## 2. Decisão e contexto

- **Usuário e decisão** [F][H]: Frederico Torres organiza o trabalho do laboratório no início de todo mês. A previsão alimenta essa organização. Com que informação ele decide hoje: a confirmar [L].
- **Cadência:** mensal [F].
- **Capacidade k** [F][L]: média de {n(config.CAPACIDADE_K, 0)} exames, lida como volume mensal. Unidade de tempo e o que limita o número (pessoas, funcionária que registra, equipamentos) ainda a confirmar.
- **Baseline operacional** [F][H]: hoje não há previsão formal. O processo atual é Frederico ler os exames e repassá-los a uma funcionária, que registra o resultado no sistema da policlínica ou USF e depois no sistema interno. Como regra equivalente em termos de previsão, assumimos que o mês repete o anterior (persistência por unidade), a confirmar com ele.

## 3. Formulação

| Item | Definição |
|---|---|
| Unidade de análise | Policlínica ou USF em um mês (chave `unidade`, `mes`) [H] |
| População | {d0['n_unidades']} séries no relatório do demandante{': policlínicas/USF' if demo else ' (São Lucas, Roseane Dore, Maurílio de Almeida, Viver Mais, SUS e Particulares)'}. Se SUS e Particulares são segmentos que se sobrepõem às demais unidades ou séries separadas, e se a soma das seis é o total do laboratório: a confirmar [L]. Município não consta na planilha [L] |
| Alvo | Exames com data de chegada no mês-calendário, por unidade [H]; retificações posteriores a confirmar [L] |
| Horizonte e momento da previsão | Prever o mês m no início de m, usando só informação até o fim de m-1 [F][H] |
| Corte | Corte de 4 dias informado pelo demandante [F]. O que ele mede ainda não está claro [L]. Regra provisória: só entram dados com data de chegada até o último dia do mês anterior [H] |
| Decisão binária derivada | Reforçar o mês quando se espera que o total ultrapasse k (seção 7) [H] |

O problema é de **regressão**; o limiar da seção 7 se aplica à decisão binária derivada do total previsto.

## 4. Dados

- **Fontes:** {"planilha `dados_lapae.xlsx` enviada pelo demandante: contagem mensal de exames por unidade ou segmento, de ago/2025 a set/2026, sem identificação de pacientes (LGPD) [F][H]." if not demo else "relatórios do demandante agregados por unidade e mês, sem identificação de pacientes (LGPD) [H]."} Originais fora do Git; contrato completo na Entrega 4 e dicionário em `docs/dicionario_dados.md`.
- **Situação:** {"relatórios reais ainda não recebidos [L]; este rascunho roda sobre dados sintéticos." if demo else "dados reais carregados (" + str(d0['n_unidades']) + " séries, " + str(d0['n_meses']) + " meses). A planilha já vem agregada por mês, então a limpeza de registros (datas, duplicatas) não se aplica; a conferência é a soma da base longa contra o total da planilha (notebook 01). A planilha não informa município, data de extração nem retificações [L]."}
- **Tratamento:** {'conversão da planilha larga (unidade × mês) para a base longa, com conferência de totais (notebook 01).' if not demo else 'normalização de unidade e município, descarte de datas inválidas, remoção de duplicatas por `id_registro`, grade completa unidade × mês, com log de contagens antes e depois (notebook 01).'}
- **Faltantes:** {d['celulas_sem_registro (NaN)']} de {d['celulas_unidade_mes']} células unidade·mês sem registro; ausência não é convertida em zero antes de o demandante explicar o que ela significa [H]. {d['linhas_descartadas_sem_historico_ou_alvo']} linhas descartadas por falta de histórico (três meses de defasagem) ou alvo ausente.
- **Vazamento:** variáveis permitidas = defasagens 1 a 3, média móvel dos 3 meses anteriores, mês do ano, dias úteis, unidade{' e município' if tem_mun else ' (município não disponível na planilha [L])'}. Proibidas = qualquer informação de m (primeiros dias de m, total de m, tempo de liberação), contagem retificada depois do corte, horas extras e reforço de equipe (consequência da decisão) e ajustes sobre todos os meses. Testes automáticos garantem que as variáveis não usam o mês-alvo e que o pré-processador é ajustado só no treino.
- **Limitações:** {d0['n_meses']} meses por unidade ({d0['n_meses'] - 3} utilizáveis depois de três defasagens); sem como usar "mesmo mês do ano anterior" [F][H]; a defasagem 1 depende de o mês anterior estar fechado no corte [L].

## 5. Método

**Partição temporal** (a decisão é aplicada ao futuro): treino {R['particao'].iloc[0]['de']} a {R['particao'].iloc[0]['ate']}, validação {R['particao'].iloc[1]['de']} a {R['particao'].iloc[1]['ate']}, teste {R['particao'].iloc[2]['de']} a {R['particao'].iloc[2]['ate']}{marca}. O teste fica guardado e é avaliado uma única vez, com os modelos reajustados em treino + validação.

**Validação cruzada:** janela expansiva (origem móvel) *dentro do treino*: cada dobra prevê um mês usando só meses anteriores ({len(R['dobras_cv'])} dobras{marca}). Protege contra treinar com o futuro e contra escolher hiperparâmetros olhando o teste. Embaralhar meses aleatoriamente foi descartado.

**Modelos e o que cada um minimiza:**

{tabela(R['grades'])}
**Métrica principal: MAE, em exames por unidade e mês.** A decisão é de planejamento de tempo, e o MAE está na unidade do demandante (exames). A escolha de hiperparâmetros usa a mesma métrica. **Secundárias:** WAPE (erro relativo ponderado, comparável entre unidades de portes diferentes), viés (previsto − real; negativo = subestima, que tende a gerar falta de tempo) e erro absoluto médio do **total** mensal, que é o número que a decisão de capacidade sente. Os erros têm custos assimétricos [H], por isso o viés é reportado à parte.

**Regra de escolha (a complexidade precisa se pagar) [H]:** o modelo só substitui o baseline se reduzir o MAE em pelo menos {pct(config.GANHO_MINIMO_RELATIVO, 0)} e não piorar o erro do total mensal.

**Pré-processamento:** `ColumnTransformer` dentro de `Pipeline`: mediana para faltantes, padronização apenas para o modelo linear, one-hot com categorias novas ignoradas. Tudo ajustado só no treino.

## 6. Resultados{marca}

**Quadro de comparação (validação, mesma partição e métrica):**

{tabela(q)}
**Teste (uma única avaliação, modelos reajustados em treino + validação):**

{tabela(qt)}
{confirma}

**Ganho contra o baseline operacional (persistência)**: {E['melhor_modelo_na_validacao']} reduz o MAE em {n(go_v['exames_por_unidade_mes_evitados'], 1)} exames por unidade e mês na validação ({pct(go_v['reducao_relativa_mae'])}) e {n(go_t['exames_por_unidade_mes_evitados'], 1)} no teste ({pct(go_t['reducao_relativa_mae'])}); no erro do total mensal, {n(go_v['exames_por_mes_no_total_evitados'], 0)} e {n(go_t['exames_por_mes_no_total_evitados'], 0)} exames por mês.

**Ganho em unidade do demandante contra o melhor baseline** (melhor candidato, {E['melhor_modelo_na_validacao']}, contra {E['melhor_baseline_na_validacao']}): na validação, {n(gv['exames_por_unidade_mes_evitados'], 2)} exames por unidade e mês ({pct(gv['reducao_relativa_mae'])} do MAE) e {n(gv['exames_por_mes_no_total_evitados'], 1)} exames por mês no erro do total; no teste, {n(gt['exames_por_unidade_mes_evitados'], 2)} e {n(gt['exames_por_mes_no_total_evitados'], 1)}, respectivamente. Valores negativos significam que o candidato errou mais que o baseline.

Hiperparâmetros escolhidos por validação cruzada: {params}.

## 7. Limiar e operação{marca}

| Elemento | Registro |
|---|---|
| B e C | B = {n(L['B'], 1)} (benefício de reforçar num mês que estoura) e C = {n(L['C'], 1)} (custo de reforçar à toa), em horas-equipe. {L['origem_BC']}. Estimar com o demandante [L] |
| t* = C/(B+C) | {n(L['t_estrela'], 2)}. {L['frase'].replace('.', ',') if False else L['frase']} |
| Capacidade k | {n(L['k'], 0)} exames/mês. {L['k_origem']} |
| Dispersão do erro do total (σ) | {n(sig['sigma'], 1)} exames (maior entre RMS do total por mês, {n(sig['sigma_rms_total'], 1)}, e soma em quadratura por unidade, {n(sig['sigma_quadratura'], 1)}; só {sig['n_meses']} meses de CV, estimativa grosseira [H]) |
| Limiar efetivo | A ação dispara quando o total previsto passa de {n(ef['mu_estrela'], 0)} exames, {n(abs(ef['margem_exames']), 0)} {"abaixo" if ef['margem_exames'] > 0 else "acima"} de k. Restrição que morde primeiro: {ef['restricao_que_morde_primeiro']} |
| Calibração | Razão real/previsto por faixa em `calibracao.csv` (próxima de 1 = calibrado); intervalo de {pct(config.NIVEL_INTERVALO, 0)} cobriu {pct(R['cobertura']['cobertura_observada'])} dos casos em {R['cobertura']['n']} previsões. Probabilidade de estouro assume erro normal, não verificada [H] |

{('Na série inteira, o total mensal passou de k em: ' + ', '.join(acima) + ' (máximo de ' + n(L['total_mensal_maximo_na_serie'], 0) + ' exames).' ) if acima else 'Nenhum mês da série passou de k.'} Os meses de validação e teste ficaram {'todos abaixo' if L['meses_acima_de_k_no_real'] == 0 else 'parcialmente acima'} de k, então a tabela abaixo não discrimina entre limiares: o pico de outubro/2025 está fora dela, porque as defasagens consomem os três primeiros meses.

Sensibilidade a C/B (meses de validação e teste, {L['meses_avaliados']} meses, {L['meses_acima_de_k_no_real']} acima de k):

{tabela(R['tabela_limiar'][['C/B', 't*', 'total previsto que dispara a ação', 'meses com ação', 'ação certa (VP)', 'ação à toa (FP)', 'estouro sem ação (FN)', 'benefício líquido (B=1)']], {'C/B': lambda v: n(v, 2), 't*': lambda v: n(v, 2)})}
## 8. Erros e equidade (esboço com uma análise)

**Onde os erros se concentram (faixa do previsto){marca}:**

{tabela(faixa, {'WAPE': pct})}
**Maiores erros e possível causa:**

{tabela(casos)}
Problemas de dado, não de modelo: {d['celulas_sem_registro (NaN)']} células sem registro, {d['unidades_com_algum_mes_ausente']} unidades com algum mês ausente e {d['linhas_descartadas_sem_historico_ou_alvo']} linhas sem histórico suficiente (unidade nova não é prevista; com {d0['n_meses']} meses, três viram defasagem). Saltos bruscos no real precisam ser checados com o demandante (retificação, falha de envio ou evento real) [L].

**Equidade.** O modelo orienta a alocação de uma equipe finita; subestimar um grupo sistematicamente faz o trabalho dele ficar para trás primeiro. Comparação de WAPE entre grupos (limite de {n(config.LIMITE_RAZAO_WAPE_GRUPOS, 1)}x entre o pior e o melhor grupo, combinado como [H]):

{eq_txt}

{tabela(eqt, {"WAPE": pct, "viés relativo": pct})}
Em séries pequenas, o WAPE alto corresponde a poucos exames (ver MAE em `erro_unidade.csv`); o erro que pesa na capacidade está nas séries grandes. Variáveis proxy: `unidade`{' e `município`' if tem_mun else ''} podem refletir perfil de público ou convênio. Sem {'elas' if tem_mun else 'ela'}, o WAPE da validação foi {pct(ab['WAPE_sem_unidade_e_municipio'])} contra {pct(ab['WAPE_com'])} com elas ({ab['modelo']}{marca}). A diferença entre grupos é reportada mesmo se não puder ser corrigida no semestre; com poucas observações por grupo, ela pode ser ruído [H].

## 9. Produto (esboço)

**MVP:** tela única que recebe o histórico mensal por unidade e devolve a previsão do mês.
**Entradas:** arquivo de contagens por unidade e mês até o mês anterior; mês-alvo; capacidade k (editável).
**Saídas:** total previsto do mês com faixa de incerteza, previsão por unidade, alerta "pode estourar a capacidade" (probabilidade ≥ t*) e comparação com a regra de persistência.

```
+--------------------------------------------------------------+
| LAPAE | Previsão de exames           Mês-alvo: [ 2027-01 v ] |
+--------------------------------------------------------------+
| Total previsto: 1.7xx   (faixa 80%: 1.6xx a 1.8xx)           |
| Capacidade k: [1850]    Chance de estourar: 3x%   [ATENÇÃO]  |
+--------------------------------------------------------------+
| Unidade        | Previsto | Mês anterior | Faixa              |
| Unidade A      |   xxx    |     xxx      | xxx - xxx          |
| ...                                                          |
+--------------------------------------------------------------+
| [Baixar CSV]   Aviso: previsão de volume, não decide sozinha |
+--------------------------------------------------------------+
```

## 10. Riscos e limites (esboço)

- **Usos vedados** [L, a confirmar na escuta]: não usar a previsão para avaliar desempenho de unidades ou de pessoas, nem para reduzir equipe sem revisão humana. Uso previsto: planejamento de capacidade com dados agregados.
- **Degradação esperada:** pouco histórico, pico de outubro não verificável, mudanças de convênio ou de rota de coleta, unidade nova sem histórico.
- **Incentivos:** se a previsão passar a orientar a escala, a equipe pode ajustar o registro dos exames; o próprio resultado altera os dados futuros.
- **LGPD:** apenas contagens agregadas, sem paciente; base legal e autorização formal pendentes [L].

## 11. Devolutiva

Pendente: o registro da validação com o demandante será feito após a devolutiva coletiva de 03/12 e a segunda rodada de escuta [L].

## 12. Reprodutibilidade

- **Ambiente:** Python 3.13; dependências fixadas em `requirements.txt`; caminhos relativos à raiz.
- **Semente:** {R['semente']} (modelos, divisão e geração sintética).
- **Comandos** (da raiz do repositório):

```bash
pip install -r requirements.txt
python -m pytest
python -m src.executar          # pipeline completo, grava resultados/<modo>/
python -m src.relatorio         # regera este rascunho
# ou, em notebooks: 01_auditoria, 02_baseline, 03_modelagem, 04_limiar_calibracao, 05_erros_equidade
```

- **Versão dos dados:** {"dados sintéticos de demonstração (`base_mensal_DEMO.csv`); relatórios reais ainda não recebidos [L]." if demo else "registrar data de recebimento, nome do arquivo e quem enviou em `dados/bruto/LEIAME.md`."}

## Apêndice A. Contribuição de cada integrante

| Integrante | Contribuição |
|---|---|
| Vítor Batista | [preencher] |
| Marcello Siqueira | [preencher] |
| Ricardo César | [preencher] |

## Apêndice B. Declaração de uso de IA generativa

| Item | Registro |
|---|---|
| Ferramenta | Claude (Anthropic) |
| Finalidade | Apoio na estrutura do pipeline de modelagem, na análise de erros e equidade, na escolha de limiar e no rascunho deste relatório, a partir do guia da Entrega 6 e do repositório da Entrega 4 |
| Trechos influenciados | `src/validacao.py`, `modelos.py`, `avaliacao.py`, `limiar.py`, `erros.py`, `equidade.py`, `executar.py`, `relatorio.py`, `tests/test_modelagem.py`, notebooks 03 a 05 e o texto deste relatório |
| Dados inseridos | Nenhum dado sigiloso, pessoal ou de base restrita; apenas código e documentos da equipe |
| Responsabilidade | A equipe revisou o conteúdo e responde por ele; cada integrante deve saber explicar e defender qualquer parte |

## Apêndice C. Hipóteses e abordagens descartadas

- **Divisão aleatória ou validação cruzada embaralhada:** deixaria o modelo ver o futuro; descartada em favor da janela expansiva.
- **Mesmo mês do ano anterior como baseline:** impossível com ~12 meses de histórico [F][H].
- **SARIMA, Prophet e modelos de série longa:** exigem mais pontos por série do que existem; fora do escopo do semestre.
- **Exames dos primeiros dias do mês-alvo como variável:** só existe depois do corte e faz parte do alvo (vazamento temporal).
- **Previsão só do total do laboratório:** mantida como alternativa se as séries por unidade forem curtas ou ruidosas demais [H].
- **Alvo relativo (razão ao mês anterior) para modelos de árvore, que não extrapolam tendência:** ideia anotada para a Entrega 8, não testada.
"""


if __name__ == "__main__":
    texto = gerar()
    destino = config.RAIZ / "docs" / "E06_equipeXX_relatorio_preliminar.md"
    destino.write_text(texto, encoding="utf-8")
    print("Gravado:", destino.relative_to(config.RAIZ))
