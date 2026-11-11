"""Executa o projeto de ponta a ponta: limpeza, atributos, análises, tabelas e figuras.

Uso:  python src/run_all.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as an
import feature_engineering as fe
import preprocessing as pp
import visualization as viz
from preprocessing import DIR_TABELAS

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 40)


def salvar_tabela(tabela: pd.DataFrame, nome: str) -> Path:
    DIR_TABELAS.mkdir(parents=True, exist_ok=True)
    caminho = DIR_TABELAS / f"{nome}.csv"
    tabela.to_csv(caminho, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return caminho


def verificar_consistencias(df: pd.DataFrame, resumo: pd.DataFrame, decisoes: pd.DataFrame) -> None:
    """Checagens automáticas dos pontos críticos (executadas também nos testes)."""
    assert df["GastoTotal"].notna().all(), "GastoTotal com ausentes"
    assert (df["GastoTotal"] == df[pp.COLUNAS_GASTO].sum(axis=1)).all(), "GastoTotal inconsistente"
    assert set(df["SegmentoGasto"]) <= set(fe.ORDEM_SEGMENTOS), "rótulos de segmento inesperados"

    n = len(df)
    grupos = resumo.set_index("Grupo")
    assert grupos.loc[fe.ROTULO_ALTO, "N_clientes"] + grupos.loc[fe.ROTULO_DEMAIS, "N_clientes"] == n
    assert abs(grupos.loc["Total", "Participacao_gasto_total"] - 100) < 1e-6
    assert abs(
        grupos.loc[fe.ROTULO_ALTO, "Participacao_gasto_total"]
        + grupos.loc[fe.ROTULO_DEMAIS, "Participacao_gasto_total"]
        - 100
    ) < 0.01, "participações no gasto não somam 100%"
    assert abs(
        grupos.loc[fe.ROTULO_ALTO, "Percentual_clientes"]
        + grupos.loc[fe.ROTULO_DEMAIS, "Percentual_clientes"]
        - 100
    ) < 0.01

    # Segmentação pelo percentil 75, com tratamento de empates.
    limite = df["GastoTotal"].quantile(0.75)
    assert (df.loc[df["SegmentoGasto"] == fe.ROTULO_ALTO, "GastoTotal"] >= limite).all()

    # Gasto mensal: apenas tempo de relacionamento nulo/zero gera ausência.
    assert np.isfinite(df["GastoMensal"].dropna()).all(), "GastoMensal infinito"
    assert df.loc[df["TempoRelacionamento"] == 0, "GastoMensal"].isna().all()

    # Ausências documentadas: renda (24 + 1 implausível) e idade (3).
    assert df["Income"].isna().sum() == 25, df["Income"].isna().sum()
    assert df["Idade"].isna().sum() == 3, df["Idade"].isna().sum()
    assert len(decisoes) > 0


def main() -> dict:
    bruto = pp.carregar_bruto()
    limpo = pp.limpar(bruto)
    df = fe.adicionar_faixas(fe.construir_atributos(limpo))
    df = an.adicionar_canal_predominante(df)

    print(f"Base bruta: {bruto.shape[0]} linhas x {bruto.shape[1]} colunas")
    print(f"Base analítica: {df.shape[0]} linhas x {df.shape[1]} colunas")
    print(f"Data de referência (proxy): {fe.data_referencia(df):%d-%m-%Y}")

    # ---------------------------------------------------------------- tabelas
    perfil = pp.perfil_colunas(bruto)
    descritivas = pp.descritivas(bruto)
    derivadas = ["GastoTotal", "Idade", "TotalFilhos", "TempoRelacionamento", "GastoMensal",
                 "TotalCompras", "NumDealsPurchases", "NumCatalogPurchases"]
    descritivas_derivadas = pp.descritivas(df, derivadas)
    qualidade = pp.tabela_qualidade(bruto)

    resumo = an.resumo_segmentos(df)
    comparacao = an.comparacao_grupos(df)
    categorico = an.perfil_categorico(df)
    canais = an.analise_canais(df)
    canal_pred = an.canal_predominante(df).reset_index()
    descontos = an.analise_descontos(df)
    dist_descontos = an.distribuicao_descontos(df).reset_index()
    categorias = an.analise_categorias(df)
    publico = an.publico_alvo(df)
    combinacoes = an.combinacoes_perfis(df)
    combinacoes_renda = an.combinacoes_renda_filhos(df)
    matriz = an.matriz_renda_idade(df).reset_index()
    premissas = an.verificacao_premissas(df)
    testes = an.testes_estatisticos(df)
    correlacoes = an.correlacoes(df)
    regressao = an.regressao_loglog(df)
    concordancia, sensibilidade = an.sensibilidade_temporal(df)
    deceis = an.concentracao_por_decil(df)

    tabelas = {
        "T01_perfil_colunas": perfil,
        "T02_descritivas": descritivas,
        "T02b_descritivas_derivadas": descritivas_derivadas,
        "T03_qualidade": qualidade,
        "T04_resumo_segmentos": resumo,
        "T05_comparacao_grupos": comparacao,
        "T06_perfil_categorico": categorico,
        "T07_canais": canais,
        "T08_canal_predominante": canal_pred,
        "T09_descontos": descontos,
        "T10_distribuicao_descontos": dist_descontos,
        "T11_categorias": categorias,
        "T12_publico_alvo": publico,
        "T13_combinacoes": combinacoes,
        "T13b_combinacoes_renda_filhos": combinacoes_renda,
        "T14_matriz_renda_idade": matriz,
        "T15_premissas": premissas,
        "T15b_testes": testes,
        "T16_correlacoes": correlacoes,
        "T17_regressao_loglog": regressao,
        "T18_concordancia_segmentos": concordancia,
        "T19_sensibilidade_tempo": sensibilidade,
        "T20_concentracao_decis": deceis,
    }
    for nome, tabela in tabelas.items():
        salvar_tabela(tabela, nome)

    # ---------------------------------------------------------------- figuras
    figuras = [
        viz.fig_distribuicao_renda(df),
        viz.fig_distribuicao_idade(df),
        viz.fig_distribuicao_gasto(df),
        viz.fig_gasto_por_grupo(df),
        viz.fig_renda_por_grupo(df),
        viz.fig_idade_por_grupo(df),
        viz.fig_filhos_por_grupo(df),
        viz.fig_categorias(df, categorias),
        viz.fig_canais(df, canais),
        viz.fig_descontos(df, descontos, dist_descontos),
        viz.fig_participacao(df, resumo, deceis),
        viz.fig_renda_vs_gasto(df),
        viz.fig_tempo(df, sensibilidade),
        viz.fig_perfil_demografico(df),
        viz.fig_combinacoes(an.matriz_renda_idade(df)),
        viz.fig_correlacoes(df),
    ]
    print(f"\n{len(figuras)} figuras geradas em {pp.DIR_FIGURAS}")

    # ---------------------------------------------------------------- validação
    verificar_consistencias(df, resumo, qualidade)
    caminho_processado = pp.salvar_processado(df)
    print(f"Base processada salva em {caminho_processado}")

    # ---------------------------------------------------------------- resumo
    alto = resumo.set_index("Grupo").loc[fe.ROTULO_ALTO]
    print("\n=== RESULTADOS-CHAVE ===")
    print(f"Limite P75 do GastoTotal: {alto['Limite_P75_GastoTotal']:,.2f}")
    print(f"Alto gasto: {int(alto['N_clientes'])} clientes ({alto['Percentual_clientes']:.2f}%)")
    print(f"Participação no gasto total: {alto['Participacao_gasto_total']:.2f}%")
    print(f"Gasto médio: {alto['Media_gasto']:,.2f} x {resumo.set_index('Grupo').loc[fe.ROTULO_DEMAIS, 'Media_gasto']:,.2f}")
    print("\nCanais (média por cliente):")
    print(canais.pivot(index="Canal", columns="Grupo", values="Media_por_cliente").round(2).to_string())
    print("\nCategorias (participação na cesta, %):")
    print(categorias.set_index("Categoria")[["Perc_dentro_cesta_alto", "Perc_dentro_cesta_demais"]].to_string())
    print("\nTestes com p ajustado < 0,05:")
    print(testes.loc[testes["p_ajustado_BH"] < 0.05, ["Pergunta", "p_ajustado_BH", "Metrica_efeito"]].to_string(index=False))
    return {"df": df, "tabelas": tabelas, "resumo": resumo}


if __name__ == "__main__":
    main()
