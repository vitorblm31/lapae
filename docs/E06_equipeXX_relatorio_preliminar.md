# E06 | Relatório preliminar: previsão mensal de exames do LAPAE

**Equipe XX:** Vítor Batista, Marcello Siqueira e Ricardo César. **Demandante:** Frederico Torres (LAPAE, João Pessoa/PB).
**Repositório:** https://github.com/vitorblm31/lapae. **Disciplina:** Aprendizagem de Máquina Supervisionada, UFPB/CCSA, 2026.2.

Legenda: **[F]** fato relatado pelo demandante, **[H]** hipótese da equipe, **[L]** lacuna ou pendência.

## 1. Resumo executivo (esboço)

O LAPAE registra o volume mensal de exames, mas não o usa no planejamento, e às vezes falta tempo para dar conta de tudo [F]. Prevemos, no início de cada mês, quantos exames cada policlínica ou USF vai enviar naquele mês, para que o demandante organize o trabalho. Recomendação preliminar: **manter Média do treino** como regra operacional. O melhor candidato (Random forest) não se paga: o erro do total mensal piorou em relação ao baseline. Essa é a regra mais exigente: contra a persistência, que é a hipótese de baseline operacional, o candidato ganha com folga (ver seção 6). Contra o baseline operacional (repetir o mês anterior), o melhor candidato (Random forest) reduz o erro em 20,2 exames por unidade e mês na validação e 17,9 no teste; no erro do total mensal, 96 e 165 exames por mês, respectivamente (negativo = piora). Principal limite: apenas 14 meses de histórico por unidade impedem separar sazonalidade de tendência, inclusive o pico de outubro [F][H]. Custos B e C ainda não foram estimados com o demandante [L].

## 2. Decisão e contexto

- **Usuário e decisão** [F][H]: Frederico Torres organiza o trabalho do laboratório no início de todo mês. A previsão alimenta essa organização. Com que informação ele decide hoje: a confirmar [L].
- **Cadência:** mensal [F].
- **Capacidade k** [F][L]: média de 1.850 exames, lida como volume mensal. Unidade de tempo e o que limita o número (pessoas, funcionária que registra, equipamentos) ainda a confirmar.
- **Baseline operacional** [F][H]: hoje não há previsão formal. O processo atual é Frederico ler os exames e repassá-los a uma funcionária, que registra o resultado no sistema da policlínica ou USF e depois no sistema interno. Como regra equivalente em termos de previsão, assumimos que o mês repete o anterior (persistência por unidade), a confirmar com ele.

## 3. Formulação

| Item | Definição |
|---|---|
| Unidade de análise | Policlínica ou USF em um mês (chave `unidade`, `mes`) [H] |
| População | 6 séries no relatório do demandante (São Lucas, Roseane Dore, Maurílio de Almeida, Viver Mais, SUS e Particulares). Se SUS e Particulares são segmentos que se sobrepõem às demais unidades ou séries separadas, e se a soma das seis é o total do laboratório: a confirmar [L]. Município não consta na planilha [L] |
| Alvo | Exames com data de chegada no mês-calendário, por unidade [H]; retificações posteriores a confirmar [L] |
| Horizonte e momento da previsão | Prever o mês m no início de m, usando só informação até o fim de m-1 [F][H] |
| Corte | Corte de 4 dias informado pelo demandante [F]. O que ele mede ainda não está claro [L]. Regra provisória: só entram dados com data de chegada até o último dia do mês anterior [H] |
| Decisão binária derivada | Reforçar o mês quando se espera que o total ultrapasse k (seção 7) [H] |

O problema é de **regressão**; o limiar da seção 7 se aplica à decisão binária derivada do total previsto.

## 4. Dados

- **Fontes:** planilha `dados_lapae.xlsx` enviada pelo demandante: contagem mensal de exames por unidade ou segmento, de ago/2025 a set/2026, sem identificação de pacientes (LGPD) [F][H]. Originais fora do Git; contrato completo na Entrega 4 e dicionário em `docs/dicionario_dados.md`.
- **Situação:** dados reais carregados (6 séries, 14 meses). A planilha já vem agregada por mês, então a limpeza de registros (datas, duplicatas) não se aplica; a conferência é a soma da base longa contra o total da planilha (notebook 01). A planilha não informa município, data de extração nem retificações [L].
- **Tratamento:** conversão da planilha larga (unidade × mês) para a base longa, com conferência de totais (notebook 01).
- **Faltantes:** 0 de 84 células unidade·mês sem registro; ausência não é convertida em zero antes de o demandante explicar o que ela significa [H]. 18 linhas descartadas por falta de histórico (três meses de defasagem) ou alvo ausente.
- **Vazamento:** variáveis permitidas = defasagens 1 a 3, média móvel dos 3 meses anteriores, mês do ano, dias úteis, unidade (município não disponível na planilha [L]). Proibidas = qualquer informação de m (primeiros dias de m, total de m, tempo de liberação), contagem retificada depois do corte, horas extras e reforço de equipe (consequência da decisão) e ajustes sobre todos os meses. Testes automáticos garantem que as variáveis não usam o mês-alvo e que o pré-processador é ajustado só no treino.
- **Limitações:** 14 meses por unidade (11 utilizáveis depois de três defasagens); sem como usar "mesmo mês do ano anterior" [F][H]; a defasagem 1 depende de o mês anterior estar fechado no corte [L].

## 5. Método

**Partição temporal** (a decisão é aplicada ao futuro): treino 2025-11 a 2026-05, validação 2026-06 a 2026-07, teste 2026-08 a 2026-09. O teste fica guardado e é avaliado uma única vez, com os modelos reajustados em treino + validação.

**Validação cruzada:** janela expansiva (origem móvel) *dentro do treino*: cada dobra prevê um mês usando só meses anteriores (5 dobras). Protege contra treinar com o futuro e contra escolher hiperparâmetros olhando o teste. Embaralhar meses aleatoriamente foi descartado.

**Modelos e o que cada um minimiza:**

| modelo | o que minimiza | grade |
|---|---|---|
| Linear (Ridge) | erro quadrático + penalização L2 dos coeficientes | {"alpha": [0.01, 0.1, 1.0, 10.0, 100.0]} |
| Árvore de decisão | erro quadrático (impureza) em cada divisão | {"max_depth": [2, 3, 4, 6], "min_samples_leaf": [2, 5, 10]} |
| Random forest | erro quadrático por árvore; a média das árvores reduz a variância | {"max_depth": [3, 6, null], "min_samples_leaf": [2, 5], "max_features": [0.5, 1.0]} |
| Gradient boosting | erro quadrático, corrigindo os resíduos das árvores anteriores | {"n_estimators": [100, 300], "learning_rate": [0.03, 0.1], "max_depth": [2, 3]} |

**Métrica principal: MAE, em exames por unidade e mês.** A decisão é de planejamento de tempo, e o MAE está na unidade do demandante (exames). A escolha de hiperparâmetros usa a mesma métrica. **Secundárias:** WAPE (erro relativo ponderado, comparável entre unidades de portes diferentes), viés (previsto − real; negativo = subestima, que tende a gerar falta de tempo) e erro absoluto médio do **total** mensal, que é o número que a decisão de capacidade sente. Os erros têm custos assimétricos [H], por isso o viés é reportado à parte.

**Regra de escolha (a complexidade precisa se pagar) [H]:** o modelo só substitui o baseline se reduzir o MAE em pelo menos 10% e não piorar o erro do total mensal.

**Pré-processamento:** `ColumnTransformer` dentro de `Pipeline`: mediana para faltantes, padronização apenas para o modelo linear, one-hot com categorias novas ignoradas. Tudo ajustado só no treino.

## 6. Resultados

**Quadro de comparação (validação, mesma partição e métrica):**

| Abordagem | Hiperparâmetros | Métrica principal: MAE (exames/unidade·mês) | Métrica secundária: WAPE; viés; erro do total mensal | Custo/tempo |
|---|---|---|---|---|
| Persistência (operacional) | — | 63,83 | 25,8%; -18,5; 358,0 | desprezível |
| Média do treino | — | 50,65 | 20,5%; 1,3; 234,5 | desprezível |
| Mediana do treino | — | 53,08 | 21,4%; -1,1; 234,5 | desprezível |
| Média móvel de 3 meses | — | 62,33 | 25,2%; 10,9; 315,0 | desprezível |
| Linear (Ridge) | alpha=0.1 | 54,39 | 22,0%; -7,9; 252,6 | busca 0,3 s; previsão 2,8 ms |
| Árvore de decisão | max_depth=4, min_samples_leaf=5 | 51,49 | 20,8%; 1,0; 237,0 | busca 0,6 s; previsão 2,6 ms |
| Random forest | max_depth=3, max_features=0.5, min_samples_leaf=2 | 43,64 | 17,6%; 2,4; 261,9 | busca 6,3 s; previsão 10,0 ms |
| Gradient boosting | learning_rate=0.03, max_depth=2, n_estimators=300 | 78,70 | 31,8%; -6,2; 440,4 | busca 2,1 s; previsão 2,5 ms |

**Teste (uma única avaliação, modelos reajustados em treino + validação):**

| Abordagem | MAE | WAPE | Viés | Erro do total mensal |
|---|---|---|---|---|
| Persistência (operacional) | 45,42 | 18,9% | 19,4 | 206,5 |
| Média do treino | 38,54 | 16,0% | 8,2 | 49,4 |
| Mediana do treino | 46,50 | 19,3% | 5,2 | 45,0 |
| Média móvel de 3 meses | 28,53 | 11,9% | 5,1 | 61,8 |
| Linear (Ridge) | 38,96 | 16,2% | 12,2 | 73,0 |
| Árvore de decisão | 38,52 | 16,0% | 8,7 | 52,4 |
| Random forest | 27,49 | 11,4% | 6,9 | 41,4 |
| Gradient boosting | 36,28 | 15,1% | 3,4 | 45,8 |

O teste, avaliado uma única vez, **confirmou** o ganho da validação.

**Ganho contra o baseline operacional (persistência)**: Random forest reduz o MAE em 20,2 exames por unidade e mês na validação (31,6%) e 17,9 no teste (39,5%); no erro do total mensal, 96 e 165 exames por mês.

**Ganho em unidade do demandante contra o melhor baseline** (melhor candidato, Random forest, contra Média do treino): na validação, 7,01 exames por unidade e mês (13,8% do MAE) e -27,4 exames por mês no erro do total; no teste, 11,04 e 8,1, respectivamente. Valores negativos significam que o candidato errou mais que o baseline.

Hiperparâmetros escolhidos por validação cruzada: Linear (Ridge) (alpha=0.1); Árvore de decisão (max_depth=4, min_samples_leaf=5); Random forest (max_depth=3, max_features=0.5, min_samples_leaf=2); Gradient boosting (learning_rate=0.03, max_depth=2, n_estimators=300).

## 7. Limiar e operação

| Elemento | Registro |
|---|---|
| B e C | B = 2,0 (benefício de reforçar num mês que estoura) e C = 1,0 (custo de reforçar à toa), em horas-equipe. [H] hipótese da equipe, não estimada com o demandante. Estimar com o demandante [L] |
| t* = C/(B+C) | 0,33. Com B = 2,0 e C = 1,0 (horas-equipe), t* = 0,33: vale reforçar o mês quando a chance estimada de estourar a capacidade for de pelo menos 33%, porque deixar de agir num mês que estoura custa 2,0 vez(es) o custo de agir à toa. |
| Capacidade k | 1.850 exames/mês. [F] média informada pelo demandante; [L] unidade de tempo a confirmar |
| Dispersão do erro do total (σ) | 274,3 exames (maior entre RMS do total por mês, 274,3, e soma em quadratura por unidade, 262,0; só 5 meses de CV, estimativa grosseira [H]) |
| Limiar efetivo | A ação dispara quando o total previsto passa de 1.732 exames, 118 abaixo de k. Restrição que morde primeiro: econômica (t*): age antes de chegar a k |
| Calibração | Razão real/previsto por faixa em `calibracao.csv` (próxima de 1 = calibrado); intervalo de 80% cobriu 95,8% dos casos em 24 previsões. Probabilidade de estouro assume erro normal, não verificada [H] |

Na série inteira, o total mensal passou de k em: 2025-10 (máximo de 1.971 exames). Os meses de validação e teste ficaram todos abaixo de k, então a tabela abaixo não discrimina entre limiares: o pico de outubro/2025 está fora dela, porque as defasagens consomem os três primeiros meses.

Sensibilidade a C/B (meses de validação e teste, 4 meses, 0 acima de k):

| C/B | t* | total previsto que dispara a ação | meses com ação | ação certa (VP) | ação à toa (FP) | estouro sem ação (FN) | benefício líquido (B=1) |
|---|---|---|---|---|---|---|---|
| 0,25 | 0,20 | 1.619,2 | 0 | 0 | 0 | 0 | 0 |
| 0,50 | 0,33 | 1.731,9 | 0 | 0 | 0 | 0 | 0 |
| 1,00 | 0,50 | 1.850 | 0 | 0 | 0 | 0 | 0 |
| 2,00 | 0,67 | 1.968,1 | 0 | 0 | 0 | 0 | 0 |

## 8. Erros e equidade (esboço com uma análise)

**Onde os erros se concentram (faixa do previsto):**

| faixa do previsto | n | MAE | WAPE | viés | exames subestimados | exames superestimados |
|---|---|---|---|---|---|---|
| (367.0, 666.0] | 8 | 64,7 | 12,1% | 10,4 | 217,4 | 300,6 |
| (6.0, 66.0] | 8 | 5,9 | 54,0% | -3,6 | 38,3 | 9,2 |
| (66.0, 367.0] | 8 | 36,0 | 19,5% | 7,1 | 115,6 | 172,6 |

**Maiores erros e possível causa:**

| unidade | mes | exames | previsto | erro | indício |
|---|---|---|---|---|---|
| SUS | 2026-06 | 491 | 665,9 | 174,9 | sem salto: erro do modelo |
| Maurílio de Almeida | 2026-07 | 593 | 467,4 | -125,6 | sem salto: erro do modelo |
| SUS | 2026-08 | 510 | 606,8 | 96,8 | sem salto: erro do modelo |
| Roseane Dore | 2026-07 | 344 | 272,2 | -71,8 | salto brusco no real: checar registro/retificação (dado) ou evento real |
| Roseane Dore | 2026-06 | 218 | 286,8 | 68,8 | sem salto: erro do modelo |

Problemas de dado, não de modelo: 0 células sem registro, 0 unidades com algum mês ausente e 18 linhas sem histórico suficiente (unidade nova não é prevista; com 14 meses, três viram defasagem). Saltos bruscos no real precisam ser checados com o demandante (retificação, falha de envio ou evento real) [L].

**Equidade.** O modelo orienta a alocação de uma equipe finita; subestimar um grupo sistematicamente faz o trabalho dele ficar para trás primeiro. Comparação de WAPE entre grupos (limite de 1,5x entre o pior e o melhor grupo, combinado como [H]):

- **porte da unidade**: pior grupo `pequena` (WAPE 54,0%) contra melhor `grande` (WAPE 12,1%); razão 4,5x. Diferença acima do limite combinado [H]: reportar e discutir com o demandante.
- **unidade**: pior grupo `Particulares` (WAPE 56,0%) contra melhor `Maurílio de Almeida` (WAPE 10,6%); razão 5,3x. Diferença acima do limite combinado [H]: reportar e discutir com o demandante.

| critério | grupo | n | WAPE | viés relativo |
|---|---|---|---|---|
| porte da unidade | grande | 8 | 12,1% | 1,9% |
| porte da unidade | média | 8 | 19,5% | 3,9% |
| porte da unidade | pequena | 8 | 54,0% | -33,1% |

Em séries pequenas, o WAPE alto corresponde a poucos exames (ver MAE em `erro_unidade.csv`); o erro que pesa na capacidade está nas séries grandes. Variáveis proxy: `unidade` podem refletir perfil de público ou convênio. Sem ela, o WAPE da validação foi 19,0% contra 17,6% com elas (Random forest). A diferença entre grupos é reportada mesmo se não puder ser corrigida no semestre; com poucas observações por grupo, ela pode ser ruído [H].

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
- **Semente:** 42 (modelos, divisão e geração sintética).
- **Comandos** (da raiz do repositório):

```bash
pip install -r requirements.txt
python -m pytest
python -m src.executar          # pipeline completo, grava resultados/<modo>/
python -m src.relatorio         # regera este rascunho
# ou, em notebooks: 01_auditoria, 02_baseline, 03_modelagem, 04_limiar_calibracao, 05_erros_equidade
```

- **Versão dos dados:** registrar data de recebimento, nome do arquivo e quem enviou em `dados/bruto/LEIAME.md`.

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
