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

# ---- Entrega 6: modelagem, limiar, erros e equidade ----
RESULTADOS = RAIZ / "resultados"

# Capacidade k: [F] média de 1.850 exames (demandante); [L] unidade de tempo (mensal?) e o que limita, a confirmar.
CAPACIDADE_K = 1850

# Custos do erro, em unidade comum (horas-equipe). [L] NÃO foram estimados com o demandante.
# Valores abaixo são HIPÓTESE de trabalho; o relatório traz análise de sensibilidade (RAZOES_C_SOBRE_B).
# B = benefício de reforçar a equipe quando o mês de fato estoura a capacidade (evita atraso).
# C = custo de reforçar quando o mês não estoura (capacidade ociosa).
B_HIPOTESE = 2.0
C_HIPOTESE = 1.0
RAZOES_C_SOBRE_B = [0.25, 0.5, 1.0, 2.0]

# Validação cruzada com janela expansiva (origem móvel), em meses
MIN_MESES_TREINO_CV = 2

# Regra "complexidade precisa se pagar" [H]: ganho mínimo relativo de MAE sobre o melhor baseline na validação
GANHO_MINIMO_RELATIVO = 0.10

# Equidade [H]: diferença de WAPE entre grupos acima da qual o resultado é sinalizado
LIMITE_RAZAO_WAPE_GRUPOS = 1.5
MIN_LINHAS_GRUPO = 4
NIVEL_INTERVALO = 0.80
