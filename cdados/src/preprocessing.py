"""Carregamento, inspeção estrutural e limpeza do dataset Customer Personality Analysis.

Decisões de tratamento são registradas em `tabela_qualidade` para que o relatório
possa justificar cada uma delas.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BRUTO = RAIZ / "data" / "raw" / "marketing_campaign.csv"
CAMINHO_PROCESSADO = RAIZ / "data" / "processed" / "customer_personality_processado.csv"
DIR_FIGURAS = RAIZ / "outputs" / "figures"
DIR_TABELAS = RAIZ / "outputs" / "tables"

# Rótulos em português para as seis categorias de gasto (mantendo a ordem da base).
CATEGORIAS = {
    "MntWines": "Vinhos",
    "MntFruits": "Frutas",
    "MntMeatProducts": "Carnes",
    "MntFishProducts": "Peixes",
    "MntSweetProducts": "Doces",
    "MntGoldProds": "Ouro",
}
COLUNAS_GASTO = list(CATEGORIAS)

# Compra declarada por canal (quantidade de compras, não valor monetário).
CANAIS = {
    "NumWebPurchases": "Web",
    "NumCatalogPurchases": "Catálogo",
    "NumStorePurchases": "Loja física",
}

# Limite de plausibilidade para a renda anual: o maior valor da base é 666.666,
# 12,7x a mediana, com dígitos repetidos e gasto total de apenas 27 unidades
# monetárias. Tratado como erro de digitação -> ausente.
RENDA_MAXIMA_PLAUSIVEL = 600_000.0
# Idades acima de 100 anos na data de referência são tratadas como erro de cadastro
# (3 casos: nascidos em 1893, 1899 e 1900).
IDADE_MAXIMA_PLAUSIVEL = 100


def carregar_bruto(caminho: Path | str = CAMINHO_BRUTO) -> pd.DataFrame:
    """Lê o arquivo original (TSV) sem qualquer alteração."""
    return pd.read_csv(caminho, sep="\t")


def _tipo_analitico(serie: pd.Series, nome: str) -> str:
    if nome == "ID":
        return "Identificadora"
    if nome == "Dt_Customer":
        return "Temporal"
    if serie.nunique(dropna=True) == 1:
        return "Constante"
    if not pd.api.types.is_numeric_dtype(serie):
        return "Categórica"
    valores = set(serie.dropna().unique())
    if valores <= {0, 1}:
        return "Binária"
    if all(float(v).is_integer() for v in valores):
        return "Numérica discreta"
    return "Numérica contínua"


def perfil_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Inventário das variáveis: tipo, cardinalidade, ausências e exemplo."""
    registros = []
    for coluna in df.columns:
        serie = df[coluna]
        registros.append(
            {
                "Variavel": coluna,
                "Tipo_pandas": str(serie.dtype),
                "Tipo_analitico": _tipo_analitico(serie, coluna),
                "Nao_nulos": int(serie.notna().sum()),
                "Ausentes": int(serie.isna().sum()),
                "N_unicos": int(serie.nunique(dropna=True)),
                "Exemplo": serie.dropna().iloc[0] if serie.notna().any() else np.nan,
            }
        )
    return pd.DataFrame(registros)


def descritivas(df: pd.DataFrame, colunas: list[str] | None = None) -> pd.DataFrame:
    """Estatísticas descritivas robustas a assimetria (mediana, quartis, assimetria)."""
    colunas = colunas or [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    registros = []
    for coluna in colunas:
        serie = df[coluna].dropna().astype(float)
        registros.append(
            {
                "Variavel": coluna,
                "N": int(serie.size),
                "Media": serie.mean(),
                "Mediana": serie.median(),
                "Desvio_padrao": serie.std(),
                "Minimo": serie.min(),
                "Q1": serie.quantile(0.25),
                "Q3": serie.quantile(0.75),
                "Maximo": serie.max(),
                "Assimetria": serie.skew(),
                "Curtose": serie.kurt(),
                "CV": serie.std() / serie.mean() if serie.mean() else np.nan,
            }
        )
    return pd.DataFrame(registros).round(3)


def _outliers_iqr(serie: pd.Series) -> int:
    serie = serie.dropna()
    q1, q3 = serie.quantile([0.25, 0.75])
    iqr = q3 - q1
    return int(((serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)).sum())


def tabela_qualidade(df: pd.DataFrame) -> pd.DataFrame:
    """Problemas investigados, ocorrências, percentual e decisão adotada."""
    n = len(df)
    gasto = df[COLUNAS_GASTO].sum(axis=1)
    estados_civis_invalidos = sorted(
        set(df["Marital_Status"].unique())
        - {"Single", "Married", "Together", "Divorced", "Widow"}
    )
    n_estados_invalidos = int(df["Marital_Status"].isin(estados_civis_invalidos).sum())
    n_renda_invalida = int((df["Income"] >= RENDA_MAXIMA_PLAUSIVEL).sum())
    datas = pd.to_datetime(df["Dt_Customer"], format="%d-%m-%Y", errors="coerce")
    ano_ref = datas.max().year
    idade_invalida = ano_ref - df["Year_Birth"] > IDADE_MAXIMA_PLAUSIVEL
    n_idade_invalida = int(idade_invalida.sum())

    linhas = [
        ("Registros duplicados (linhas completas)", "todas", int(df.duplicated().sum()),
         "Nenhum; base mantida integralmente."),
        ("Identificadores (ID) repetidos", "ID", int(df["ID"].duplicated().sum()),
         "Nenhum; ID é chave única (usado apenas como identificador)."),
        ("Renda ausente", "Income", int(df["Income"].isna().sum()),
         "Mantidos como ausentes; excluídos apenas das análises que usam renda."),
        ("Renda implausível (>= 600.000)", "Income", n_renda_invalida,
         "Convertida em ausente (erro de digitação provável); linha preservada."),
        ("Idade implausível (> 100 anos)", "Year_Birth", n_idade_invalida,
         "Idade tratada como ausente nesses casos; demais variáveis preservadas."),
        ("Estado civil fora do padrão (Alone/Absurd/YOLO)", "Marital_Status", n_estados_invalidos,
         "Alone -> Solteiro(a); Absurd/YOLO -> Outros (4 casos), sem imputação inventada."),
        ("Escolaridade fora do padrão", "Education", 0,
         "5 rótulos válidos (Basic, Graduation, 2n Cycle, Master, PhD); apenas traduzidos."),
        ("Datas inválidas (Dt_Customer)", "Dt_Customer", int(datas.isna().sum()),
         "Nenhuma; conversão com formato explícito %d-%m-%Y."),
        ("Valores negativos em atributos não negativos", "numéricas", int((df.select_dtypes("number") < 0).sum().sum()),
         "Nenhum; nenhum ajuste necessário."),
        ("Colunas constantes", "Z_CostContact, Z_Revenue", int(df["Z_CostContact"].nunique() == 1) * 2,
         "Removidas: valor único (3 e 11), sem poder discriminante."),
        ("Outliers univariados (regra 1,5 IQR) em renda", "Income", _outliers_iqr(df["Income"]),
         "Mantidos: rendas altas são consumidores legítimos; a análise é descritiva."),
        ("Outliers univariados (regra 1,5 IQR) em idade", "Year_Birth",
         _outliers_iqr(pd.Series(2014 - df["Year_Birth"])),
         "Mantidos (exceto os 3 impossíveis): idosos de 70-90 anos são plausíveis."),
        ("Outliers univariados (regra 1,5 IQR) em GastoTotal", "GastoTotal", _outliers_iqr(gasto),
         "Mantidos: representam comportamento de consumo excepcional, não erro."),
    ]
    tabela = pd.DataFrame(linhas, columns=["Problema", "Variavel", "Ocorrencias", "Decisao"])
    tabela["Percentual"] = (tabela["Ocorrencias"] / n * 100).round(2)
    return tabela


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica os tratamentos documentados em `tabela_qualidade`."""
    d = df.copy()

    # Colunas constantes: sem informação.
    d = d.drop(columns=["Z_CostContact", "Z_Revenue"])

    # Datas no formato dia-mês-ano.
    d["Dt_Customer"] = pd.to_datetime(d["Dt_Customer"], format="%d-%m-%Y")

    # Idades implausíveis -> ausentes (evita distorcer médias de idade).
    ano_ref = d["Dt_Customer"].dt.year.max()
    d.loc[ano_ref - d["Year_Birth"] > IDADE_MAXIMA_PLAUSIVEL, "Year_Birth"] = np.nan

    # Renda: erro de digitação -> ausente (não imputado).
    d.loc[d["Income"] >= RENDA_MAXIMA_PLAUSIVEL, "Income"] = np.nan

    # Padronização do estado civil em português.
    mapa_civil = {
        "Single": "Solteiro(a)",
        "Alone": "Solteiro(a)",
        "Married": "Casado(a)",
        "Together": "União estável",
        "Divorced": "Divorciado(a)",
        "Widow": "Viúvo(a)",
    }
    d["EstadoCivil"] = d["Marital_Status"].map(mapa_civil).fillna("Outros")
    d = d.drop(columns=["Marital_Status"])

    # Escolaridade: tradução mantendo a ordem hierárquica original.
    mapa_escolaridade = {
        "Basic": "Básico",
        "Graduation": "Graduação",
        "2n Cycle": "Ciclo 2",
        "Master": "Mestrado",
        "PhD": "Doutorado",
    }
    d["Escolaridade"] = pd.Categorical(
        d["Education"].map(mapa_escolaridade),
        categories=["Básico", "Graduação", "Ciclo 2", "Mestrado", "Doutorado"],
        ordered=True,
    )
    d = d.drop(columns=["Education"])

    return d


def salvar_processado(df: pd.DataFrame, caminho: Path | str = CAMINHO_PROCESSADO) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False)
    return caminho
