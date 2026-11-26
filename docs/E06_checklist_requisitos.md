# Entrega 6 – onde cada requisito está atendido

Guia: `entrega_6_pacote_a2.pdf`. Prazo 26/11/2026, 23h59. Arquivo principal: `E06_equipeXX_relatorio_preliminar.pdf` (até 8 páginas) + link do repositório, pelo SIGAA.

## O que entregar

| # | Requisito | Onde |
|---|---|---|
| 1 | Pipeline reproduzível, do dado bruto ao modelo | `src/dados.py` → `variaveis.py` → `particao.py` → `modelos.py`; orquestrado por `src/executar.py`; notebooks 01 a 03 |
| 2 | Baseline operacional recalculado na mesma partição | `src/executar.py` (`previsoes_baseline`, recalculado em validação e teste); notebook 03 |
| 3 | Linear, árvore e ensemble, hiperparâmetros por CV | `src/modelos.py` (Ridge, árvore, random forest e gradient boosting; `GridSearchCV` com CV temporal) |
| 4 | Estratégia de validação | `src/validacao.py` (janela expansiva dentro do treino); relatório, seção 5 |
| 5 | Métrica principal justificada | Relatório, seção 5 (MAE em exames; WAPE, viés e erro do total como secundárias) |
| 6 | Escolha de limiar | `src/limiar.py`; notebook 04; relatório, seção 7 |
| 7 | Análise de erros e observações problemáticas | `src/erros.py`; notebook 05; relatório, seção 8 |
| 8 | Equidade entre grupos | `src/equidade.py` (município, porte, unidade); notebook 05 |
| 9 | Relatório preliminar | `docs/E06_equipeXX_relatorio_preliminar.md` (gerado por `python -m src.relatorio`) |

## Checklist do guia

| Item | Situação | Evidência |
|---|---|---|
| Todos os modelos na mesma partição e métrica | Feito | `comparacao_validacao.csv`, `comparacao_teste.csv`; teste `test_execucao_ponta_a_ponta_demo_e_deterministica` |
| Baseline recalculado, não copiado | Feito | calculado em `executar()` a cada execução |
| Hiperparâmetros por validação, não por tentativa manual | Feito | `GridSearchCV` com grades fixas em `modelos.py`; grades e escolhas gravadas nos resultados |
| Nenhuma transformação usou o teste | Feito | `Pipeline` ajustado só no treino; teste reajusta em treino + validação sem escolher nada; `test_cv_so_dentro_do_treino_e_sem_olhar_o_futuro` |
| Limiar justificado por B, C e capacidade | Feito com hipótese | B e C são [H], não estimados com o demandante [L]; sensibilidade em `tabela_limiar.csv` |
| Análise de erros com perfis concretos | Feito | faixa do escore, unidade, município, mês, casos problemáticos |
| Comparação entre grupos reportada | Feito | `equidade.csv`, `equidade_resumo` em `resumo.json` |
| Ganho sobre baseline em unidade de decisão | Feito | exames por unidade·mês e exames por mês no total (`ganho_validacao`, `ganho_teste`) |
| Seções "completas" completas | Parcial: depende dos dados reais | seções 2 a 7 e 12 têm texto fechado; os números só valem após rodar com os relatórios do LAPAE |

## O que ainda depende de vocês

1. **Dados reais.** Copiar os relatórios para `dados/bruto/`, ajustar `carregar_bruto()` ao formato, rodar o notebook 01 (gera `base_mensal.csv`), depois `python -m src.executar` e `python -m src.relatorio`. Revisar os textos interpretativos, que foram escritos para os resultados de demonstração.
2. **B e C.** Obter uma estimativa grosseira com o Frederico (horas-equipe ou atraso evitado) e trocar `B_HIPOTESE` e `C_HIPOTESE` em `src/config.py`.
3. **Capacidade k.** Confirmar se 1.850 é mensal e o que a limita. Em modo demonstração, k é um percentil dos dados sintéticos.
4. **Quadro de contribuições** (apêndice A) e o número da equipe no nome do arquivo.
5. **Remunerômetro 2.0** é atividade individual e não está neste repositório.
6. **Tamanho:** o rascunho passa de 8 páginas se exportado inteiro. Cortar a tabela de sensibilidade e a tabela de equidade por unidade primeiro.
7. **Exportar para PDF** com o nome `E06_equipeXX_relatorio_preliminar.pdf` (por exemplo, `pandoc` ou colar no Docs) e conferir se os links estão acessíveis ao professor.
