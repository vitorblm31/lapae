"""Primeiro modelo de regressão: Ridge sobre o desvio relativo à média de cada origem.

    y(origem, mês) / média(origem) - 1 = b0 + b_mês do ano (+ b1 * tendência, opcional) + erro
    previsão = média(origem) * (1 + valor estimado)

A média da origem fixa o nível de cada série (a escala das origens varia de poucos exames a centenas),
e o Ridge estima, de forma regularizada e compartilhada entre as origens, o efeito do mês do ano.
A tendência fica desligada por padrão: extrapolá-la 11 a 15 meses à frente, com 14 meses de histórico, não pode ser validada.
Estimação: minimiza a soma de (z - Xb)^2 mais alfa vezes a soma de b^2, com o intercepto fora da penalidade.
O alfa é escolhido por validação cruzada com origem móvel por mês, usando só o treino."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import COL_ORIGEM, SEMENTE
from src.particao import splits_por_mes

ALPHAS = (1.0, 3.0, 10.0, 30.0, 100.0)


class ModeloRelativo(BaseEstimator, RegressorMixin):
    """Ridge sobre o desvio relativo à média da origem. Tudo é aprendido só com os dados do fit."""

    def __init__(self, alpha: float = 10.0, usar_tendencia: bool = False):
        self.alpha = alpha
        self.usar_tendencia = usar_tendencia

    def fit(self, X: pd.DataFrame, y):
        X = X.reset_index(drop=True)
        y = pd.Series(np.asarray(y, dtype=float))
        self.medias_ = y.groupby(X[COL_ORIGEM].to_numpy()).mean()
        self.media_global_ = float(y.mean())
        mu = X[COL_ORIGEM].map(self.medias_).to_numpy(dtype=float)
        z = np.where(mu > 0, y.to_numpy() / np.where(mu > 0, mu, 1.0) - 1.0, 0.0)
        blocos = [("cat", OneHotEncoder(handle_unknown="ignore"), ["mes_do_ano"])]
        if self.usar_tendencia:
            blocos.insert(0, ("num", Pipeline([("imputacao", SimpleImputer(strategy="median")),
                                               ("escala", StandardScaler())]), ["tendencia"]))
        pre = ColumnTransformer(blocos)
        self.pipeline_ = Pipeline([("pre", pre), ("ridge", Ridge(alpha=self.alpha, random_state=SEMENTE))]).fit(X, z)
        return self

    def predict(self, X: pd.DataFrame):
        mu = X[COL_ORIGEM].map(self.medias_).fillna(self.media_global_).to_numpy(dtype=float)
        z = self.pipeline_.predict(X.reset_index(drop=True))
        return np.clip(mu * (1.0 + z), 0.0, None)


def ajustar_modelo(treino: pd.DataFrame, alphas=ALPHAS, n_splits: int = 2) -> GridSearchCV:
    """Escolhe o alfa por validação cruzada temporal (mês inteiro por dobra) e reajusta no treino."""
    X = treino.reset_index(drop=True)
    busca = GridSearchCV(ModeloRelativo(), {"alpha": list(alphas)}, cv=splits_por_mes(X, n_splits=n_splits),
                         scoring="neg_mean_absolute_error", refit=True)
    return busca.fit(X, X["exames"])


def prever(modelo, df: pd.DataFrame):
    return modelo.predict(df)
