# Dicionário de dados

Série = origem do exame. Linha da base analítica = uma origem em um mês. Chave: (`origem`, `mes`).
Marcação: **[F]** fato relatado pelo demandante, **[H]** hipótese da equipe, **[L]** lacuna.

## Entrada (`dados/bruto/dados_lapae.xlsx`)

Planilha larga: 6 linhas (origens) e 14 colunas de mês (`Agosto(2025)` a `Setembro(2026)`), valores inteiros.
Origens: São Lucas, Roseane Dore, Maurílio de Almeida, Viver Mais, SUS, Particulares. Unidade: exames recebidos no mês [L: confirmar com o demandante se "recebidos" é a data de chegada ou de cadastro].

## Base analítica (em memória; `src/dados.py`)

| Coluna | Tipo | Descrição |
|---|---|---|
| `origem` | texto | Origem do exame, sem acentos e em maiúsculas |
| `mes` | data (1º dia do mês) | Mês |
| `exames` | inteiro (NaN se não houver registro) | **Alvo**: exames do mês. Ausência não é convertida em zero. |

## Variáveis (`src/variaveis.py`), todas conhecidas de antemão

| Variável | Definição | Uso |
|---|---|---|
| `mes_do_ano` | Mês do calendário (1 a 12), categoria | Sim, no modelo |
| `tendencia` | Meses desde o primeiro mês da base | Disponível; desligada por padrão (extrapolação de 11 a 15 meses não validável) |
| `dias_uteis` | Dias úteis do mês, sem feriados | Calculada; não usada no modelo atual |
| `origem` | Identificação da série | Sim, fixa o nível (média da origem no treino) |

Defasagens do alvo e médias móveis **não são usadas**: para prever 11 a 15 meses à frente, elas não existem nos meses-alvo.
Variáveis proibidas (alvo, temporal, partição, consequência da decisão): ver relatórios das Entregas 4 e 5.

## Saídas (`dados/processado/`)

`previsao_2027_por_origem.csv`, `previsao_2027_total.csv`, `resultados.json`, `baselines_validacao.csv`.
