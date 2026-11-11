"""Visualizações do projeto (Matplotlib/Seaborn), salvas em outputs/figures."""

from __future__ import annotations

from pathlib import Path

import sys

import matplotlib

# Em scripts (fora do Jupyter) usa backend sem interface; no notebook mantém o inline.
if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from feature_engineering import ORDEM_SEGMENTOS, ROTULO_ALTO, ROTULO_DEMAIS
from preprocessing import CANAIS, CATEGORIAS, COLUNAS_GASTO, DIR_FIGURAS

PALETA_SEGMENTO = {ROTULO_ALTO: "#c0392b", ROTULO_DEMAIS: "#7f8c8d"}
PALETA_CATEGORIAS = sns.color_palette("viridis", 6)
COR_NEUTRA = "#34495e"

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": False,
        "legend.frameon": False,
    }
)


def _pt(valor: float, dec: int = 1) -> str:
    """Número com vírgula decimal (padrão brasileiro)."""
    return f"{valor:.{dec}f}".replace(".", ",")


def _salvar(fig: plt.Figure, nome: str) -> Path:
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    caminho = DIR_FIGURAS / f"{nome}.png"
    fig.savefig(caminho)
    return caminho


def _formata_milhar(eixo, quantidade=6):
    eixo.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    eixo.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(quantidade))


def _texto(eixo, x, y, texto, **kwargs):
    """Texto com fundo branco semi-transparente para não competir com as barras."""
    kwargs.setdefault("fontsize", 8)
    kwargs.setdefault("color", COR_NEUTRA)
    kwargs.setdefault("ha", "left")
    kwargs.setdefault("va", "center")
    eixo.text(x, y, texto, bbox={"boxstyle": "round,pad=0.25", "fc": "white", "alpha": 0.85, "ec": "none"}, **kwargs)


def _rotulo_mediana(eixo, indice, valor, sufixo=""):
    eixo.annotate(f"{valor:,.0f}{sufixo}".replace(",", "."), xy=(indice, valor),
                  xytext=(10, 0), textcoords="offset points", va="center", fontsize=8,
                  fontweight="bold", color="#1a1a1a",
                  bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "#cccccc", "lw": 0.5})


# ------------------------------------------------------------------ 1-3 distribuições gerais
def fig_distribuicao_renda(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    renda = df["Income"].dropna()
    sns.histplot(renda, bins=40, color="#2c7fb8", ax=eixos[0])
    eixos[0].axvline(renda.median(), color="#c0392b", ls="--", label=f"Mediana: {renda.median():,.0f}")
    eixos[0].axvline(renda.mean(), color="#f39c12", ls=":", label=f"Média: {renda.mean():,.0f}")
    eixos[0].set_title("Distribuição da renda anual")
    eixos[0].set_xlabel("Renda anual (u.m.)")
    eixos[0].set_ylabel("Número de clientes")
    eixos[0].legend()
    eixos[0].tick_params(axis="x", rotation=20)

    sns.boxplot(x=renda, ax=eixos[1], color="#2c7fb8")
    eixos[1].set_title("Renda: dispersão e outliers")
    eixos[1].set_xlabel("Renda anual (u.m.)")
    eixos[1].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
    eixos[1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f} mil"))
    eixos[0].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(6))
    eixos[0].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f} mil"))
    eixos[1].annotate(
        f"Assimetria = {renda.skew():.2f}\nMédia > mediana\n{len(df) - len(renda)} rendas ausentes",
        xy=(0.55, 0.75), xycoords="axes fraction", fontsize=9, color=COR_NEUTRA,
    )
    fig.suptitle("Renda anual: forte assimetria à direita", fontweight="bold")
    _salvar(fig, "01_distribuicao_renda")
    return fig


def fig_distribuicao_idade(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    idade = df["Idade"].dropna()
    sns.histplot(idade, bins=30, color="#16a085", ax=eixos[0])
    eixos[0].axvline(idade.median(), color="#c0392b", ls="--", label=f"Mediana: {idade.median():.0f} anos")
    eixos[0].set_title("Distribuição da idade")
    eixos[0].set_xlabel("Idade (anos)")
    eixos[0].set_ylabel("Número de clientes")
    eixos[0].legend()

    sns.boxplot(x=idade, ax=eixos[1], color="#16a085")
    eixos[1].set_title("Idade: dispersão e outliers")
    eixos[1].set_xlabel("Idade (anos)")
    eixos[1].annotate(
        f"Assimetria = {idade.skew():.2f}\nMín. {idade.min():.0f} | Máx. {idade.max():.0f}\n"
        f"{df['Idade'].isna().sum()} idades inválidas",
        xy=(0.45, 0.6), xycoords="axes fraction", fontsize=9, color=COR_NEUTRA,
    )
    fig.suptitle("Idade: concentração entre 40 e 60 anos", fontweight="bold")
    _salvar(fig, "02_distribuicao_idade")
    return fig


def fig_distribuicao_gasto(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    gasto = df["GastoTotal"]
    sns.histplot(gasto, bins=40, color="#8e44ad", ax=eixos[0])
    eixos[0].axvline(gasto.quantile(0.75), color="#c0392b", ls="--",
                     label=f"P75 (limite alto gasto): {gasto.quantile(0.75):,.0f}")
    eixos[0].set_title("Distribuição do gasto total (escala linear)")
    eixos[0].set_xlabel("Gasto total (u.m.)")
    eixos[0].set_ylabel("Número de clientes")
    eixos[0].legend()

    sns.histplot(np.log1p(gasto), bins=40, color="#8e44ad", ax=eixos[1])
    eixos[1].set_title("Gasto total em escala logarítmica")
    eixos[1].set_xlabel("log(1 + gasto total)")
    eixos[1].set_ylabel("Número de clientes")
    _texto(
        eixos[1], 0.02, 0.97,
        f"Assimetria (escala original) = {gasto.skew():.2f}\n"
        f"Média {gasto.mean():,.0f} | Mediana {gasto.median():,.0f}".replace(",", "."),
        transform=eixos[1].transAxes, va="top", fontsize=9,
    )
    fig.suptitle("Gasto total: distribuição bimodal e concentrada à direita", fontweight="bold")
    _salvar(fig, "03_distribuicao_gasto_total")
    return fig


# ------------------------------------------------------------------ 4-7 comparações por grupo
def fig_gasto_por_grupo(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.8))
    medias = df.groupby("SegmentoGasto", observed=True)["GastoTotal"].median()
    sns.boxplot(data=df, x="SegmentoGasto", y="GastoTotal", order=ORDEM_SEGMENTOS,
                hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False, ax=eixos[0], width=0.45)
    for i, grupo in enumerate(ORDEM_SEGMENTOS):
        _rotulo_mediana(eixos[0], i, medias[grupo])
    eixos[0].set_title("Gasto total por segmento (escala linear)")
    eixos[0].set_xlabel("")
    eixos[0].set_ylabel("Gasto total (u.m.)")

    sns.stripplot(data=df, x="SegmentoGasto", y="GastoTotal", order=ORDEM_SEGMENTOS,
                  hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False,
                  size=1.6, alpha=0.35, jitter=0.25, ax=eixos[1])
    eixos[1].set_yscale("log")
    eixos[1].set_title("Gasto total por segmento (escala log)")
    eixos[1].set_xlabel("")
    eixos[1].set_ylabel("Gasto total (u.m., log)")
    fig.suptitle("Os 25% de maior gasto se separam com folga dos demais", fontweight="bold")
    _salvar(fig, "04_gasto_total_por_grupo")
    return fig


def fig_renda_por_grupo(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.8))
    d = df.dropna(subset=["Income"])
    sns.boxplot(data=d, x="SegmentoGasto", y="Income", order=ORDEM_SEGMENTOS,
                hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False, ax=eixos[0], width=0.45)
    for i, grupo in enumerate(ORDEM_SEGMENTOS):
        mediana = d.loc[d["SegmentoGasto"] == grupo, "Income"].median()
        _rotulo_mediana(eixos[0], i, mediana)
    eixos[0].set_ylim(0, d["Income"].quantile(0.99))
    eixos[0].set_title("Renda anual por segmento (até P99)")
    eixos[0].set_xlabel("")
    eixos[0].set_ylabel("Renda anual (u.m.)")

    sns.violinplot(data=d, x="SegmentoGasto", y="Income", order=ORDEM_SEGMENTOS,
                   hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False,
                   ax=eixos[1], cut=0, density_norm="width")
    eixos[1].set_yscale("log")
    eixos[1].set_title("Densidade da renda (escala log)")
    eixos[1].set_xlabel("")
    eixos[1].set_ylabel("Renda anual (u.m., log)")
    fig.suptitle("Clientes de alto gasto têm renda muito superior", fontweight="bold")
    _salvar(fig, "05_renda_por_grupo")
    return fig


def fig_idade_por_grupo(df: pd.DataFrame) -> plt.Figure:
    fig, eixo = plt.subplots(figsize=(8, 4.6))
    sns.boxplot(data=df, x="SegmentoGasto", y="Idade", order=ORDEM_SEGMENTOS,
                hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False, ax=eixo, width=0.4)
    for i, grupo in enumerate(ORDEM_SEGMENTOS):
        mediana = df.loc[df["SegmentoGasto"] == grupo, "Idade"].median()
        _rotulo_mediana(eixo, i, mediana, " anos")
    eixo.set_title("Idade por segmento de gasto")
    eixo.set_xlabel("")
    eixo.set_ylabel("Idade (anos)")
    fig.suptitle("Diferença de idade entre os grupos é pequena", fontweight="bold")
    _salvar(fig, "06_idade_por_grupo")
    return fig


def fig_filhos_por_grupo(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12.5, 4.8))
    distribuicao = (pd.crosstab(df["FaixaFilhos"], df["SegmentoGasto"], normalize="columns") * 100)
    distribuicao = distribuicao[ORDEM_SEGMENTOS]
    x = np.arange(len(distribuicao))
    largura = 0.36
    for deslocamento, grupo in zip((-largura / 2, largura / 2), ORDEM_SEGMENTOS):
        barras = eixos[0].bar(x + deslocamento, distribuicao[grupo], largura, label=grupo,
                              color=PALETA_SEGMENTO[grupo])
        eixos[0].bar_label(barras, fmt="%.0f%%", fontsize=7, padding=2)
    eixos[0].set_xticks(x, distribuicao.index)
    eixos[0].set_title("Distribuição da quantidade de filhos (% dentro do grupo)")
    eixos[0].set_xlabel("Filhos")
    eixos[0].set_ylabel("% de clientes do grupo")
    eixos[0].legend(fontsize=8)
    eixos[0].set_ylim(0, distribuicao.to_numpy().max() * 1.18)

    taxa = df.groupby("FaixaFilhos", observed=True).apply(
        lambda s: (s["SegmentoGasto"] == ROTULO_ALTO).mean() * 100, include_groups=False
    )
    barras = eixos[1].bar(x, taxa.values, color=sns.color_palette("Blues", len(taxa)))
    eixos[1].bar_label(barras, fmt="%.1f%%", fontsize=8)
    eixos[1].axhline(25, color="#c0392b", ls="--", label="Taxa média (25%)")
    eixos[1].set_xticks(x, taxa.index)
    eixos[1].set_title("Taxa de alto gasto por quantidade de filhos")
    eixos[1].set_xlabel("Filhos")
    eixos[1].set_ylabel("% de clientes de alto gasto")
    eixos[1].legend(fontsize=8)
    fig.suptitle("Ausência de filhos é a característica demográfica mais associada ao alto gasto",
                 fontweight="bold")
    _salvar(fig, "07_filhos_por_grupo")
    return fig


# ------------------------------------------------------------------ 8-10 categorias, canais, descontos
def fig_categorias(df: pd.DataFrame, tabela_categorias: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(13, 5))
    cesta = tabela_categorias.set_index("Categoria")[["Perc_dentro_cesta_alto", "Perc_dentro_cesta_demais"]]
    cesta.columns = [ROTULO_ALTO, ROTULO_DEMAIS]
    cesta.plot(kind="bar", ax=eixos[0], color=[PALETA_SEGMENTO[c] for c in cesta.columns], width=0.75)
    eixos[0].set_title("Participação de cada categoria na cesta do grupo (%)")
    eixos[0].set_xlabel("")
    eixos[0].set_ylabel("% do gasto do grupo")
    eixos[0].tick_params(axis="x", rotation=0)
    eixos[0].legend(fontsize=8)
    for container in eixos[0].containers:
        eixos[0].bar_label(container, fmt="%.1f", fontsize=7, padding=2)

    medias = tabela_categorias.set_index("Categoria")[["Media_alto", "Media_demais"]]
    medias.columns = [ROTULO_ALTO, ROTULO_DEMAIS]
    medias.plot(kind="bar", ax=eixos[1], color=[PALETA_SEGMENTO[c] for c in medias.columns], width=0.75)
    eixos[1].set_title("Gasto médio por cliente em cada categoria (u.m.)")
    eixos[1].set_xlabel("")
    eixos[1].set_ylabel("Gasto médio (u.m.)")
    eixos[1].tick_params(axis="x", rotation=0)
    eixos[1].legend(fontsize=8)
    eixos[1].bar_label(eixos[1].containers[0], fmt="%.0f", fontsize=7, padding=2)
    fig.suptitle("Vinhos dominam a cesta; carnes pesam proporcionalmente mais no alto gasto", fontweight="bold")
    _salvar(fig, "08_categorias_produto")
    return fig


def fig_canais(df: pd.DataFrame, tabela_canais: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.8))
    sns.barplot(data=tabela_canais, x="Canal", y="Media_por_cliente", hue="Grupo",
                hue_order=ORDEM_SEGMENTOS, palette=PALETA_SEGMENTO, ax=eixos[0])
    eixos[0].set_title("Média de compras por cliente em cada canal")
    eixos[0].set_xlabel("Canal")
    eixos[0].set_ylabel("Compras por cliente (n)")
    eixos[0].bar_label(eixos[0].containers[0], fmt="%.1f", fontsize=8)
    eixos[0].bar_label(eixos[0].containers[1], fmt="%.1f", fontsize=8)
    eixos[0].legend(fontsize=8)

    sns.barplot(data=tabela_canais, x="Canal", y="Participacao_no_grupo", hue="Grupo",
                hue_order=ORDEM_SEGMENTOS, palette=PALETA_SEGMENTO, ax=eixos[1])
    eixos[1].set_title("Participação de cada canal no total de compras do grupo (%)")
    eixos[1].set_xlabel("Canal")
    eixos[1].set_ylabel("% das compras do grupo")
    eixos[1].bar_label(eixos[1].containers[0], fmt="%.1f", fontsize=8)
    eixos[1].bar_label(eixos[1].containers[1], fmt="%.1f", fontsize=8)
    eixos[1].legend(fontsize=8)
    fig.suptitle("Loja física lidera em quantidade; web e catálogo pesam mais no alto gasto", fontweight="bold")
    _salvar(fig, "09_canais_compra")
    return fig


def fig_descontos(df: pd.DataFrame, tabela_descontos: pd.DataFrame,
                  dist_descontos: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12.5, 4.8))
    faixas = dist_descontos.set_index("Compras_com_desconto")[ORDEM_SEGMENTOS]
    faixas.plot(kind="bar", ax=eixos[0], color=[PALETA_SEGMENTO[g] for g in ORDEM_SEGMENTOS], width=0.75)
    eixos[0].set_title("Distribuição das compras com desconto (% dentro do grupo)")
    eixos[0].set_xlabel("Compras com desconto (n)")
    eixos[0].set_ylabel("% de clientes do grupo")
    eixos[0].tick_params(axis="x", rotation=0)
    eixos[0].legend(fontsize=8)

    barras = eixos[1].bar(tabela_descontos["Grupo"], tabela_descontos["Perc_usuarios"],
                          color=[PALETA_SEGMENTO[g] for g in tabela_descontos["Grupo"]], width=0.45)
    eixos[1].bar_label(barras, fmt="%.1f%%", fontsize=10)
    for i, (_, linha) in enumerate(tabela_descontos.iterrows()):
        eixos[1].annotate(f"média {linha['Media']:.2f} compras\nmediana {linha['Mediana']:.1f}",
                          xy=(i, linha["Perc_usuarios"] - 12), ha="center", fontsize=8, color="white")
    eixos[1].set_title("Clientes que usaram ao menos uma oferta")
    eixos[1].set_xlabel("")
    eixos[1].set_ylabel("% de clientes com NumDealsPurchases > 0")
    eixos[1].set_ylim(0, 108)
    fig.suptitle("Desconto é hábito da base inteira; o alto gasto usa um pouco menos",
                 fontweight="bold")
    _salvar(fig, "10_compras_descontos")
    return fig


# ------------------------------------------------------------------ 11-13 concentração e relações
def fig_participacao(df: pd.DataFrame, resumo: pd.DataFrame, deceis: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.8))
    linha = resumo.set_index("Grupo").loc[[ROTULO_ALTO, ROTULO_DEMAIS]]
    x = np.arange(len(linha))
    largura = 0.36
    eixos[0].bar(x - largura / 2, linha["Percentual_clientes"], largura, label="% dos clientes",
                 color="#95a5a6")
    eixos[0].bar(x + largura / 2, linha["Participacao_gasto_total"], largura, label="% do gasto total",
                 color="#c0392b")
    for i, (clientes, gasto) in enumerate(zip(linha["Percentual_clientes"], linha["Participacao_gasto_total"])):
        eixos[0].text(i - largura / 2, clientes, f"{clientes:.1f}%", ha="center", va="bottom", fontsize=8)
        eixos[0].text(i + largura / 2, gasto, f"{gasto:.1f}%", ha="center", va="bottom", fontsize=9,
                      fontweight="bold")
    eixos[0].set_xticks(x, linha.index)
    eixos[0].set_ylabel("% do total")
    eixos[0].set_title("Clientes x gasto: concentração no alto gasto")
    eixos[0].set_ylim(0, 85)
    eixos[0].legend(fontsize=8)

    eixos[1].plot([0, 100], [0, 100], ls="--", color="#bdc3c7", label="Igualdade perfeita")
    eixos[1].plot(deceis["Perc_clientes"], deceis["Perc_gasto_acumulado"], marker="o",
                  color="#c0392b", label="Concentração observada")
    for decil, deslocamento in ((1, (18, -14)), (5, (-38, -20))):
        valor = deceis.loc[deceis["Decil_maiores_gastos"] == decil, "Perc_gasto_acumulado"].iloc[0]
        eixos[1].annotate(f"{valor:.1f}% do gasto\n({decil*10}% dos clientes)",
                          xy=(decil * 10, valor), xytext=deslocamento, textcoords="offset points",
                          fontsize=8, arrowprops={"arrowstyle": "->", "color": "#7f8c8d"})
    eixos[1].set_xlabel("% de clientes (do maior para o menor gasto)")
    eixos[1].set_ylabel("% acumulado do gasto")
    eixos[1].set_title("Curva de concentração do gasto")
    eixos[1].legend(fontsize=8, loc="lower right")
    participacao = linha.loc[ROTULO_ALTO, "Participacao_gasto_total"]
    fig.suptitle(f"25% dos clientes respondem por {_pt(participacao)}% do gasto", fontweight="bold")
    _salvar(fig, "11_participacao_gasto_total")
    return fig


def fig_renda_vs_gasto(df: pd.DataFrame) -> plt.Figure:
    d = df.dropna(subset=["Income"])
    fig, eixo = plt.subplots(figsize=(9, 5.6))
    for grupo in ORDEM_SEGMENTOS:
        sub = d[d["SegmentoGasto"] == grupo]
        eixo.scatter(sub["Income"], sub["GastoTotal"].replace(0, 0.5), s=14, alpha=0.45,
                     color=PALETA_SEGMENTO[grupo], label=grupo, edgecolors="none")
    coef = np.polyfit(np.log(d["Income"]), np.log(d["GastoTotal"].replace(0, 0.5)), 1)
    grade = np.linspace(d["Income"].min(), d["Income"].max(), 100)
    eixo.plot(grade, np.exp(np.polyval(coef, np.log(grade))), color="#2c3e50", lw=2, ls="--",
              label="Ajuste log-linear global")
    rho = d["Income"].corr(d["GastoTotal"], method="spearman")
    eixo.set_xscale("log")
    eixo.set_yscale("log")
    eixo.set_xlabel("Renda anual (u.m., log)")
    eixo.set_ylabel("Gasto total (u.m., log)")
    eixo.set_title(f"Renda x gasto total — Spearman ρ = {rho:.3f}")
    eixo.legend(title="Segmento", fontsize=8, title_fontsize=8)
    fig.suptitle("Renda explica boa parte do gasto, mas há dispersão relevante", fontweight="bold")
    _salvar(fig, "12_renda_vs_gasto")
    return fig


def fig_tempo(df: pd.DataFrame, tabela_tempo: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.8))
    sns.boxplot(data=df, x="SegmentoGasto", y="TempoRelacionamento", order=ORDEM_SEGMENTOS,
                hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False, ax=eixos[0], width=0.4)
    eixos[0].set_title("Tempo de relacionamento por segmento")
    eixos[0].set_xlabel("")
    eixos[0].set_ylabel("Tempo de relacionamento (meses)")
    _texto(eixos[0], 0.02, 0.03, "Tenure = data de referência (2014-06-29) − Dt_Customer",
           transform=eixos[0].transAxes, fontsize=8)

    d = df.dropna(subset=["GastoMensal"])
    sns.boxplot(data=d, x="SegmentoGasto", y="GastoMensal", order=ORDEM_SEGMENTOS,
                hue="SegmentoGasto", palette=PALETA_SEGMENTO, legend=False, ax=eixos[1], width=0.4)
    eixos[1].set_yscale("log")
    for i, grupo in enumerate(ORDEM_SEGMENTOS):
        mediana = d.loc[d["SegmentoGasto"] == grupo, "GastoMensal"].median()
        _rotulo_mediana(eixos[1], i, mediana)
    eixos[1].set_title("Gasto mensal normalizado pelo tempo de relacionamento")
    eixos[1].set_xlabel("")
    eixos[1].set_ylabel("Gasto mensal (u.m./mês, log)")
    mediana_alto = d.loc[d["SegmentoGasto"] == ROTULO_ALTO, "GastoMensal"].median()
    mediana_demais = d.loc[d["SegmentoGasto"] == ROTULO_DEMAIS, "GastoMensal"].median()
    fig.suptitle(f"Normalizado pelo tempo, o alto gasto segue {_pt(mediana_alto / mediana_demais)}x maior",
                 fontweight="bold")
    _salvar(fig, "13_gasto_acumulado_vs_mensal")
    return fig


# ------------------------------------------------------------------ 14-16 perfil e combinações
def fig_perfil_demografico(df: pd.DataFrame) -> plt.Figure:
    linhas = []
    for coluna, nome in [("Escolaridade", "Escolaridade"), ("EstadoCivil", "Estado civil"),
                         ("FaixaEtaria", "Faixa etária")]:
        tabela = pd.crosstab(df[coluna], df["SegmentoGasto"], normalize="columns") * 100
        for categoria, valores in tabela.iterrows():
            linhas.append(
                {"Dimensao": nome, "Categoria": f"{nome}: {categoria}",
                 "Perc_alto": valores.get(ROTULO_ALTO, 0), "Perc_demais": valores.get(ROTULO_DEMAIS, 0)}
            )
    heat = pd.DataFrame(linhas)
    heat["Diferenca"] = heat["Perc_alto"] - heat["Perc_demais"]
    heat = heat.sort_values(["Dimensao", "Diferenca"], ascending=[True, False]).set_index("Categoria")

    fig, eixo = plt.subplots(figsize=(9.5, 6.2))
    sns.heatmap(heat[["Diferenca"]], annot=True, fmt="+.1f", cmap="RdBu_r", center=0,
                linewidths=0.5, ax=eixo, cbar_kws={"label": "p.p. a mais (+) ou a menos (−) no alto gasto"})
    eixo.set_title("Diferença de composição (alto gasto − demais clientes), em pontos percentuais")
    eixo.set_xlabel("")
    eixo.set_ylabel("")
    top = heat["Diferenca"].sort_values(ascending=False).head(3)
    destaques = ", ".join(
        f"{c.split(': ')[-1]} ({'+' if v > 0 else '-'}{_pt(abs(v))} p.p.)" for c, v in top.items()
    )
    fig.suptitle(f"Concentrações no alto gasto: {destaques}", fontweight="bold", fontsize=10.5)
    _salvar(fig, "14_perfil_demografico_alto_gasto")
    return fig


def fig_combinacoes(matriz: pd.DataFrame) -> plt.Figure:
    fig, eixo = plt.subplots(figsize=(8.5, 4.8))
    sns.heatmap(matriz, annot=True, fmt=".1f", cmap="YlOrRd", linewidths=0.5, ax=eixo,
                cbar_kws={"label": "% de alto gasto na célula"})
    eixo.set_title("Taxa de alto gasto (%) por faixa de renda e faixa etária")
    eixo.set_xlabel("Faixa etária (anos)")
    eixo.set_ylabel("Faixa de renda (quintis)")
    fig.suptitle(f"Renda domina a combinação: maior taxa observada = {_pt(matriz.to_numpy().max())}%",
                 fontweight="bold")
    _salvar(fig, "15_combinacoes_alto_gasto")
    return fig


def fig_correlacoes(df: pd.DataFrame) -> plt.Figure:
    colunas = {
        "GastoTotal": "Gasto total",
        "Income": "Renda",
        "Idade": "Idade",
        "TotalFilhos": "Filhos",
        "TempoRelacionamento": "Tempo relac.",
        "TotalCompras": "Total compras",
        "NumDealsPurchases": "Compras desconto",
        "NumWebVisitsMonth": "Visitas site",
        "NumCatalogPurchases": "Compras catálogo",
    }
    corr = df[list(colunas)].rename(columns=colunas).corr(method="spearman")
    fig, eixo = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1,
                linewidths=0.5, ax=eixo, cbar_kws={"label": "ρ de Spearman"})
    eixo.set_title("Correlações de Spearman entre as variáveis centrais")
    fig.suptitle("Gasto total é dominado por renda e volume de compras", fontweight="bold")
    _salvar(fig, "16_correlacoes")
    return fig
