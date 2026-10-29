"""Configuração central: caminhos relativos à raiz do repositório e constantes do projeto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BRUTO = RAIZ / "dados" / "bruto"
PROCESSADO = RAIZ / "dados" / "processado"

SEMENTE = 42

# Contrato de dados: série = origem do exame (laboratório, clínica ou segmento); linha = origem x mês
COL_ORIGEM = "origem"
COL_ID = "id_registro"         # opcional, usado para remover duplicatas nos registros por exame
COL_DATA = "data_chegada"      # só nos registros por exame
COL_MES = "mes"                # primeiro dia do mês
COL_ALVO = "exames"            # exames recebidos no mês

CHAVE = [COL_ORIGEM, COL_MES]

# Variáveis conhecidas de antemão (não dependem do alvo nem de meses futuros)
NUMERICAS = ["tendencia", "dias_uteis"]
CATEGORICAS = [COL_ORIGEM, "mes_do_ano"]
ATRIBUTOS = NUMERICAS + CATEGORICAS

# Partição temporal (em meses)
N_MESES_VALIDACAO = 3
N_MESES_TESTE = 3

# Meses a prever (pedido da equipe) e capacidade média informada pelo demandante
MESES_PREVISAO = ["2027-08-01", "2027-09-01", "2027-10-01", "2027-11-01", "2027-12-01"]
CAPACIDADE_MEDIA = 1850
