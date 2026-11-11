"""Engenharia de atributos e segmentação por gasto total."""

from __future__ import annotations

import numpy as np
import pandas as pd

from preprocessing import CATEGORIAS, COLUNAS_GASTO

DIAS_POR_MES = 30.4375  # média do calendário gregoriano
ROTULO_ALTO = "Alto gasto"
ROTULO_DEMAIS = "Demais clientes"
ORDEM_SEGMENTOS = [ROTULO_ALTO, ROTULO_DEMAIS]


def data_referencia(df: pd.DataFrame) -> pd.Timestamp:
    """Proxy da data de observação: último cadastro presente na base.

    A base não documenta a data de coleta. Como o gasto é acumulado até a coleta,
    a coleta é necessariamente >= o último cadastro (2014-06-29). Essa é a proxy
    mais conservadora disponível; limitação: o tempo de relacionamento fica
    subestimado em todo o período entre a coleta real e essa data, o que afeta
    apenas o nível (não a ordenação) do gasto mensal.
    """
    return df["Dt_Customer"].max()


def construir_atributos(df: pd.DataFrame, referencia: pd.Timestamp | None = None) -> pd.DataFrame:
    """Cria gasto total, idade, filhos, tempo de relacionamento, gasto mensal e segmento."""
    referencia = referencia or data_referencia(df)
    d = df.copy()

    d["GastoTotal"] = d[COLUNAS_GASTO].sum(axis=1)

    d["Idade"] = referencia.year - d["Year_Birth"]

    d["TotalFilhos"] = d["Kidhome"] + d["Teenhome"]

    d["TempoRelacionamento"] = (referencia - d["Dt_Customer"]).dt.days / DIAS_POR_MES

    # Divisão por zero: clientes cadastrados na própria data de referência.
    d["GastoMensal"] = np.where(
        d["TempoRelacionamento"] > 0, d["GastoTotal"] / d["TempoRelacionamento"], np.nan
    )

    d["TotalCompras"] = d[["NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases"]].sum(axis=1)

    # Segmentação principal: 25% com maior GastoTotal acumulado (percentil 75).
    # Empates no limite: todos com GastoTotal >= P75 entram em "Alto gasto"
    # (contagem efetiva reportada na análise); na base atual o valor do P75 não
    # coincide com nenhum registro, portanto o grupo fica com exatamente 25%.
    limite = d["GastoTotal"].quantile(0.75)
    d["SegmentoGasto"] = np.where(d["GastoTotal"] >= limite, ROTULO_ALTO, ROTULO_DEMAIS)

    for coluna, nome in CATEGORIAS.items():
        # Participação de cada categoria no gasto individual (0 quando não há gasto).
        d[f"Perc_{coluna}"] = np.where(d["GastoTotal"] > 0, d[coluna] / d["GastoTotal"] * 100, 0.0)

    return d


def adicionar_faixas(df: pd.DataFrame) -> pd.DataFrame:
    """Faixas justificadas para a análise de público-alvo.

    - Renda: quintis (grupos de tamanho semelhante -> estimativas estáveis).
    - Idade: décadas, com o primeiro e o último grupos abertos.
    - Filhos: 0, 1, 2, 3+.
    - Tempo de relacionamento: quartis.
    """
    d = df.copy()
    d["FaixaRenda"] = pd.qcut(
        d["Income"],
        5,
        labels=["Q1 (menor)", "Q2", "Q3", "Q4", "Q5 (maior)"],
    )
    d["FaixaEtaria"] = pd.cut(
        d["Idade"],
        bins=[17, 30, 40, 50, 60, 120],
        labels=["18-29", "30-39", "40-49", "50-59", "60+"],
        right=False,
    )
    d["FaixaFilhos"] = pd.cut(
        d["TotalFilhos"],
        bins=[-1, 0, 1, 2, 10],
        labels=["Sem filhos", "1 filho", "2 filhos", "3+ filhos"],
    )
    d["FaixaTempo"] = pd.qcut(
        d["TempoRelacionamento"],
        4,
        labels=["Q1 (mais recente)", "Q2", "Q3", "Q4 (mais antigo)"],
    )
    d["PossuiFilhos"] = np.where(d["TotalFilhos"] > 0, "Com filhos", "Sem filhos")
    return d
