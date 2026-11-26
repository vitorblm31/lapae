"""Dados SINTÉTICOS, usados apenas para demonstrar e testar o pipeline enquanto os relatórios reais
do demandante não chegam. Nada aqui representa o LAPAE, e nenhum resultado calculado sobre esses
dados deve ser reportado como resultado do projeto."""
import numpy as np
import pandas as pd

from src.config import COL_DATA, COL_ID, COL_MUNICIPIO, COL_UNIDADE, SEMENTE

ROTULO_DEMO = "MODO DEMONSTRAÇÃO: dados sintéticos, não são dados do LAPAE."


def gerar_registros_sinteticos(n_unidades=10, n_meses=12, inicio="2025-10-01", semente=SEMENTE):
    """Gera registros brutos (um por exame) com problemas injetados de propósito:
    duplicatas (mesmo id_registro repetido), datas inválidas e unidade com grafia diferente."""
    rng = np.random.default_rng(semente)
    meses = pd.date_range(inicio, periods=n_meses, freq="MS")
    unidades = [f"Unidade {i:02d}" for i in range(1, n_unidades + 1)]
    municipios = {u: f"Município {1 + i % 4}" for i, u in enumerate(unidades)}
    linhas = []
    for u in unidades:
        nivel = rng.integers(40, 160)
        for k, m in enumerate(meses):
            n = max(0, int(nivel * (1 + 0.04 * k) + rng.normal(0, 8)))
            dias = rng.integers(0, m.days_in_month, size=n)
            for d in dias:
                linhas.append((u, municipios[u], m + pd.Timedelta(days=int(d))))
    df = pd.DataFrame(linhas, columns=[COL_UNIDADE, COL_MUNICIPIO, COL_DATA])
    df.insert(0, COL_ID, np.arange(1, len(df) + 1))
    # Problemas injetados
    dup = df.sample(15, random_state=semente)
    df = pd.concat([df, dup], ignore_index=True)
    df.loc[df.sample(5, random_state=semente + 1).index, COL_DATA] = pd.NaT
    idx = df.sample(8, random_state=semente + 2).index
    df.loc[idx, COL_UNIDADE] = df.loc[idx, COL_UNIDADE].str.upper() + " "
    return df.sample(frac=1, random_state=semente).reset_index(drop=True)
