"""Verificações automáticas do pipeline (executáveis com pytest ou `python tests/test_pipeline.py`)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import analysis as an  # noqa: E402
import feature_engineering as fe  # noqa: E402
import preprocessing as pp  # noqa: E402

_cache: dict = {}


def dados() -> pd.DataFrame:
    if "df" not in _cache:
        bruto = pp.carregar_bruto()
        limpo = pp.limpar(bruto)
        df = an.adicionar_canal_predominante(fe.adicionar_faixas(fe.construir_atributos(limpo)))
        _cache.update(bruto=bruto, df=df)
        _cache["resumo"] = an.resumo_segmentos(df)
        _cache["categorias"] = an.analise_categorias(df)
        _cache["canais"] = an.analise_canais(df)
    return _cache["df"]


def test_leitura_e_dimensoes() -> None:
    bruto = pp.carregar_bruto()
    assert bruto.shape == (2240, 29), bruto.shape
    assert bruto["ID"].is_unique
    assert bruto.duplicated().sum() == 0


def test_gasto_total_e_soma_das_categorias() -> None:
    df = dados()
    soma = df[pp.COLUNAS_GASTO].sum(axis=1)
    assert np.allclose(df["GastoTotal"], soma)
    assert df["GastoTotal"].min() > 0  # todos os clientes têm algum gasto


def test_segmentacao_no_percentil_75_com_empates() -> None:
    df = dados()
    limite = df["GastoTotal"].quantile(0.75)
    esperado = (df["GastoTotal"] >= limite).sum()
    assert (df["SegmentoGasto"] == fe.ROTULO_ALTO).sum() == esperado
    participacao = (df["SegmentoGasto"] == fe.ROTULO_ALTO).mean()
    assert 0.24 <= participacao <= 0.26, participacao
    # Regra de empates: nenhum cliente elegível fica fora do grupo
    assert (df.loc[df["SegmentoGasto"] == fe.ROTULO_ALTO, "GastoTotal"] >= limite).all()


def test_participacao_no_gasto_soma_100() -> None:
    resumo = _cache["resumo"].set_index("Grupo")
    total = resumo.loc["Total", "Participacao_gasto_total"]
    soma = resumo.loc[fe.ROTULO_ALTO, "Participacao_gasto_total"] + resumo.loc[
        fe.ROTULO_DEMAIS, "Participacao_gasto_total"
    ]
    assert abs(total - 100) < 1e-6
    assert abs(soma - 100) < 1e-6
    assert abs(resumo.loc[fe.ROTULO_ALTO, "Gasto_acumulado"] - _cache["df"].query(
        "SegmentoGasto == @fe.ROTULO_ALTO")["GastoTotal"].sum()) < 0.01


def test_gasto_mensal_sem_divisao_invalida() -> None:
    df = dados()
    assert np.isfinite(df["GastoMensal"].dropna()).all()
    sem_tempo = df["TempoRelacionamento"] <= 0
    assert df.loc[sem_tempo, "GastoMensal"].isna().all(), "tempo zero deveria gerar ausência"
    assert (df["TempoRelacionamento"] >= 0).all()


def test_idade_plausivel_apos_tratamento() -> None:
    df = dados()
    idade = df["Idade"].dropna()
    assert idade.min() >= 18 and idade.max() <= pp.IDADE_MAXIMA_PLAUSIVEL
    assert df["Idade"].isna().sum() == 3


def test_renda_invalida_removida() -> None:
    df = dados()
    assert df["Income"].max() < pp.RENDA_MAXIMA_PLAUSIVEL
    assert df["Income"].isna().sum() == 25


def test_cestas_e_canais_somam_100() -> None:
    categorias = _cache["categorias"]
    assert abs(categorias["Perc_dentro_cesta_alto"].sum() - 100) < 0.05
    assert abs(categorias["Perc_dentro_cesta_demais"].sum() - 100) < 0.05
    canais = _cache["canais"].groupby("Grupo")["Participacao_no_grupo"].sum()
    assert np.allclose(canais.values, 100, atol=0.05), canais


def test_agregados_batem_com_a_base() -> None:
    df = dados()
    categorias = _cache["categorias"].set_index("Categoria")
    for coluna, nome in pp.CATEGORIAS.items():
        assert abs(categorias.loc[nome, "Gasto_total"] - df[coluna].sum()) < 0.01
    assert abs(df["GastoTotal"].sum() - 1_356_988) < 1  # mesma base da execução de referência


def test_ferramentas_estatisticas() -> None:
    p = pd.Series([0.001, 0.02, 0.03, 0.4, np.nan])
    ajustado = an.bh_correcao(p)
    assert ajustado.isna().sum() == 1
    assert (ajustado.dropna() >= p.dropna() - 1e-12).all()
    assert ajustado.dropna().is_monotonic_increasing
    inf, sup = an.wilson_ic(0, 10)
    assert 0 <= inf <= sup <= 1


def test_analise_temporal_consistente() -> None:
    concordancia, sensibilidade = an.sensibilidade_temporal(dados())
    assert len(concordancia) == 3  # 2x2 + linha de kappa
    assert -1 <= concordancia.iloc[-1, 2] <= 1
    assert set(sensibilidade["Grupo"]) == set(fe.ORDEM_SEGMENTOS)


def test_artefatos_gerados() -> None:
    figuras = sorted((RAIZ / "outputs" / "figures").glob("*.png"))
    tabelas = sorted((RAIZ / "outputs" / "tables").glob("*.csv"))
    assert len(figuras) >= 16, len(figuras)
    assert len(tabelas) >= 20, len(tabelas)
    assert (RAIZ / "data" / "processed" / "customer_personality_processado.csv").exists()


def test_notebook_executado() -> None:
    import json

    caminho = RAIZ / "notebooks" / "analise_customer_personality.ipynb"
    nb = json.loads(caminho.read_text())
    erros = [o for c in nb["cells"] for o in c.get("outputs", []) if o.get("output_type") == "error"]
    assert not erros, erros[:1]
    codigos = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert all(c.get("execution_count") for c in codigos), "notebook tem células não executadas"


if __name__ == "__main__":
    falhas = 0
    for nome, funcao in sorted(globals().items()):
        if nome.startswith("test_") and callable(funcao):
            try:
                funcao()
                print(f"OK   {nome}")
            except AssertionError as erro:
                falhas += 1
                print(f"FALHA {nome}: {erro}")
    print(f"\n{'Todas as verificações passaram.' if not falhas else f'{falhas} falha(s).'}")
    sys.exit(1 if falhas else 0)
