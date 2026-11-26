# LAPAE | Previsão mensal de exames

Projeto aplicado da disciplina de Aprendizagem de Máquina Supervisionada (UFPB/CCSA, 2026.2), desenvolvido para o
**LAPAE – Laboratório de Patologia e Análises Especializadas**, de João Pessoa/PB.

## Problema, decisão e alvo

- **Problema:** o laboratório não usa o volume mensal de exames, que já fica registrado no sistema, e às vezes falta tempo para dar conta de tudo.
- **Decisão apoiada:** a organização do trabalho do mês, feita pelo demandante no início de cada mês.
- **Alvo:** quantidade de exames recebidos por policlínica ou USF em cada mês (unidade × mês).
- **Fontes:** relatórios enviados pelo demandante (ainda não recebidos). Enquanto isso, o código roda com dados sintéticos, identificados como demonstração.

## Equipe

Vítor Batista, Marcello Siqueira e Ricardo César. Demandante: Frederico Torres (LAPAE).

## Estrutura

```
.
├── README.md
├── requirements.txt          # dependências com versões
├── dados/
│   ├── bruto/                # relatórios originais (não versionados; ver LEIAME.md)
│   └── processado/           # base analítica gerada pelo notebook 01
├── notebooks/
│   ├── 01_auditoria.ipynb          # inspeção, limpeza, contagens e base mensal
│   ├── 02_baseline.ipynb           # partição temporal, pré-processador e baselines
│   ├── 03_modelagem.ipynb          # 4 modelos, CV temporal, quadro de comparação, teste
│   ├── 04_limiar_calibracao.ipynb  # B, C, t*, capacidade, calibração
│   └── 05_erros_equidade.ipynb     # erros por faixa, perfil e grupo; equidade e proxies
├── src/                      # funções reutilizadas pelo pipeline (executar.py roda tudo)
├── tests/                    # testes do pipeline e da modelagem (dados sintéticos)
├── resultados/               # tabelas geradas por src.executar (demo/ versionado; real/ fora do Git)
└── docs/                     # dicionário, Entregas 3 e 4, relatório preliminar e checklist da Entrega 6
```

## Como executar

Requer Python 3.13 (ambiente de referência).

```bash
python -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest                   # testes do pipeline
jupyter nbconvert --to notebook --execute --inplace notebooks/01_auditoria.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_baseline.ipynb

python -m src.executar             # Entrega 6: modelos, limiar, erros e equidade -> resultados/<modo>/
python -m src.relatorio            # regera docs/E06_equipeXX_relatorio_preliminar.md
```
Os notebooks 03 a 05 rodam do mesmo modo (`nbconvert --execute`); o 03 deve rodar antes do 04 e do 05.

Sem arquivos em `dados/bruto/`, os notebooks rodam em **modo demonstração** (dados sintéticos) e mostram um aviso.
Nenhum resultado desse modo é resultado do projeto. Com os relatórios reais na pasta, o mesmo código usa os dados reais.
Todos os caminhos são relativos à raiz do repositório.

## Decisões de método

- **Partição temporal:** a decisão é aplicada ao futuro; treino no passado, validação e teste em meses posteriores.
- **Sem vazamento:** variáveis derivadas só usam meses anteriores ao mês-alvo; imputação, codificação e escala são ajustadas apenas no treino, dentro de um `Pipeline`; categorias novas no teste são ignoradas pelo codificador.
- **Baselines:** persistência (hipótese de baseline operacional), média e mediana do treino, média móvel de 3 meses.
- **Métricas:** MAE (principal, em exames por unidade e mês), WAPE, viés (previsto − real) e erro do total mensal.
- **Modelos (Entrega 6):** Ridge, árvore de decisão, random forest e gradient boosting; hiperparâmetros por validação cruzada com janela expansiva dentro do treino; teste avaliado uma única vez, com reajuste em treino + validação.
- **Regra de escolha:** o modelo só substitui o baseline se reduzir o MAE em pelo menos 10% e não piorar o erro do total mensal [H].
- **Limiar:** decisão derivada "reforçar o mês se P(total > k) ≥ t\* = C/(B+C)"; B e C ainda são hipótese [L].

## Status

| Etapa | Situação |
|---|---|
| Escuta do demandante e Canvas de ML (Entrega 3) | Concluída |
| Contrato de dados, pipeline e testes (Entrega 4) | Pipeline e testes prontos com dados sintéticos |
| Execução com dados reais e baseline real | Pendente dos relatórios do demandante |
| Modelagem, limiar, erros, equidade e relatório preliminar (Entrega 6) | Código e rascunho prontos; números reais dependem dos relatórios |
| Devolutiva ao laboratório | Pendente |

## Dados e privacidade

Só contagens agregadas por unidade e mês, sem identificação de pacientes. Por serem dados de saúde, o acesso e o uso dependem de
autorização do laboratório e seguem a LGPD. Relatórios originais não são versionados (`.gitignore`).
