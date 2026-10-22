"""Configuração central: caminhos relativos à raiz do repositório e constantes do projeto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BRUTO = RAIZ / "dados" / "bruto"
PROCESSADO = RAIZ / "dados" / "processado"

SEMENTE = 42

# Colunas do contrato de dados (unidade x mês)
COL_UNIDADE = "unidade"
COL_MUNICIPIO = "municipio"
COL_ID = "id_registro"
COL_DATA = "data_chegada"
COL_MES = "mes"
COL_ALVO = "exames"

# Variáveis candidatas (ver docs/dicionario_dados.md)
NUMERICAS = ["lag_1", "lag_2", "lag_3", "media_movel_3", "dias_uteis"]
CATEGORICAS = [COL_UNIDADE, COL_MUNICIPIO, "mes_do_ano"]

# Partição temporal (meses): proposta inicial, ajustável quando a série real chegar
N_MESES_VALIDACAO = 2
N_MESES_TESTE = 2
