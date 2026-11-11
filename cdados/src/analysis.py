"""Análises comparativas, de público-alvo e testes estatísticos.

Todas as funções recebem o DataFrame já tratado e com atributos derivados
(`preprocessing.limpar` + `feature_engineering.construir_atributos/adicionar_faixas`).
Nenhum resultado é fixado no código: tudo é recalculado a partir da base.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from feature_engineering import ORDEM_SEGMENTOS, ROTULO_ALTO, ROTULO_DEMAIS
from preprocessing import CANAIS, CATEGORIAS, COLUNAS_GASTO

ALFA = 0.05


# ----------------------------------------------------------------------------- auxiliares
def _grupos(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    alto = df.loc[df["SegmentoGasto"] == ROTULO_ALTO]
    demais = df.loc[df["SegmentoGasto"] == ROTULO_DEMAIS]
    return alto, demais


def wilson_ic(sucessos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson para uma proporção (robusto com n pequeno)."""
    if n == 0:
        return (np.nan, np.nan)
    p = sucessos / n
    denom = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denom
    margem = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centro - margem), min(1.0, centro + margem))


def _rank_biserial(u: float, n1: int, n2: int) -> float:
    """Tamanho de efeito do Mann-Whitney: r = 2U/(n1*n2) - 1 (positivo = grupo 1 maior)."""
    return 2 * u / (n1 * n2) - 1


def magnitude_r(r: float) -> str:
    r = abs(r)
    if r < 0.1:
        return "desprezível"
    if r < 0.3:
        return "pequeno"
    if r < 0.5:
        return "médio"
    return "grande"


def magnitude_v(v: float) -> str:
    if v < 0.1:
        return "desprezível"
    if v < 0.3:
        return "pequeno"
    if v < 0.5:
        return "médio"
    return "grande"


def bh_correcao(p: pd.Series) -> pd.Series:
    """Correção de Benjamini-Hochberg (FDR); NaN preservados."""
    validos = p.dropna()
    m = len(validos)
    if m == 0:
        return p.copy()
    ordem = validos.sort_values()
    ranks = np.arange(1, m + 1)
    ajustado = np.minimum.accumulate((ordem.values * m / ranks)[::-1])[::-1]
    resultado = pd.Series(np.clip(ajustado, 0, 1), index=ordem.index)
    return p.where(p.isna(), resultado.reindex(p.index))


# ----------------------------------------------------------------------------- segmentação
def resumo_segmentos(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela central: tamanho, gasto e participação de cada segmento."""
    limite = df["GastoTotal"].quantile(0.75)
    total_geral = df["GastoTotal"].sum()
    registros = []
    for rotulo in ORDEM_SEGMENTOS + ["Total"]:
        sub = df if rotulo == "Total" else df[df["SegmentoGasto"] == rotulo]
        registros.append(
            {
                "Grupo": rotulo,
                "N_clientes": len(sub),
                "Percentual_clientes": len(sub) / len(df) * 100,
                "Limite_P75_GastoTotal": limite,
                "Gasto_acumulado": sub["GastoTotal"].sum(),
                "Participacao_gasto_total": sub["GastoTotal"].sum() / total_geral * 100,
                "Media_gasto": sub["GastoTotal"].mean(),
                "Mediana_gasto": sub["GastoTotal"].median(),
                "Desvio_gasto": sub["GastoTotal"].std(),
                "Media_gasto_mensal": sub["GastoMensal"].mean(),
                "Mediana_gasto_mensal": sub["GastoMensal"].median(),
            }
        )
    return pd.DataFrame(registros).round(2)


def comparacao_grupos(df: pd.DataFrame) -> pd.DataFrame:
    """Médias e medianas por grupo para as variáveis centrais das comparações."""
    variaveis = {
        "Income": "Renda anual",
        "Idade": "Idade (anos)",
        "TotalFilhos": "Número de filhos",
        "TempoRelacionamento": "Tempo de relacionamento (meses)",
        "GastoTotal": "Gasto total (u.m.)",
        "GastoMensal": "Gasto mensal (u.m./mês)",
        "TotalCompras": "Total de compras (n)",
        "NumDealsPurchases": "Compras com desconto (n)",
        "NumWebVisitsMonth": "Visitas ao site por mês (n)",
    }
    alto, demais = _grupos(df)
    registros = []
    for coluna, nome in variaveis.items():
        a = alto[coluna].dropna()
        b = demais[coluna].dropna()
        registros.append(
            {
                "Variavel": nome,
                "N_alto": len(a),
                "Media_alto": a.mean(),
                "Mediana_alto": a.median(),
                "N_demais": len(b),
                "Media_demais": b.mean(),
                "Mediana_demais": b.median(),
                "Diferenca_medias": a.mean() - b.mean(),
                "Razao_medias": a.mean() / b.mean() if b.mean() else np.nan,
                "Razao_medianas": a.median() / b.median() if b.median() else np.nan,
            }
        )
    return pd.DataFrame(registros).round(3)


def perfil_categorico(df: pd.DataFrame) -> pd.DataFrame:
    """Distribuição das variáveis categóricas dentro de cada grupo e taxa de alto gasto."""
    registros = []
    for coluna, nome in [
        ("Escolaridade", "Escolaridade"),
        ("EstadoCivil", "Estado civil"),
        ("FaixaFilhos", "Quantidade de filhos"),
    ]:
        contagem = df.groupby([coluna, "SegmentoGasto"], observed=True).size().unstack(fill_value=0)
        totais = contagem.sum()
        for categoria, linha in contagem.iterrows():
            n = int(linha.sum())
            n_alto = int(linha.get(ROTULO_ALTO, 0))
            n_demais = int(linha.get(ROTULO_DEMAIS, 0))
            registros.append(
                {
                    "Dimensao": nome,
                    "Categoria": str(categoria),
                    "N": n,
                    "Percentual_dentro_alto": n_alto / totais[ROTULO_ALTO] * 100,
                    "Percentual_dentro_demais": n_demais / totais[ROTULO_DEMAIS] * 100,
                    "Taxa_alto_gasto": n_alto / n * 100,
                }
            )
    return pd.DataFrame(registros).round(2)


# ----------------------------------------------------------------------------- canais
def analise_canais(df: pd.DataFrame) -> pd.DataFrame:
    """Compras por canal (quantidade), por grupo. Não há valor monetário por canal na base."""
    registros = []
    for coluna, nome in CANAIS.items():
        for rotulo in ORDEM_SEGMENTOS:
            sub = df[df["SegmentoGasto"] == rotulo]
            total_grupo = sub[list(CANAIS)].to_numpy().sum()
            registros.append(
                {
                    "Canal": nome,
                    "Grupo": rotulo,
                    "N_clientes": len(sub),
                    "Total_compras": int(sub[coluna].sum()),
                    "Media_por_cliente": sub[coluna].mean(),
                    "Mediana_por_cliente": sub[coluna].median(),
                    "Participacao_no_grupo": sub[coluna].sum() / total_grupo * 100,
                    "Perc_clientes_com_compra": (sub[coluna] > 0).mean() * 100,
                }
            )
    return pd.DataFrame(registros).round(2)


def adicionar_canal_predominante(df: pd.DataFrame) -> pd.DataFrame:
    """Cria a coluna CanalPredominante (canal com mais compras do cliente)."""
    d = df.copy()
    d["CanalPredominante"] = (
        d[list(CANAIS)].rename(columns=CANAIS).idxmax(axis=1).where(d["TotalCompras"] > 0, "Sem compras")
    )
    return d


def canal_predominante(df: pd.DataFrame) -> pd.DataFrame:
    """Canal com maior número de compras por cliente, distribuído por segmento."""
    d = df if "CanalPredominante" in df.columns else adicionar_canal_predominante(df)
    tabela = (
        d.groupby(["CanalPredominante", "SegmentoGasto"], observed=True)
        .size()
        .unstack(fill_value=0)
    )
    tabela["Total"] = tabela.sum(axis=1)
    tabela["Perc_alto"] = tabela[ROTULO_ALTO] / tabela[ROTULO_ALTO].sum() * 100
    tabela["Perc_demais"] = tabela[ROTULO_DEMAIS] / tabela[ROTULO_DEMAIS].sum() * 100
    return tabela.round(2)


# ----------------------------------------------------------------------------- descontos
def analise_descontos(df: pd.DataFrame) -> pd.DataFrame:
    """Compras com ofertas/descontos (NumDealsPurchases), por grupo."""
    variavel = "NumDealsPurchases"
    registros = []
    for rotulo in ORDEM_SEGMENTOS:
        sub = df[df["SegmentoGasto"] == rotulo][variavel]
        usam = sub > 0
        registros.append(
            {
                "Grupo": rotulo,
                "N_clientes": len(sub),
                "Media": sub.mean(),
                "Mediana": sub.median(),
                "Desvio_padrao": sub.std(),
                "Maximo": sub.max(),
                "N_usuarios": int(usam.sum()),
                "Perc_usuarios": usam.mean() * 100,
                "Media_entre_usuarios": sub[usam].mean() if usam.any() else np.nan,
                "Mediana_entre_usuarios": sub[usam].median() if usam.any() else np.nan,
                "Total_de_compras_com_desconto": int(sub.sum()),
            }
        )
    return pd.DataFrame(registros).round(2)


def distribuicao_descontos(df: pd.DataFrame) -> pd.DataFrame:
    """Distribuição do número de compras com desconto (0 a 5+), em % por grupo."""
    faixas = pd.cut(df["NumDealsPurchases"], [-1, 0, 1, 2, 3, 4, 99],
                    labels=["0", "1", "2", "3", "4", "5+"])
    tabela = (pd.crosstab(faixas, df["SegmentoGasto"], normalize="columns") * 100).round(2)
    tabela.index.name = "Compras_com_desconto"
    return tabela


# ----------------------------------------------------------------------------- categorias
def analise_categorias(df: pd.DataFrame) -> pd.DataFrame:
    """Gasto por categoria de produto, por grupo, e participação na cesta de cada grupo."""
    alto, demais = _grupos(df)
    total_geral = df[COLUNAS_GASTO].to_numpy().sum()
    registros = []
    for coluna, nome in CATEGORIAS.items():
        total_cat = df[coluna].sum()
        registros.append(
            {
                "Categoria": nome,
                "Gasto_total": int(total_cat),
                "Perc_gasto_global": total_cat / total_geral * 100,
                "Media_alto": alto[coluna].mean(),
                "Mediana_alto": alto[coluna].median(),
                "Media_demais": demais[coluna].mean(),
                "Mediana_demais": demais[coluna].median(),
                "Perc_dentro_cesta_alto": alto[coluna].sum() / alto[COLUNAS_GASTO].to_numpy().sum() * 100,
                "Perc_dentro_cesta_demais": demais[coluna].sum() / demais[COLUNAS_GASTO].to_numpy().sum() * 100,
                "Perc_do_gasto_da_categoria_no_alto": alto[coluna].sum() / total_cat * 100,
                "Razao_medias": alto[coluna].mean() / demais[coluna].mean(),
            }
        )
    return pd.DataFrame(registros).round(2)


# ----------------------------------------------------------------------------- público-alvo
def publico_alvo(df: pd.DataFrame) -> pd.DataFrame:
    """Taxa de alto gasto (P(alto | categoria)), participação nos altos e lift por faixa."""
    taxa_base = (df["SegmentoGasto"] == ROTULO_ALTO).mean() * 100
    n_alto_total = int((df["SegmentoGasto"] == ROTULO_ALTO).sum())
    registros = []
    for coluna, nome in [
        ("FaixaRenda", "Faixa de renda"),
        ("FaixaEtaria", "Faixa etária"),
        ("Escolaridade", "Escolaridade"),
        ("EstadoCivil", "Estado civil"),
        ("FaixaFilhos", "Quantidade de filhos"),
        ("FaixaTempo", "Tempo de relacionamento"),
    ]:
        for categoria, sub in df.groupby(coluna, observed=True):
            n = len(sub)
            n_alto = int((sub["SegmentoGasto"] == ROTULO_ALTO).sum())
            taxa = n_alto / n * 100
            inf, sup = wilson_ic(n_alto, n)
            registros.append(
                {
                    "Dimensao": nome,
                    "Categoria": str(categoria),
                    "N": n,
                    "N_alto_gasto": n_alto,
                    "Taxa_alto_gasto": taxa,
                    "IC95_inf": inf * 100,
                    "IC95_sup": sup * 100,
                    "Perc_dos_altos": n_alto / n_alto_total * 100,
                    "Lift": taxa / taxa_base,
                }
            )
    return pd.DataFrame(registros).round(2)


def combinacoes_perfis(df: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    """Combinações renda x filhos x escolaridade, ordenadas pela taxa de alto gasto.

    Só são mantidas células com n >= min_n para evitar proporções instáveis.
    """
    d = df.dropna(subset=["FaixaRenda", "FaixaFilhos", "Escolaridade"]).copy()
    d["EscolaridadeGrupo"] = np.where(
        d["Escolaridade"].isin(["Graduação", "Ciclo 2", "Mestrado", "Doutorado"]),
        "Ensino superior",
        "Até ensino básico",
    )
    taxa_base = (d["SegmentoGasto"] == ROTULO_ALTO).mean() * 100
    n_alto_total = int((d["SegmentoGasto"] == ROTULO_ALTO).sum())
    tabela = (
        d.groupby(["FaixaRenda", "FaixaFilhos", "EscolaridadeGrupo"], observed=True)
        .agg(N=("ID", "size"), N_alto=("SegmentoGasto", lambda s: (s == ROTULO_ALTO).sum()))
        .reset_index()
    )
    tabela = tabela[tabela["N"] >= min_n].copy()
    tabela["Taxa_alto_gasto"] = tabela["N_alto"] / tabela["N"] * 100
    tabela["Perc_dos_altos"] = tabela["N_alto"] / n_alto_total * 100
    tabela["Lift"] = tabela["Taxa_alto_gasto"] / taxa_base
    tabela["Perfil"] = (
        tabela["FaixaRenda"].astype(str) + " | " + tabela["FaixaFilhos"].astype(str) + " | " + tabela["EscolaridadeGrupo"]
    )
    colunas = ["Perfil", "N", "N_alto", "Taxa_alto_gasto", "Perc_dos_altos", "Lift"]
    return tabela.sort_values("Taxa_alto_gasto", ascending=False)[colunas].round(2).reset_index(drop=True)


def combinacoes_renda_filhos(df: pd.DataFrame) -> pd.DataFrame:
    """Cruzamento completo renda (quintis) x filhos: n, taxa de alto gasto e lift."""
    d = df.dropna(subset=["FaixaRenda", "FaixaFilhos"])
    taxa_base = (d["SegmentoGasto"] == ROTULO_ALTO).mean() * 100
    tabela = (
        d.groupby(["FaixaRenda", "FaixaFilhos"], observed=True)
        .agg(N=("ID", "size"), N_alto=("SegmentoGasto", lambda s: (s == ROTULO_ALTO).sum()))
        .reset_index()
    )
    tabela["Taxa_alto_gasto"] = tabela["N_alto"] / tabela["N"] * 100
    tabela["Lift"] = tabela["Taxa_alto_gasto"] / taxa_base
    return tabela.round(2)


def matriz_renda_idade(df: pd.DataFrame) -> pd.DataFrame:
    """Taxa de alto gasto (%) por faixa de renda x faixa etária (para mapa de calor)."""
    d = df.dropna(subset=["FaixaRenda", "FaixaEtaria"])
    tabela = (
        d.assign(alto=(d["SegmentoGasto"] == ROTULO_ALTO).astype(float) * 100)
        .pivot_table(index="FaixaRenda", columns="FaixaEtaria", values="alto", aggfunc="mean", observed=True)
        .reindex(index=d["FaixaRenda"].cat.categories)
    )
    return tabela.round(1)


# ----------------------------------------------------------------------------- testes
def verificacao_premissas(df: pd.DataFrame) -> pd.DataFrame:
    """Assimetria, normalidade (Shapiro-Wilk) e homogeneidade de variâncias (Levene).

    Justifica o uso de testes não paramétricos. Com n > 30 o Teorema Central do Limite
    ampararia a comparação de médias, mas a assimetria forte torna a mediana e o
    Mann-Whitney mais informativos para estas variáveis.
    """
    alto, demais = _grupos(df)
    registros = []
    for coluna, nome in [
        ("Income", "Renda"),
        ("Idade", "Idade"),
        ("GastoTotal", "Gasto total"),
        ("GastoMensal", "Gasto mensal"),
        ("TotalFilhos", "Número de filhos"),
        ("TempoRelacionamento", "Tempo de relacionamento"),
    ]:
        a = alto[coluna].dropna()
        b = demais[coluna].dropna()
        shapiro_alto = stats.shapiro(a.sample(min(len(a), 5000), random_state=42)).pvalue
        shapiro_demais = stats.shapiro(b.sample(min(len(b), 5000), random_state=42)).pvalue
        levene = stats.levene(a, b).pvalue
        registros.append(
            {
                "Variavel": nome,
                "Assimetria_alto": a.skew(),
                "Assimetria_demais": b.skew(),
                "Shapiro_p_alto": shapiro_alto,
                "Shapiro_p_demais": shapiro_demais,
                "Levene_p": levene,
                "Normalidade": "Rejeitada em pelo menos um grupo"
                if min(shapiro_alto, shapiro_demais) < ALFA
                else "Não rejeitada",
                "Variancias": "Desiguais" if levene < ALFA else "Homogêneas",
            }
        )
    return pd.DataFrame(registros).round(6)


def testes_estatisticos(df: pd.DataFrame) -> pd.DataFrame:
    """Testes com pergunta concreta, premissas verificadas e tamanho de efeito."""
    alto, demais = _grupos(df)
    registros = []

    def mann_whitney(coluna, nome, pergunta):
        a = alto[coluna].dropna()
        b = demais[coluna].dropna()
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        r = _rank_biserial(u, len(a), len(b))
        registros.append(
            {
                "Pergunta": pergunta,
                "Variaveis": nome,
                "Teste": "Mann-Whitney U",
                "Hipotese_nula": f"Distribuição de {nome} é igual nos dois grupos",
                "Estatistica": u,
                "p_valor": p,
                "Tamanho_efeito": r,
                "Metrica_efeito": f"r rank-biserial ({magnitude_r(r)})",
            }
        )

    def qui_quadrado(coluna, nome, pergunta):
        sub = df.dropna(subset=[coluna])
        tabela = pd.crosstab(sub[coluna], sub["SegmentoGasto"])
        chi2, p, gl, _ = stats.chi2_contingency(tabela)
        v = np.sqrt(chi2 / (tabela.to_numpy().sum() * (min(tabela.shape) - 1)))
        registros.append(
            {
                "Pergunta": pergunta,
                "Variaveis": nome,
                "Teste": f"Qui-quadrado (gl={gl})",
                "Hipotese_nula": f"{nome} é independente do segmento de gasto",
                "Estatistica": chi2,
                "p_valor": p,
                "Tamanho_efeito": v,
                "Metrica_efeito": f"V de Cramér ({magnitude_v(v)})",
            }
        )

    mann_whitney("Income", "Renda", "A renda difere entre alto gasto e demais clientes?")
    mann_whitney("Idade", "Idade", "A idade difere entre os grupos?")
    mann_whitney("TotalFilhos", "Número de filhos", "O número de filhos difere entre os grupos?")
    mann_whitney("TempoRelacionamento", "Tempo de relacionamento",
                 "O tempo de relacionamento difere entre os grupos?")
    mann_whitney("GastoMensal", "Gasto mensal", "O gasto mensal normalizado difere entre os grupos?")
    mann_whitney("NumDealsPurchases", "Compras com desconto",
                 "O uso de compras com desconto difere entre os grupos?")
    mann_whitney("NumWebVisitsMonth", "Visitas ao site por mês",
                 "A intensidade de visitas ao site difere entre os grupos?")

    qui_quadrado("Escolaridade", "Escolaridade", "A escolaridade é independente do segmento?")
    qui_quadrado("EstadoCivil", "Estado civil", "O estado civil é independente do segmento?")
    qui_quadrado("FaixaRenda", "Faixa de renda", "A faixa de renda é independente do segmento?")
    qui_quadrado("PossuiFilhos", "Possui filhos", "Ter filhos é independente do segmento?")
    qui_quadrado("FaixaEtaria", "Faixa etária", "A faixa etária é independente do segmento?")
    qui_quadrado("CanalPredominante", "Canal predominante",
                 "O canal predominante de compra é independente do segmento?")

    tabela = pd.DataFrame(registros)
    tabela["p_ajustado_BH"] = bh_correcao(tabela["p_valor"])
    tabela["Interpretacao"] = np.where(
        tabela["p_ajustado_BH"] < ALFA,
        "Diferença/associação estatisticamente significativa (p ajustado < 0,05)",
        "Sem evidência de diferença/associação (p ajustado >= 0,05)",
    )
    return tabela.round(6)


def correlacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Correlações de Spearman (robustas a não normalidade) com correção BH."""
    alvos = {
        "Income": "Renda anual",
        "Idade": "Idade",
        "TotalFilhos": "Número de filhos",
        "TempoRelacionamento": "Tempo de relacionamento",
        "TotalCompras": "Total de compras",
        "NumDealsPurchases": "Compras com desconto",
        "NumWebVisitsMonth": "Visitas ao site por mês",
        "NumCatalogPurchases": "Compras por catálogo",
    }
    registros = []
    for desfecho, nome_desfecho in [("GastoTotal", "Gasto total"), ("GastoMensal", "Gasto mensal")]:
        for coluna, nome in alvos.items():
            sub = df[[desfecho, coluna]].dropna()
            rho, p = stats.spearmanr(sub[desfecho], sub[coluna])
            registros.append(
                {
                    "Desfecho": nome_desfecho,
                    "Variavel": nome,
                    "N": len(sub),
                    "Spearman_rho": rho,
                    "p_valor": p,
                    "Magnitude": magnitude_r(rho),
                }
            )
    tabela = pd.DataFrame(registros)
    tabela["p_ajustado_BH"] = bh_correcao(tabela["p_valor"])
    return tabela.round(6)


def regressao_loglog(df: pd.DataFrame) -> pd.DataFrame:
    """Elasticidade renda-gasto: OLS de log(GastoTotal) em log(Renda) e controles."""
    import statsmodels.formula.api as smf

    sub = df.dropna(subset=["Income", "GastoTotal", "Idade", "TotalFilhos"]).copy()
    sub = sub[(sub["Income"] > 0) & (sub["GastoTotal"] > 0)]
    sub["log_gasto"] = np.log(sub["GastoTotal"])
    sub["log_renda"] = np.log(sub["Income"])

    modelos = {
        "M1: log(Gasto) ~ log(Renda)": smf.ols("log_gasto ~ log_renda", data=sub).fit(),
        "M2: + idade + filhos": smf.ols("log_gasto ~ log_renda + Idade + TotalFilhos", data=sub).fit(),
    }
    registros = []
    for nome, modelo in modelos.items():
        for termo in modelo.params.index[1:]:
            ic = modelo.conf_int().loc[termo]
            registros.append(
                {
                    "Modelo": nome,
                    "Termo": termo,
                    "Coeficiente": modelo.params[termo],
                    "IC95_inf": ic[0],
                    "IC95_sup": ic[1],
                    "p_valor": modelo.pvalues[termo],
                    "R2": modelo.rsquared,
                    "N": int(modelo.nobs),
                }
            )
    return pd.DataFrame(registros).round(4)


# ----------------------------------------------------------------------------- tempo
def sensibilidade_temporal(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A segmentação por GastoTotal acumulado se mantém com o gasto mensal?

    Retorna (tabela de concordância, tabela do efeito do tempo de relacionamento).
    """
    d = df.dropna(subset=["GastoMensal"]).copy()
    limite_mensal = d["GastoMensal"].quantile(0.75)
    d["SegmentoMensal"] = np.where(d["GastoMensal"] >= limite_mensal, ROTULO_ALTO, ROTULO_DEMAIS)
    concordancia = pd.crosstab(d["SegmentoGasto"], d["SegmentoMensal"])
    total = concordancia.to_numpy().sum()
    po = concordancia.to_numpy().trace() / total
    pe = (concordancia.sum(axis=1) * concordancia.sum(axis=0)).sum() / total**2
    kappa = (po - pe) / (1 - pe)
    tabela_concordancia = concordancia.reset_index()
    tabela_concordancia.loc[len(tabela_concordancia)] = ["Acordo observado / Kappa", np.nan, np.nan]
    tabela_concordancia.iloc[-1, 1] = po * 100
    tabela_concordancia.iloc[-1, 2] = kappa

    registros = []
    for rotulo in ORDEM_SEGMENTOS:
        sub = df[(df["SegmentoGasto"] == rotulo) & df["GastoMensal"].notna()]
        registros.append(
            {
                "Grupo": rotulo,
                "N": len(sub),
                "Media_tempo_meses": sub["TempoRelacionamento"].mean(),
                "Mediana_tempo_meses": sub["TempoRelacionamento"].median(),
                "Mediana_gasto_acumulado": sub["GastoTotal"].median(),
                "Mediana_gasto_mensal": sub["GastoMensal"].median(),
            }
        )
    return tabela_concordancia.round(4), pd.DataFrame(registros).round(2)


def concentracao_por_decil(df: pd.DataFrame) -> pd.DataFrame:
    """Curva de concentração: % acumulado do gasto pelos decis de clientes ordenados por gasto."""
    ordenado = df["GastoTotal"].sort_values(ascending=False).to_numpy()
    total = ordenado.sum()
    n = len(ordenado)
    registros = []
    acumulado = 0.0
    for decil in range(1, 11):
        acumulado += ordenado[(decil - 1) * n // 10 : decil * n // 10].sum()
        registros.append(
            {
                "Decil_maiores_gastos": decil,
                "Perc_clientes": decil / 10 * 100,
                "Perc_gasto_acumulado": acumulado / total * 100,
            }
        )
    return pd.DataFrame(registros).round(2)
