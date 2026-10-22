# dados/bruto/

Pasta dos relatórios originais enviados pelo LAPAE. **Os arquivos desta pasta não são versionados**
(ver `.gitignore`): são dados de saúde de terceiros, e o uso depende de autorização do demandante (LGPD).

## Como obter novamente

1. Pedir ao demandante (Frederico Torres, LAPAE) o relatório mensal de exames por policlínica ou USF,
   com os municípios cobertos, **agregado e sem identificação de pacientes**.
2. Salvar o(s) arquivo(s) `.csv` ou `.xlsx` nesta pasta, sem editá-los.
3. Registrar na tabela abaixo a data de recebimento, o nome do arquivo e quem enviou.

| Data de recebimento | Arquivo | Enviado por | Período coberto | Observações |
|---|---|---|---|---|
| (nenhum relatório recebido até agora) | | | | |

## Colunas esperadas pelo código (`src/dados.py`)

| Coluna | Descrição |
|---|---|
| `unidade` | Policlínica ou USF que enviou o exame |
| `municipio` | Município da unidade |
| `data_chegada` | Data de chegada do exame ao laboratório |
| `id_registro` | Identificador do registro (opcional; usado para remover duplicatas) |

O formato real dos relatórios ainda é desconhecido. Quando chegarem, ajustar `carregar_bruto()` e
registrar o mapeamento em `docs/dicionario_dados.md`.

## Amostra anonimizada

Enquanto não houver relatórios, o notebook usa dados **sintéticos** (`src/demo.py`), identificados como
demonstração. Quando houver dados reais, incluir aqui uma amostra anonimizada e sem pacientes.
