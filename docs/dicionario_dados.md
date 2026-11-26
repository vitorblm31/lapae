# Dicionário de dados

Contrato de dados completo no PDF da Entrega 4 (seção 1). Chave: (`unidade`, `mes`). Uma linha = exames de uma unidade em um mês.
Marcação: **[F]** fato relatado pelo demandante, **[H]** hipótese da equipe, **[L]** lacuna.

## Registros brutos (`dados/bruto/`)

| Coluna | Tipo | Descrição | Marca |
|---|---|---|---|
| `unidade` | texto | Policlínica ou USF de origem | [H] nome exato a confirmar |
| `municipio` | texto | Município da unidade | [L] lista virá nos relatórios |
| `data_chegada` | data | Data de chegada do exame ao laboratório | [F] fica registrada no sistema |
| `id_registro` | texto/número | Identificador do registro, se existir | [L] |

## Base analítica (`dados/processado/base_mensal.csv`)

| Coluna | Tipo | Descrição |
|---|---|---|
| `unidade` | texto | Chave, parte 1 |
| `mes` | data (1º dia do mês) | Chave, parte 2 |
| `municipio` | texto | Município da unidade |
| `exames` | inteiro (NaN se não houver registro) | **Alvo**: exames com data de chegada no mês. Ausência não é convertida em zero. |

## Variáveis derivadas (`src/variaveis.py`)

| Variável | Definição | Permitida? |
|---|---|---|
| `lag_1`, `lag_2`, `lag_3` | Exames da unidade 1, 2 e 3 meses antes | Sim, condicionada ao corte de 4 dias [L] |
| `media_movel_3` | Média dos 3 meses anteriores (shift antes da janela) | Sim |
| `mes_do_ano` | Mês do calendário (1 a 12), tratado como categoria | Sim |
| `dias_uteis` | Dias úteis do mês-alvo, sem feriados | Sim |

Variáveis proibidas por vazamento (alvo, temporal, partição ou consequência da decisão) estão no PDF, seção 4.
