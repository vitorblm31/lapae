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
│   ├── 01_auditoria.ipynb    # inspeção, limpeza, contagens e base mensal
│   └── 02_baseline.ipynb     # partição temporal, pré-processador e baselines
├── src/                      # funções reutilizadas pelo pipeline
├── tests/                    # testes do pipeline (dados sintéticos)
└── docs/                     # dicionário de dados, memória da escuta, Canvas e relatório da Entrega 4
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
```

Sem arquivos em `dados/bruto/`, os notebooks rodam em **modo demonstração** (dados sintéticos) e mostram um aviso.
Nenhum resultado desse modo é resultado do projeto. Com os relatórios reais na pasta, o mesmo código usa os dados reais.
Todos os caminhos são relativos à raiz do repositório.

## Decisões de método

- **Partição temporal:** a decisão é aplicada ao futuro; treino no passado, validação e teste em meses posteriores.
- **Sem vazamento:** variáveis derivadas só usam meses anteriores ao mês-alvo; imputação, codificação e escala são ajustadas apenas no treino, dentro de um `Pipeline`; categorias novas no teste são ignoradas pelo codificador.
- **Baselines:** persistência (hipótese de baseline operacional), média e mediana do treino, média móvel de 3 meses.
- **Métricas:** MAE, WAPE e viés (previsto − real).

## Status

| Etapa | Situação |
|---|---|
| Escuta do demandante e Canvas de ML (Entrega 3) | Concluída |
| Contrato de dados, pipeline e testes (Entrega 4) | Pipeline e testes prontos com dados sintéticos |
| Execução com dados reais e baseline real | Pendente dos relatórios do demandante |
| Modelagem e devolutiva ao laboratório | Pendente |

## Dados e privacidade

Só contagens agregadas por unidade e mês, sem identificação de pacientes. Por serem dados de saúde, o acesso e o uso dependem de
autorização do laboratório e seguem a LGPD. Relatórios originais não são versionados (`.gitignore`).
