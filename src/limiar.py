"""Limiar de decisão a partir de custos (B, C) e capacidade k.

O problema é de regressão (total mensal de exames). A decisão binária que ele apoia, hipótese da equipe [H]:
  agir  = reforçar a equipe / reorganizar o mês quando se espera que o volume estoure a capacidade k;
  positivo = mês em que o volume real supera k.
  B = benefício de agir quando o mês de fato estoura (atraso evitado); C = custo de agir quando não estoura.
Probabilidade de estouro: P(Y > k) com Y ~ Normal(previsto, sigma), sigma estimado só com erros fora da amostra
do treino. Age-se quando P(Y > k) >= t*, com t* = C / (B + C)."""
from statistics import NormalDist

import numpy as np
import pandas as pd

from src.config import COL_ALVO, COL_MES

_N = NormalDist()


def limiar_otimo(B: float, C: float) -> float:
    """t* = C / (B + C): age-se se a probabilidade do positivo for pelo menos t*."""
    if B <= 0 or C <= 0:
        raise ValueError("B e C devem ser positivos.")
    return C / (B + C)


def frase_limiar(B: float, C: float, unidade: str = "horas-equipe") -> str:
    t = limiar_otimo(B, C)
    v = lambda x, d: f"{x:.{d}f}".replace(".", ",")  # noqa: E731  (vírgula decimal, como no relatório)
    return (f"Com B = {v(B, 1)} e C = {v(C, 1)} ({unidade}), t* = {v(t, 2)}: vale reforçar o mês quando a chance estimada de "
            f"estourar a capacidade for de pelo menos {t:.0%}, porque deixar de agir num mês que estoura custa "
            f"{v(B / C, 1)} vez(es) o custo de agir à toa.")


def sigma_do_total(oof: pd.DataFrame) -> dict:
    """Dispersão do erro do TOTAL mensal, com previsões fora da amostra do treino (colunas: mes, exames, previsto).
    Usa o maior entre (a) RMS do erro do total por mês e (b) a soma em quadratura dos erros por unidade. (a) captura choques
    comuns a todas as unidades; (b) é a referência se os erros fossem independentes. Com poucos meses, é uma estimativa grosseira [H]."""
    r = oof[COL_ALVO] - oof["previsto"]
    por_mes = oof.assign(res=r).groupby(COL_MES)["res"].sum()
    rms_total = float(np.sqrt(np.mean(por_mes.to_numpy() ** 2)))
    n_unid = oof.groupby(COL_MES).size().mean()
    sigma_u = float(np.sqrt(np.mean(r.to_numpy() ** 2)))
    quad = float(sigma_u * np.sqrt(n_unid))
    return {"sigma_rms_total": rms_total, "sigma_quadratura": quad, "sigma": max(rms_total, quad),
            "n_meses": int(por_mes.shape[0]), "sigma_unidade": sigma_u}


def prob_estouro(previsto_total, k: float, sigma: float):
    previsto_total = np.asarray(previsto_total, dtype=float)
    if sigma <= 0:
        return (previsto_total > k).astype(float)
    return np.array([1 - _N.cdf((k - m) / sigma) for m in previsto_total])


def previsto_limiar_em_exames(k: float, sigma: float, t_star: float) -> float:
    """Total previsto a partir do qual a probabilidade de estouro chega a t*: mu* = k + sigma * Phi^-1(t*)."""
    return k + sigma * _N.inv_cdf(t_star)


def tabela_limiar(totais: pd.DataFrame, k: float, sigma: float, razoes_c_sobre_b, B_ref: float = 1.0) -> pd.DataFrame:
    """Para cada razão C/B: t*, total previsto que dispara a ação, e o resultado nos meses de `totais` (mes, real, previsto)."""
    p = prob_estouro(totais["previsto"], k, sigma)
    real_pos = (totais["real"] > k).to_numpy()
    linhas = []
    for r in razoes_c_sobre_b:
        B, C = B_ref, B_ref * r
        t = limiar_otimo(B, C)
        age = p >= t
        tp, fp = int((age & real_pos).sum()), int((age & ~real_pos).sum())
        fn, tn = int((~age & real_pos).sum()), int((~age & ~real_pos).sum())
        linhas.append({"C/B": r, "t*": round(t, 3), "total previsto que dispara a ação": round(previsto_limiar_em_exames(k, sigma, t), 1),
                       "meses com ação": int(age.sum()), "ação certa (VP)": tp, "ação à toa (FP)": fp,
                       "estouro sem ação (FN)": fn, "sem ação e sem estouro (VN)": tn,
                       "benefício líquido (B=1)": round(B * tp - C * fp, 2),
                       "benefício líquido se nunca agir": 0.0,
                       "benefício líquido se sempre agir": round(B * int(real_pos.sum()) - C * int((~real_pos).sum()), 2)})
    return pd.DataFrame(linhas)


def limiar_efetivo(k: float, sigma: float, t_star: float, previsto_max: float) -> dict:
    """Qual restrição morde primeiro: a econômica (t*) ou a de capacidade (k)?
    Se mu* < k, a ação é disparada ANTES de o previsto alcançar a capacidade (margem de segurança pelo custo assimétrico).
    Se mu* > k, o custo da ação é tão alto que se espera passar da capacidade para agir."""
    mu = previsto_limiar_em_exames(k, sigma, t_star)
    return {"k": k, "mu_estrela": mu, "margem_exames": k - mu, "previsto_max_no_periodo": previsto_max,
            "restricao_que_morde_primeiro": "econômica (t*): age antes de chegar a k" if mu < k else
            "capacidade (k): só age depois de passar de k"}


def calibracao(df: pd.DataFrame, previsto, n_faixas: int = 3) -> pd.DataFrame:
    """Confiabilidade do escore (previsto) por faixa: média prevista x média observada. Razão 1 = calibrado."""
    x = pd.DataFrame({"previsto": np.asarray(previsto, dtype=float), "real": df[COL_ALVO].to_numpy()})
    x["faixa"] = pd.qcut(x["previsto"], q=n_faixas, duplicates="drop", precision=0)
    g = x.groupby("faixa", observed=True).agg(n=("real", "size"), previsto_medio=("previsto", "mean"), real_medio=("real", "mean")).reset_index()
    g["real/previsto"] = g["real_medio"] / g["previsto_medio"]
    g["faixa"] = g["faixa"].astype(str)
    return g


def cobertura_intervalo(df: pd.DataFrame, previsto, sigma_unidade: float, nivel: float = 0.80) -> dict:
    """Fração dos casos em que o real cai em previsto ± z*sigma_unidade. Esperado ~ nível, se o intervalo estiver calibrado."""
    z = _N.inv_cdf(0.5 + nivel / 2)
    dentro = np.abs(df[COL_ALVO].to_numpy() - np.asarray(previsto, dtype=float)) <= z * sigma_unidade
    return {"nivel_nominal": nivel, "cobertura_observada": float(dentro.mean()), "n": int(len(dentro))}
