# LAPAE | Previsão mensal de exames

Projeto aplicado da disciplina de Aprendizagem de Máquina Supervisionada (UFPB/CCSA, 2026.2), desenvolvido para o
**LAPAE – Laboratório de Patologia e Análises Especializadas**, de João Pessoa/PB.

## Problema, decisão e alvo

- **Problema:** o volume mensal de exames fica registrado no sistema, mas não é usado para nada, e às vezes falta tempo para dar conta de tudo.
- **Decisão apoiada:** planejar a capacidade de trabalho (pessoas, escalas, insumos) dos meses de 2027. O demandante organiza o trabalho no início de cada mês.
- **Alvo:** número de exames recebidos por **origem** (São Lucas, Roseane Dore, Maurílio de Almeida, Viver Mais, SUS e Particulares) em cada mês.
- **Horizonte:** agosto a dezembro de 2027, a partir do último mês observado (setembro de 2026), isto é, 11 a 15 meses à frente.
- **Dados:** base oficial enviada pelo demandante, 14 meses (agosto/2025 a setembro/2026), contagens mensais por origem.

## Equipe

Vítor Batista, Marcello Siqueira e Ricardo César. Demandante: Frederico Torres (LAPAE).

## Estrutura

```
.
├── README.md
├── requirements.txt          # dependências com versões
├── dados/
│   ├── bruto/                # planilha original dados_lapae.xlsx (ver LEIAME.md)
│   └── processado/           # previsões e métricas geradas pelos notebooks
├── notebooks/
│   ├── 01_auditoria.ipynb    # conferência do arquivo, esquema, totais e perfil por origem
│   ├── 02_baseline.ipynb     # variáveis, partição temporal e baselines
│   └── 03_modelo.ipynb       # Ridge, comparação, backtest, resíduos e previsão de 2027
├── src/                      # funções reutilizadas pelo pipeline
├── tests/                    # testes do pipeline (dados sintéticos)
└── docs/                     # dicionário de dados, relatórios das Entregas 3, 4 e 5, figuras
```

## Como executar

Requer Python 3.13 (ambiente de referência). Coloque `dados_lapae.xlsx` em `dados/bruto/` (ver `dados/bruto/LEIAME.md`).

```bash
python -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest                   # testes do pipeline
jupyter nbconvert --to notebook --execute --inplace notebooks/01_auditoria.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_baseline.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_modelo.ipynb
```

Execute os notebooks nessa ordem. Todos os caminhos são relativos à raiz do repositório e a semente está fixa (`src/config.py`).
Resultados: `dados/processado/previsao_2027_por_origem.csv`, `previsao_2027_total.csv` e `resultados.json`.

## Decisões de método

- **Variáveis conhecidas de antemão:** origem, mês do ano (e, opcionalmente, tendência e dias úteis). Não há defasagens do alvo, porque os meses-alvo estão 11 a 15 meses além do último dado.
- **Partição temporal:** treino ago/2025–mar/2026 (8 meses), validação abr–jun/2026 (3), teste jul–set/2026 (3, usado uma vez). Backtest de origem móvel como checagem adicional.
- **Sem vazamento:** nível da origem, imputação, escala e codificação são ajustados só no treino, dentro do modelo/`Pipeline`; categorias novas são ignoradas pelo codificador.
- **Baselines:** trivial (média e mediana do treino por origem) e operacional (hipótese: repetir o último mês observado).
- **Modelo:** Ridge sobre o desvio relativo à média de cada origem, com efeito do mês do ano; `alpha = 30` (10 a 100 dão resultado quase igual no backtest).
- **Métrica principal:** MAE do total mensal, em exames. Secundárias: WAPE por origem e viés do total (previsto − real).

## Limites conhecidos

- Só 14 meses: cada mês do ano aparece no máximo duas vezes; outubro a dezembro, uma vez. A sazonalidade não é verificável.
- O horizonte de 11 a 15 meses nunca foi validado (o backtest cobre 1 a 3 meses).
- A diferença entre o modelo e a média histórica por origem é pequena e está dentro do ruído.
- Origens em crescimento (Particulares, São Lucas) tendem a ser subestimadas; o viés do total no backtest é negativo.
- A base oficial não traz município.

## Dados e privacidade

Só contagens mensais agregadas por origem, sem identificação de pacientes. Por serem dados de saúde, o uso depende de autorização do
laboratório e segue a LGPD. A planilha original não é versionada sem autorização (`.gitignore`).
