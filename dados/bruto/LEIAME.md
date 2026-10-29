# dados/bruto/

Pasta dos dados originais do LAPAE. **A planilha desta pasta não é versionada** (ver `.gitignore`): são dados de
saúde de terceiros, e o uso depende de autorização do demandante (LGPD).

## Como obter novamente

1. Pedir ao demandante (Frederico Torres, LAPAE) a planilha `dados_lapae.xlsx`.
2. Salvar nesta pasta, sem editar.

| Data de recebimento | Arquivo | Período coberto | Observações |
|---|---|---|---|
| (preencher a data) | `dados_lapae.xlsx` | ago/2025 a set/2026 (14 meses) | 6 origens, contagem mensal de exames, sem município |

## Formato lido por `src/dados.py`

**(c) Planilha larga (formato atual):** primeira coluna = origem; uma coluna por mês, com cabeçalho `Agosto(2025)`, `Setembro(2025)` etc.

Também são aceitos: (a) registros por exame (`origem`, `data_chegada`, `id_registro` opcional) e (b) contagens em formato longo
(`origem`, `mes`, `exames`).
