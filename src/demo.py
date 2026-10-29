"""Dados SINTÉTICOS, usados apenas para demonstrar e testar o pipeline enquanto os dados reais do
LAPAE não chegam. Nada aqui representa o laboratório, e nenhum resultado calculado sobre esses
dados deve ser reportado como resultado do projeto."""
import numpy as np
import pandas as pd

from src.config import COL_DATA, COL_ID, COL_ORIGEM, SEMENTE

ROTULO_DEMO = "MODO DEMONSTRAÇÃO: dados sintéticos, não são dados do LAPAE."

ORIGENS = ["Origem A", "Origem B", "Origem C", "Origem D", "Origem E"]


def gerar_registros_sinteticos(n_meses=12, inicio="2025-10-01", semente=SEMENTE):
    """Gera registros brutos (um por exame) com problemas injetados de propósito: duplicatas
    (mesmo id_registro repetido), datas inválidas e grafias diferentes de origem."""
    rng = np.random.default_rng(semente)
    meses = pd.date_range(inicio, periods=n_meses, freq="MS")
    linhas = []
    for o in ORIGENS:
        nivel = rng.integers(15, 70)
        for k, m in enumerate(meses):
            sazonal = 1.2 if m.month == 10 else 1.0
            n = max(0, int(nivel * sazonal * (1 + 0.03 * k) + rng.normal(0, 4)))
            dias = rng.integers(0, m.days_in_month, size=n)
            for d in dias:
                linhas.append((o, m + pd.Timedelta(days=int(d))))
    df = pd.DataFrame(linhas, columns=[COL_ORIGEM, COL_DATA])
    df.insert(0, COL_ID, np.arange(1, len(df) + 1))
    # Problemas injetados
    dup = df.sample(15, random_state=semente)
    df = pd.concat([df, dup], ignore_index=True)
    df.loc[df.sample(5, random_state=semente + 1).index, COL_DATA] = pd.NaT
    idx = df.sample(8, random_state=semente + 2).index
    df.loc[idx, COL_ORIGEM] = df.loc[idx, COL_ORIGEM].str.lower() + " "
    return df.sample(frac=1, random_state=semente).reset_index(drop=True)
