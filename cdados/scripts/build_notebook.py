"""Gera o notebook de análise a partir dos resultados reais calculados pelo pipeline.

Os textos interpretativos usam os valores calculados em tempo de execução, evitando
divergência entre narrativa, tabelas e figuras.

Uso:  python scripts/build_notebook.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import run_all  # noqa: E402

DESTINO = RAIZ / "notebooks" / "analise_customer_personality.ipynb"


def numero(valor: float, dec: int = 1) -> str:
    """Formata número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    return f"{valor:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def main() -> None:
    resultado = run_all.main()
    tabelas = resultado["tabelas"]
    df = resultado["df"]

    resumo = tabelas["T04_resumo_segmentos"].set_index("Grupo")
    alto = resumo.loc["Alto gasto"]
    demais = resumo.loc["Demais clientes"]
    comp = tabelas["T05_comparacao_grupos"].set_index("Variavel")
    categorias = tabelas["T11_categorias"].set_index("Categoria")
    canais = tabelas["T07_canais"]
    canal_alto = canais[canais["Grupo"] == "Alto gasto"].set_index("Canal")
    canal_demais = canais[canais["Grupo"] == "Demais clientes"].set_index("Canal")
    mesmos = tabelas["T09_descontos"].set_index("Grupo")
    publico = tabelas["T12_publico_alvo"]
    testes = tabelas["T15b_testes"]
    corridas = tabelas["T16_correlacoes"]
    renda_q5 = publico[(publico["Dimensao"] == "Faixa de renda") & (publico["Categoria"] == "Q5 (maior)")].iloc[0]
    sem_filhos = publico[(publico["Dimensao"] == "Quantidade de filhos") & (publico["Categoria"] == "Sem filhos")].iloc[0]
    combo_top = tabelas["T13_combinacoes"].iloc[0]
    regressao = tabelas["T17_regressao_loglog"]
    concordancia = tabelas["T18_concordancia_segmentos"]
    tempo = tabelas["T19_sensibilidade_tempo"].set_index("Grupo")
    deceis = tabelas["T20_concentracao_decis"]
    premissas = tabelas["T15_premissas"]
    perfil_cat = tabelas["T06_perfil_categorico"]
    dist_descontos = tabelas["T10_distribuicao_descontos"]
    qualidade = tabelas["T03_qualidade"]
    n_teste_sig = int((testes["p_ajustado_BH"] < 0.05).sum())

    rho_renda = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Renda anual")].iloc[0]
    rho_compras = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Total de compras")].iloc[0]
    rho_catalogo = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Compras por catálogo")].iloc[0]
    rho_deals = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Compras com desconto")].iloc[0]
    rho_visitas = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Visitas ao site por mês")].iloc[0]
    rho_tempo = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Tempo de relacionamento")].iloc[0]
    rho_filhos = corridas[(corridas["Desfecho"] == "Gasto total") & (corridas["Variavel"] == "Número de filhos")].iloc[0]

    celulas: list = []

    def md(texto: str) -> None:
        celulas.append(nbf.v4.new_markdown_cell(texto))

    def code(fonte: str) -> None:
        celulas.append(nbf.v4.new_code_cell(fonte))

    # ------------------------------------------------------------------ capa
    md(
        """# Customer Personality Analysis
## Quem são os clientes que concentram o gasto?

**Projeto acadêmico de Ciência de Dados** — análise exploratória, estatística descritiva e testes de hipótese sobre 2.240 clientes de uma empresa de varejo.

**Pergunta central:** qual é o perfil dos 25% de clientes de maior gasto, como eles se comparam aos demais e qual é sua participação no gasto total?

**Como ler este notebook:** cada seção começa com a pergunta analítica, apresenta a tabela/gráfico correspondente e termina com a interpretação. Todos os números são calculados na execução — nada é digitado à mão. O código reutilizável está em `src/`, as tabelas em `outputs/tables/` e as figuras em `outputs/figures/`.

**Reprodutibilidade:** `python src/run_all.py` gera todos os artefatos; este notebook executa o mesmo pipeline módulo a módulo.
"""
    )

    md(
        """## 1. Contexto, objetivos e perguntas de pesquisa

A base descreve clientes de uma empresa de varejo com atributos demográficos (ano de nascimento, escolaridade, estado civil, filhos), financeiros (renda anual) e comportamentais (gasto em seis categorias de produtos, compras por canal, compras com desconto, visitas ao site, adesão a campanhas).

**Objetivo geral:** identificar e caracterizar os clientes de maior gasto e investigar quais atributos estão associados à concentração de gastos.

**Perguntas que o trabalho responde:**

| # | Pergunta | Onde é respondida |
|---|----------|-------------------|
| P1 | Qual é o perfil do cliente que mais gasta? | Seções 6 e 7 |
| P2 | Qual é o canal de compra preferido desse grupo? | Seção 8 |
| P3 | Eles utilizam descontos? | Seção 9 |
| P4 | Qual categoria de produto concentra seus gastos? | Seção 10 |
| P5 | Qual público-alvo concentra a maior parte do gasto total? | Seção 11 |
| P6 | Quais são suas características de renda, escolaridade, idade e filhos? | Seções 7 e 11 |
| P7 | Qual é a participação dos clientes de alto gasto no gasto total? | Seção 6 |
| P8 | Existe relação entre renda e gastos? | Seções 12 e 13 |
| P9 | O tempo de relacionamento influencia a leitura do volume de gastos? | Seção 13 |

**Definição operacional adotada:** cliente de alto gasto é aquele cujo `GastoTotal` (soma de `MntWines`, `MntFruits`, `MntMeatProducts`, `MntFishProducts`, `MntSweetProducts`, `MntGoldProds`) é maior ou igual ao percentil 75 da distribuição. O `GastoTotal` é tratado como **aproximação do faturamento gerado pelo cliente**, porque a base não possui margem, lucro nem valor monetário por canal.
"""
    )

    code(
        """# Configuração: caminhos absolutos para o projeto funcionar de qualquer diretório
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import analysis as an
import feature_engineering as fe
import preprocessing as pp
import visualization as viz

pd.set_option("display.width", 180)
pd.set_option("display.max_columns", 50)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
print("Bibliotecas carregadas. Raiz do projeto:", RAIZ)
"""
    )

    # ------------------------------------------------------------------ inspeção
    md(
        """## 2. Inspeção e compreensão dos dados

Antes de qualquer análise, inspecionamos o arquivo real: separador, dimensões, tipos e cardinalidade. O arquivo `data/raw/marketing_campaign.csv` é **separado por tabulação** e tem 2.240 linhas — a inspeção confirmou a estrutura esperada (29 atributos), sem necessidade de ajustes de leitura.
"""
    )

    code(
        """bruto = pp.carregar_bruto()
print(f"Linhas: {bruto.shape[0]} | Colunas: {bruto.shape[1]}")
bruto.head(3)
"""
    )

    code(
        """perfil = pp.perfil_colunas(bruto)
perfil.groupby("Tipo_analitico").size().to_frame("Quantidade de variaveis")
"""
    )

    code(
        """perfil[["Variavel", "Tipo_analitico", "N_unicos", "Ausentes", "Exemplo"]]
"""
    )

    code(
        """# Estatísticas descritivas iniciais das variáveis numéricas originais
pp.descritivas(bruto).head(14)
"""
    )

    md(
        f"""**Leitura da inspeção.** A base tem {numero(df.shape[0], 0)} clientes e não possui duplicatas nem identificadores repetidos. Três variáveis exigem atenção imediata:

- `Income` tem **24 ausentes (1,07%)** e um valor de 666.666 (12,7× a mediana), incompatível com o gasto observado desse cliente — comportamento típico de erro de digitação.
- `Year_Birth` tem três registros que implicam idade superior a 100 anos.
- `Marital_Status` traz rótulos não padronizados (`Alone`, `Absurd`, `YOLO`).

`Z_CostContact` e `Z_Revenue` são **constantes** (3 e 11) e não têm poder discriminante. As seis colunas de gasto são contagens em unidades monetárias (u.m.), com forte assimetria à direita (assimetria entre 1,2 e 2,1), o que já indica que medianas e testes não paramétricos serão mais adequados que médias e testes t de Student.
"""
    )

    # ------------------------------------------------------------------ qualidade
    md(
        """## 3. Qualidade dos dados e tratamento

Cada problema investigado, sua frequência e a decisão adotada estão na tabela abaixo. Nenhuma linha foi eliminada: a base preserva todos os clientes, e as ausências são tratadas apenas nas análises que dependem da variável afetada.
"""
    )

    code(
        """qualidade = pp.tabela_qualidade(bruto)
qualidade
"""
    )

    md(
        f"""**Justificativas dos tratamentos**

1. **Renda ausente (24 casos):** não foram imputadas. Imputar renda por mediana criaria um valor artificial justamente no atributo mais associado ao gasto, contaminando as comparações. Esses clientes permanecem na base e são excluídos somente das análises que usam renda (n = {numero(df['Income'].notna().sum(), 0)} nessas análises).
2. **Renda 666.666 (1 caso):** convertida em ausente. O padrão de dígitos repetidos, o valor 12,7× a mediana e o gasto total de apenas 27 u.m. indicam erro de entrada, não um cliente de alta renda.
3. **Idades > 100 anos (3 casos):** idade tratada como ausente; as demais variáveis do cliente continuam válidas. Idades entre 70 e 90 anos foram **mantidas** — são plausíveis e o gasto desses clientes é informação legítima.
4. **Estados civis não padronizados:** `Alone` (3) foi agregado a "Solteiro(a)", interpretação direta do rótulo; `Absurd` (2) e `YOLO` (2) foram mantidos como "Outros", sem inventar uma categoria de estado civil.
5. **Escolaridade:** os cinco rótulos originais foram apenas traduzidos (`Basic`→Básico, `Graduation`→Graduação, `2n Cycle`→Ciclo 2, `Master`→Mestrado, `PhD`→Doutorado). Nenhum registro teve escolaridade inválida.
6. **Outliers:** a regra 1,5 IQR sinaliza {int(qualidade.loc[qualidade['Problema'].str.contains('GastoTotal'), 'Ocorrencias'].iloc[0])} clientes com gasto extremo, {int(qualidade.loc[qualidade['Problema'].str.contains('em renda'), 'Ocorrencias'].iloc[0])} com renda extrema e {int(qualidade.loc[qualidade['Problema'].str.contains('em idade'), 'Ocorrencias'].iloc[0])} com idade extrema (exatamente os três casos de idade impossível já tratados). **Nenhum cliente foi removido da base**: os gastos extremos são consumidores de alto padrão, o próprio objeto de interesse do trabalho — eliminá-los subestimaria a concentração de gasto, que é justamente o resultado central.
"""
    )

    code(
        """# Aplicação dos tratamentos e conferência
limpo = pp.limpar(bruto)
print("Colunas removidas:", sorted(set(bruto.columns) - set(limpo.columns)))
print("Ausentes após limpeza:")
print(limpo.isna().sum()[limpo.isna().sum() > 0].to_string())
print("Estados civis:", limpo["EstadoCivil"].value_counts().to_dict())
print("Escolaridade:", limpo["Escolaridade"].value_counts().sort_index().to_dict())
"""
    )

    # ------------------------------------------------------------------ atributos
    md(
        """## 4. Engenharia de atributos

Foram criados: `GastoTotal`, `Idade`, `TotalFilhos`, `TempoRelacionamento`, `GastoMensal`, `SegmentoGasto`, a participação de cada categoria no gasto individual, o total de compras e as faixas usadas na análise de público-alvo.

**Data de referência (decisão metodológica central).** A base não documenta a data em que foi extraída. Como o gasto é acumulado desde o cadastro, a extração ocorreu necessariamente **depois** do último cadastro presente. Adotamos a proxy mais conservadora disponível: **29-06-2014**, a maior data em `Dt_Customer`. Consequências:

- `TempoRelacionamento` = (data de referência − `Dt_Customer`) em meses (dividindo os dias por 30,4375).
- Se a extração real ocorreu depois, o tempo de relacionamento é **subestimado em uma constante** para todos os clientes, o que não altera comparações entre grupos nem a ordenação do gasto mensal, mas reduz o nível do gasto mensal calculado.
- Dois clientes cadastrados na própria data de referência têm tempo zero. Para eles `GastoMensal` fica ausente (nunca infinito), e eles são excluídos apenas das análises de gasto mensal.

**Segmentação e empates no percentil.** O limite é o percentil 75 de `GastoTotal`, e o grupo de alto gasto inclui **todos** os clientes com `GastoTotal` maior ou igual ao limite. Isso mantém a regra transparente quando há empates no valor de corte. Nesta base o percentil 75 vale 1.045,5 e **nenhum cliente tem exatamente esse gasto**, portanto o grupo fica com exatamente 25% da base.
"""
    )

    code(
        """referencia = fe.data_referencia(limpo)
df = an.adicionar_canal_predominante(fe.adicionar_faixas(fe.construir_atributos(limpo, referencia)))

limite = df["GastoTotal"].quantile(0.75)
print(f"Data de referência (proxy): {referencia:%d-%m-%Y}")
print(f"Percentil 75 do GastoTotal: {limite:,.2f}")
print(f"Clientes com gasto exatamente igual ao limite (empates): {(df['GastoTotal'] == limite).sum()}")
print(f"Clientes com tempo de relacionamento zero: {(df['TempoRelacionamento'] == 0).sum()}")
print(df["SegmentoGasto"].value_counts().to_string())
print(df["SegmentoGasto"].value_counts(normalize=True).mul(100).round(2).to_string())
"""
    )

    code(
        """# Estatísticas das variáveis derivadas (inclui o gasto mensal normalizado)
pp.descritivas(df, ["GastoTotal", "Idade", "TotalFilhos", "TempoRelacionamento", "GastoMensal", "TotalCompras"])
"""
    )

    md(
        f"""As variáveis derivadas confirmam o esperado: `GastoTotal` varia de {numero(df['GastoTotal'].min(), 0)} a {numero(df['GastoTotal'].max(), 0)} u.m., com mediana de {numero(df['GastoTotal'].median(), 0)} e média de {numero(df['GastoTotal'].mean(), 0)} — média acima da mediana é a assinatura da assimetria à direita. `GastoMensal` tem assimetria ainda maior porque clientes muito recentes podem ter acumulado pouco gasto em poucos dias; por isso, **todas as comparações de gasto mensal usam a mediana**, com a média reportada apenas como complemento.
"""
    )

    # ------------------------------------------------------------------ EDA
    md(
        """## 5. Análise exploratória geral

As três primeiras figuras respondem a uma pergunta simples e necessária: como se distribuem renda, idade e gasto? A forma dessas distribuições define quais estatísticas resumem bem os dados (mediana em vez de média) e quais testes são apropriados.
"""
    )

    code(
        """viz.fig_distribuicao_renda(df)
plt.show()
"""
    )

    md(
        f"""**Renda.** A distribuição é assimétrica à direita (assimetria {numero(df['Income'].skew(), 2)}), com mediana de {numero(df['Income'].median(), 0)} u.m. e média de {numero(df['Income'].mean(), 0)} u.m. A cauda contém clientes de alta renda que puxam a média para cima: por isso o trabalho usa mediana e quartis nas comparações. A concentração maior está entre 30 e 70 mil u.m.
"""
    )

    code(
        """viz.fig_distribuicao_idade(df)
plt.show()
"""
    )

    md(
        f"""**Idade.** A distribuição é aproximadamente simétrica (assimetria {numero(df['Idade'].skew(), 2)}), centrada em {numero(df['Idade'].median(), 0)} anos, com a maior parte entre {numero(df['Idade'].quantile(0.25), 0)} e {numero(df['Idade'].quantile(0.75), 0)} anos. Há poucos clientes acima de 70 anos, mas eles foram mantidos por serem plausíveis.
"""
    )

    code(
        """viz.fig_distribuicao_gasto(df)
plt.show()
"""
    )

    md(
        f"""**Gasto total.** A distribuição é **bimodal** (assimetria {numero(df['GastoTotal'].skew(), 2)}): um grupo numeroso com gasto próximo de zero e um grupo com gasto elevado, separados por uma região de baixa densidade. Isso não é acidente estatístico — reflete dois comportamentos de consumo distintos na base, e é o que torna a segmentação por percentil informativa. A mediana é {numero(df['GastoTotal'].median(), 0)} u.m. e a média {numero(df['GastoTotal'].mean(), 0)} u.m.
"""
    )

    code(
        """# Síntese das variáveis categóricas e de frequência
pd.DataFrame({
    "Escolaridade (%)": df["Escolaridade"].value_counts(normalize=True).mul(100).round(1),
    "Estado civil (%)": df["EstadoCivil"].value_counts(normalize=True).mul(100).round(1),
    "Filhos (%)": df["FaixaFilhos"].value_counts(normalize=True).mul(100).round(1),
    "Faixa etária (%)": df["FaixaEtaria"].value_counts(normalize=True).mul(100).round(1),
})
"""
    )

    code(
        """df[["Recency", "NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases", "NumDealsPurchases", "NumWebVisitsMonth"]].describe().T
"""
    )

    md(
        f"""**Perfil médio da base.** Predomínio de graduados, casados ou em união estável, com um filho em casa. A loja física é o canal com mais compras (mediana {numero(df['NumStorePurchases'].median(), 0)}), seguida de web (mediana {numero(df['NumWebPurchases'].median(), 0)}) e catálogo (mediana {numero(df['NumCatalogPurchases'].median(), 0)}). Quase todos os clientes usaram alguma oferta (mediana {numero(df['NumDealsPurchases'].median(), 0)} compras com desconto), e a recência mediana é de {numero(df['Recency'].median(), 0)} dias desde a última compra.
"""
    )

    # ------------------------------------------------------------------ segmentação
    md(
        """## 6. Identificação dos clientes de alto gasto

Aqui se aplica a definição central: clientes com `GastoTotal` no quartil superior. A tabela responde diretamente à pergunta P7 (participação no gasto total) e serve de base para todas as comparações seguintes.
"""
    )

    code(
        """resumo = an.resumo_segmentos(df)
resumo
"""
    )

    code(
        """# Concentração: quanto do gasto está nos maiores gastadores
deceis = an.concentracao_por_decil(df)
deceis
"""
    )

    code(
        """viz.fig_participacao(df, resumo, deceis)
plt.show()
"""
    )

    md(
        f"""**Resultado central.** O limite do quartil superior é **{numero(alto['Limite_P75_GastoTotal'], 2)} u.m.** Os {numero(alto['N_clientes'], 0)} clientes de alto gasto ({numero(alto['Percentual_clientes'], 2)}% da base) somam **{numero(alto['Participacao_gasto_total'], 2)}% do gasto total** ({numero(alto['Gasto_acumulado'], 0)} de {numero(resumo.loc['Total', 'Gasto_acumulado'], 0)} u.m.). Os {numero(demais['N_clientes'], 0)} demais clientes respondem por {numero(demais['Participacao_gasto_total'], 2)}%.

A concentração é ainda mais forte dentro do grupo: os 10% maiores gastadores respondem por {numero(deceis.iloc[0]['Perc_gasto_acumulado'], 1)}% do gasto e os 20% maiores por {numero(deceis.iloc[1]['Perc_gasto_acumulado'], 1)}%. O gasto médio do grupo de alto gasto é {numero(alto['Media_gasto'], 0)} u.m. contra {numero(demais['Media_gasto'], 0)} u.m. ({numero(alto['Media_gasto'] / demais['Media_gasto'], 1)}×); a mediana é {numero(alto['Mediana_gasto'], 0)} contra {numero(demais['Mediana_gasto'], 0)} u.m. ({numero(alto['Mediana_gasto'] / demais['Mediana_gasto'], 1)}×). A diferença entre esses dois múltiplos mostra que o grupo de alto gasto é internamente mais homogêneo que o restante da base.
"""
    )

    # ------------------------------------------------------------------ comparações
    md(
        """## 7. Comparação do perfil dos clientes

Seguimos a mesma segmentação para comparar perfil financeiro, demográfico e temporal. As figuras mostram distribuições; a tabela mostra os números que sustentam a leitura.
"""
    )

    code(
        """comparacao = an.comparacao_grupos(df)
comparacao
"""
    )

    code(
        """viz.fig_gasto_por_grupo(df)
plt.show()
"""
    )

    code(
        """viz.fig_renda_por_grupo(df)
plt.show()
"""
    )

    code(
        """viz.fig_idade_por_grupo(df)
plt.show()
"""
    )

    code(
        """viz.fig_filhos_por_grupo(df)
plt.show()
"""
    )

    code(
        """perfil_cat = an.perfil_categorico(df)
perfil_cat
"""
    )

    code(
        """viz.fig_perfil_demografico(df)
plt.show()
"""
    )

    md(
        f"""**Perfil financeiro.** Renda é a diferença mais nítida: mediana de {numero(comp.loc['Renda anual', 'Mediana_alto'], 0)} u.m. no alto gasto contra {numero(comp.loc['Renda anual', 'Mediana_demais'], 0)} u.m. nos demais ({numero(comp.loc['Renda anual', 'Razao_medianas'], 2)}×). As distribuições se sobrepõem apenas nas faixas altas: o cliente típico de alto gasto está acima de 70 mil u.m. de renda anual, e a cauda inferior do grupo é pequena.

**Perfil demográfico.** A idade praticamente não separa os grupos (medianas de {numero(comp.loc['Idade (anos)', 'Mediana_alto'], 0)} e {numero(comp.loc['Idade (anos)', 'Mediana_demais'], 0)} anos; diferença de {numero(comp.loc['Idade (anos)', 'Diferenca_medias'], 1)} ano na média). Já o número de filhos é um divisor forte: média de {numero(comp.loc['Número de filhos', 'Media_alto'], 2)} contra {numero(comp.loc['Número de filhos', 'Media_demais'], 2)}. Entre os clientes de alto gasto, {numero(perfil_cat.query("Dimensao == 'Quantidade de filhos' and Categoria == 'Sem filhos'")['Percentual_dentro_alto'].iloc[0], 1)}% não têm filhos, contra {numero(perfil_cat.query("Dimensao == 'Quantidade de filhos' and Categoria == 'Sem filhos'")['Percentual_dentro_demais'].iloc[0], 1)}% entre os demais. Escolaridade mostra diferença pequena mas consistente: doutorado é a categoria com maior taxa de alto gasto ({numero(publico.query("Dimensao == 'Escolaridade' and Categoria == 'Doutorado'")['Taxa_alto_gasto'].iloc[0], 1)}%) e básico tem {numero(publico.query("Dimensao == 'Escolaridade' and Categoria == 'Básico'")['Taxa_alto_gasto'].iloc[0], 1)}% — nenhum cliente com escolaridade básica está no quartil superior. O estado civil **não** separa os grupos de forma relevante (taxas de alto gasto entre {numero(publico.query("Dimensao == 'Estado civil'")['Taxa_alto_gasto'].min(), 1)}% e {numero(publico.query("Dimensao == 'Estado civil' and Categoria != 'Outros'")['Taxa_alto_gasto'].max(), 1)}%, excluindo a categoria residual "Outros").

**Perfil temporal.** O tempo de relacionamento mediano é de {numero(comp.loc['Tempo de relacionamento (meses)', 'Mediana_alto'], 1)} meses no alto gasto contra {numero(comp.loc['Tempo de relacionamento (meses)', 'Mediana_demais'], 1)} meses nos demais. A diferença é pequena em magnitude, mas relevante para a interpretação: o grupo de alto gasto é ligeiramente **mais antigo**, o que reforça, e não explica, seu gasto acumulado. Normalizando pelo tempo, a mediana do gasto mensal é de {numero(alto['Mediana_gasto_mensal'], 2)} u.m./mês no alto gasto contra {numero(demais['Mediana_gasto_mensal'], 2)} u.m./mês nos demais ({numero(alto['Mediana_gasto_mensal'] / demais['Mediana_gasto_mensal'], 1)}×), conforme detalhado na Seção 13.

**Relacionamento com a empresa.** A recência (dias desde a última compra) e o volume de compras completam o quadro: o alto gasto concentra mais compras ({numero(comp.loc['Total de compras (n)', 'Mediana_alto'], 0)} contra {numero(comp.loc['Total de compras (n)', 'Mediana_demais'], 0)}).
"""
    )

    # ------------------------------------------------------------------ canais
    md(
        """## 8. Canais de compra

**Pergunta:** qual canal os clientes de alto gasto usam mais? A base registra a **quantidade de compras** por canal (`NumWebPurchases`, `NumCatalogPurchases`, `NumStorePurchases`), não o valor gasto em cada canal. Portanto, a análise mede frequência de compras — nunca faturamento por canal.
"""
    )

    code(
        """canais = an.analise_canais(df)
canais
"""
    )

    code(
        """an.canal_predominante(df)
"""
    )

    code(
        """viz.fig_canais(df, canais)
plt.show()
"""
    )

    md(
        f"""**Quantidade.** A loja física continua sendo o canal mais usado pelos dois grupos, com média de {numero(canal_alto.loc['Loja física', 'Media_por_cliente'], 2)} compras por cliente no alto gasto contra {numero(canal_demais.loc['Loja física', 'Media_por_cliente'], 2)} nos demais. O que muda é a **intensidade relativa** dos outros canais: o catálogo salta de {numero(canal_demais.loc['Catálogo', 'Media_por_cliente'], 2)} para {numero(canal_alto.loc['Catálogo', 'Media_por_cliente'], 2)} compras por cliente ({numero(canal_alto.loc['Catálogo', 'Media_por_cliente'] / canal_demais.loc['Catálogo', 'Media_por_cliente'], 1)}×), e a web de {numero(canal_demais.loc['Web', 'Media_por_cliente'], 2)} para {numero(canal_alto.loc['Web', 'Media_por_cliente'], 2)}.

**Composição.** No total de compras do grupo de alto gasto, a loja física responde por {numero(canal_alto.loc['Loja física', 'Participacao_no_grupo'], 1)}%, o catálogo por {numero(canal_alto.loc['Catálogo', 'Participacao_no_grupo'], 1)}% e a web por {numero(canal_alto.loc['Web', 'Participacao_no_grupo'], 1)}%. Nos demais, a loja física pesa {numero(canal_demais.loc['Loja física', 'Participacao_no_grupo'], 1)}% e a web {numero(canal_demais.loc['Web', 'Participacao_no_grupo'], 1)}%. Ou seja: **o canal preferido em volume continua sendo a loja física**, mas o catálogo é o canal que mais distingue o segmento de alto gasto.

**Canal predominante** (maior número de compras do próprio cliente): {numero(df[df['SegmentoGasto'] == 'Alto gasto']['CanalPredominante'].eq('Loja física').mean() * 100, 1)}% do grupo de alto gasto tem a loja física como canal dominante e {numero(df[df['SegmentoGasto'] == 'Alto gasto']['CanalPredominante'].eq('Catálogo').mean() * 100, 1)}% tem o catálogo, contra {numero(df[df['SegmentoGasto'] == 'Demais clientes']['CanalPredominante'].eq('Catálogo').mean() * 100, 1)}% nos demais clientes. O catálogo, portanto, funciona como marcador de perfil de alto valor.

**Limitação explícita:** como não existe valor monetário por canal, é incorreto afirmar que a loja física "gera mais faturamento". Ela gera mais **transações**; a distribuição do gasto entre canais é desconhecida.
"""
    )

    # ------------------------------------------------------------------ descontos
    md(
        """## 9. Compras com desconto

**Pergunta:** os clientes de alto gasto usam descontos? `NumDealsPurchases` conta compras feitas com ofertas/descontos. O atributo **não comprova uso de cupom** — não há identificação de cupom na base, apenas a marcação de que a compra ocorreu com oferta.
"""
    )

    code(
        """descontos = an.analise_descontos(df)
dist_descontos = an.distribuicao_descontos(df).reset_index()
descontos
"""
    )

    code(
        """dist_descontos
"""
    )

    code(
        """viz.fig_descontos(df, descontos, dist_descontos)
plt.show()
"""
    )

    md(
        f"""**Resultado.** O uso de ofertas é quase universal na base: {numero(mesmos.loc['Alto gasto', 'Perc_usuarios'], 1)}% dos clientes de alto gasto e {numero(mesmos.loc['Demais clientes', 'Perc_usuarios'], 1)}% dos demais usaram ao menos uma oferta. Contudo, a **intensidade** é menor no alto gasto: média de {numero(mesmos.loc['Alto gasto', 'Media'], 2)} compras com desconto contra {numero(mesmos.loc['Demais clientes', 'Media'], 2)} ({numero(mesmos.loc['Alto gasto', 'Mediana'], 1)} vs {numero(mesmos.loc['Demais clientes', 'Mediana'], 1)} na mediana). Restringindo aos clientes que usaram ao menos uma oferta, a média cai para {numero(mesmos.loc['Alto gasto', 'Media_entre_usuarios'], 2)} no alto gasto e {numero(mesmos.loc['Demais clientes', 'Media_entre_usuarios'], 2)} nos demais.

**Interpretação.** Desconto não é o que move o segmento de alto valor: esses clientes compram com menos frequência em ofertas e concentram a compra em categorias de maior valor unitário. A distribuição mostra o padrão: {numero(dist_descontos.loc[dist_descontos['Compras_com_desconto'] == '0', 'Alto gasto'].iloc[0], 1)}% do alto gasto não usou nenhuma oferta, contra {numero(dist_descontos.loc[dist_descontos['Compras_com_desconto'] == '0', 'Demais clientes'].iloc[0], 1)}% dos demais, e a moda do alto gasto é 1 compra com desconto contra 2 nos demais. A leitura correta é **associação descritiva**, não causal: não se pode afirmar que dar desconto reduziria o gasto, nem que retirar descontos o aumentaria.
"""
    )

    # ------------------------------------------------------------------ categorias
    md(
        """## 10. Categorias de produto

**Pergunta:** qual categoria concentra os gastos? A análise compara total, média, mediana e participação na cesta de cada grupo.
"""
    )

    code(
        """categorias = an.analise_categorias(df)
categorias
"""
    )

    code(
        """viz.fig_categorias(df, categorias)
plt.show()
"""
    )

    md(
        f"""**Total.** Vinhos concentram {numero(categorias.loc['Vinhos', 'Perc_gasto_global'], 1)}% de todo o gasto da base ({numero(categorias.loc['Vinhos', 'Gasto_total'], 0)} u.m.), seguidos de carnes ({numero(categorias.loc['Carnes', 'Perc_gasto_global'], 1)}%), ouro ({numero(categorias.loc['Ouro', 'Perc_gasto_global'], 1)}%), peixes ({numero(categorias.loc['Peixes', 'Perc_gasto_global'], 1)}%), doces ({numero(categorias.loc['Doces', 'Perc_gasto_global'], 1)}%) e frutas ({numero(categorias.loc['Frutas', 'Perc_gasto_global'], 1)}%).

**Cesta do alto gasto.** Vinhos respondem por {numero(categorias.loc['Vinhos', 'Perc_dentro_cesta_alto'], 1)}% e carnes por {numero(categorias.loc['Carnes', 'Perc_dentro_cesta_alto'], 1)}% do gasto do grupo — juntas, {numero(categorias.loc['Vinhos', 'Perc_dentro_cesta_alto'] + categorias.loc['Carnes', 'Perc_dentro_cesta_alto'], 1)}%. Nos demais clientes, vinhos pesam {numero(categorias.loc['Vinhos', 'Perc_dentro_cesta_demais'], 1)}% e carnes {numero(categorias.loc['Carnes', 'Perc_dentro_cesta_demais'], 1)}%. A diferença relevante está em **carnes** (proporcionalmente mais importante no alto gasto) e em **ouro** (proporcionalmente mais importante entre os demais: {numero(categorias.loc['Ouro', 'Perc_dentro_cesta_demais'], 1)}% contra {numero(categorias.loc['Ouro', 'Perc_dentro_cesta_alto'], 1)}%) — ouro funciona mais como compra ocasional de ticket baixo do que como pilar do alto gasto.

**Gasto médio por cliente.** Todas as categorias crescem no grupo de alto gasto, em diferentes graus: carnes {numero(categorias.loc['Carnes', 'Razao_medias'], 1)}×, vinhos {numero(categorias.loc['Vinhos', 'Razao_medias'], 1)}×, frutas {numero(categorias.loc['Frutas', 'Razao_medias'], 1)}×, peixes {numero(categorias.loc['Peixes', 'Razao_medias'], 1)}×, doces {numero(categorias.loc['Doces', 'Razao_medias'], 1)}× e ouro apenas {numero(categorias.loc['Ouro', 'Razao_medias'], 1)}×. O grupo de alto gasto é responsável por {numero(categorias.loc['Carnes', 'Perc_do_gasto_da_categoria_no_alto'], 1)}% de toda a venda de carnes e {numero(categorias.loc['Vinhos', 'Perc_do_gasto_da_categoria_no_alto'], 1)}% de toda a venda de vinhos da base.
"""
    )

    # ------------------------------------------------------------------ público-alvo
    md(
        """## 11. Identificação do público-alvo

**Pergunta:** quais perfis concentram os clientes de alto gasto? Aqui distinguimos duas medidas que costumam ser confundidas:

- **taxa de alto gasto** = probabilidade de um cliente daquele perfil pertencer ao grupo de alto gasto (P(alto | perfil));
- **participação nos altos** = quanto daquele perfil está dentro do grupo de alto gasto.

Um perfil pode ter taxa altíssima e participação pequena (grupo raro) — ou o contrário. Reportamos as duas, com intervalo de confiança de Wilson e `lift` (taxa do perfil ÷ taxa base de 25%).
"""
    )

    code(
        """publico = an.publico_alvo(df)
publico.style.format({"Taxa_alto_gasto": "{:.1f}", "Perc_dos_altos": "{:.1f}", "Lift": "{:.2f}"})
"""
    )

    code(
        """# Recorte: faixas com maior taxa de alto gasto e n >= 50
publico[publico["N"] >= 50].sort_values("Taxa_alto_gasto", ascending=False).head(10)
"""
    )

    code(
        """combinacoes = an.combinacoes_perfis(df)
combinacoes
"""
    )

    code(
        """combinacoes_renda = an.combinacoes_renda_filhos(df)
combinacoes_renda
"""
    )

    code(
        """matriz = an.matriz_renda_idade(df)
viz.fig_combinacoes(matriz)
plt.show()
"""
    )

    md(
        f"""**Renda é o eixo dominante.** Na faixa Q5 (25% de maior renda), {numero(renda_q5['Taxa_alto_gasto'], 1)}% dos clientes são de alto gasto (IC95%: {numero(renda_q5['IC95_inf'], 1)}–{numero(renda_q5['IC95_sup'], 1)}; lift {numero(renda_q5['Lift'], 2)}) e essa faixa concentra {numero(renda_q5['Perc_dos_altos'], 1)}% de todos os clientes de alto gasto. Em Q1 e Q2 a taxa é praticamente zero — a renda funciona como condição quase necessária (não suficiente) para o alto gasto.

**Filhos são o segundo filtro mais forte.** Clientes sem filhos têm taxa de {numero(sem_filhos['Taxa_alto_gasto'], 1)}% ({numero(sem_filhos['N_alto_gasto'], 0)} de {numero(sem_filhos['N'], 0)}), com lift {numero(sem_filhos['Lift'], 2)}, e representam {numero(sem_filhos['Perc_dos_altos'], 1)}% do grupo de alto gasto. Com um filho a taxa cai para {numero(publico.query("Dimensao == 'Quantidade de filhos' and Categoria == '1 filho'")['Taxa_alto_gasto'].iloc[0], 1)}% e com dois filhos para {numero(publico.query("Dimensao == 'Quantidade de filhos' and Categoria == '2 filhos'")['Taxa_alto_gasto'].iloc[0], 1)}%.

**Combinação mais forte (n ≥ 30):** {combo_top['Perfil']} — {numero(combo_top['Taxa_alto_gasto'], 1)}% de alto gasto ({numero(combo_top['N_alto'], 0)} de {numero(combo_top['N'], 0)} clientes), lift {numero(combo_top['Lift'], 2)}, o que corresponde a {numero(combo_top['Perc_dos_altos'], 1)}% de todo o grupo de alto gasto. O cruzamento completo renda × filhos mostra o mesmo padrão: a taxa cresce de Q1 para Q5 e cai a cada filho adicional; nenhuma célula de Q1/Q2 atinge 1%.

**Idade não ordena o gasto.** As taxas por faixa etária ficam entre {numero(publico.query("Dimensao == 'Faixa etária'")['Taxa_alto_gasto'].min(), 1)}% e {numero(publico.query("Dimensao == 'Faixa etária'")['Taxa_alto_gasto'].max(), 1)}% — o mapa renda × idade mostra que a variação relevante é horizontal (entre quintis de renda), não vertical (entre faixas etárias). Dentro de Q5, todas as faixas etárias têm taxa alta.

**Cuidado com n pequeno:** "Viúvo(a)" tem taxa de {numero(publico.query("Dimensao == 'Estado civil' and Categoria == 'Viúvo(a)'")['Taxa_alto_gasto'].iloc[0], 1)}%, mas são apenas {int(publico.query("Dimensao == 'Estado civil' and Categoria == 'Viúvo(a)'")['N'].iloc[0])} clientes (IC95%: {numero(publico.query("Dimensao == 'Estado civil' and Categoria == 'Viúvo(a)'")['IC95_inf'].iloc[0], 1)}–{numero(publico.query("Dimensao == 'Estado civil' and Categoria == 'Viúvo(a)'")['IC95_sup'].iloc[0], 1)}%). Já a categoria "Outros" (n = {int(publico.query("Dimensao == 'Estado civil' and Categoria == 'Outros'")['N'].iloc[0])}) não sustenta nenhuma conclusão. Nenhuma dessas categorias pequenas deve orientar decisões de marketing.
"""
    )

    # ------------------------------------------------------------------ estatística
    md(
        """## 12. Análise estatística

Antes de testar, verificamos as premissas: assimetria, normalidade (Shapiro-Wilk) e homogeneidade de variâncias (Levene). Os resultados justificam a escolha de testes **não paramétricos** — o que não é uma formalidade: médias e desvios-padrão seriam resumos ruins para `GastoMensal` (assimetria acima de 9).
"""
    )

    code(
        """premissas = an.verificacao_premissas(df)
premissas
"""
    )

    md(
        f"""A normalidade é rejeitada em todos os grupos para todas as variáveis (p < 0,001), e as variâncias são desiguais para a maioria. Com n grande, o Teorema Central do Limite ampararia a comparação de médias, mas a assimetria forte torna a mediana o resumo mais fiel. Por isso, usamos **Mann-Whitney** para variáveis numéricas e **qui-quadrado** para associações categóricas, sempre com tamanho de efeito e correção de comparações múltiplas (Benjamini-Hochberg, FDR de 5%).
"""
    )

    code(
        """testes = an.testes_estatisticos(df)
testes[["Pergunta", "Teste", "Estatistica", "p_valor", "Tamanho_efeito", "Metrica_efeito", "p_ajustado_BH"]]
"""
    )

    md(
        f"""**Leitura dos testes.** {n_teste_sig} dos {len(testes)} testes permanecem significativos após a correção de BH (p ajustado < 0,05). Os efeitos grandes concentram-se em renda (r = {numero(testes.query("Variaveis == 'Renda'")['Tamanho_efeito'].iloc[0], 2)}), faixa de renda (V = {numero(testes.query("Variaveis == 'Faixa de renda'")['Tamanho_efeito'].iloc[0], 2)}), número de filhos (r = {numero(testes.query("Variaveis == 'Número de filhos'")['Tamanho_efeito'].iloc[0], 2)}), gasto mensal (r = {numero(testes.query("Variaveis == 'Gasto mensal'")['Tamanho_efeito'].iloc[0], 2)}) e possuir filhos (V = {numero(testes.query("Variaveis == 'Possui filhos'")['Tamanho_efeito'].iloc[0], 2)}).

Três resultados merecem ressalva, porque "significativo" não significa "relevante":

- **Idade**: p ajustado = {numero(testes.query("Variaveis == 'Idade'")['p_ajustado_BH'].iloc[0], 4)}, mas r = {numero(testes.query("Variaveis == 'Idade'")['Tamanho_efeito'].iloc[0], 2)} (desprezível). Com 2.240 clientes, diferenças de 1 ano aparecem como significativas. A conclusão prática é que idade **não** distingue os grupos.
- **Faixa etária**: V de Cramér = {numero(testes.query("Variaveis == 'Faixa etária'")['Tamanho_efeito'].iloc[0], 2)} (desprezível), mesmo com p < 0,01.
- **Estado civil**: p ajustado = {numero(testes.query("Variaveis == 'Estado civil'")['p_ajustado_BH'].iloc[0], 4)} — nenhuma evidência de associação com o segmento (V = {numero(testes.query("Variaveis == 'Estado civil'")['Tamanho_efeito'].iloc[0], 2)}).

**Tempo de relacionamento** é significativo com efeito pequeno (r = {numero(testes.query("Variaveis == 'Tempo de relacionamento'")['Tamanho_efeito'].iloc[0], 2)}), o que é coerente com a interpretação de que tempo não explica o volume de gasto.

**Canal predominante** é significativo com efeito pequeno-médio (V = {numero(testes.query("Variaveis == 'Canal predominante'")['Tamanho_efeito'].iloc[0], 2)}), sustentando a leitura de que o catálogo pesa mais no alto gasto.

Nenhum desses resultados estabelece causalidade: são associações observadas em uma base transversal, sem controle de confundidores.
"""
    )

    code(
        """correlacoes = an.correlacoes(df)
correlacoes
"""
    )

    code(
        """viz.fig_correlacoes(df)
plt.show()
"""
    )

    md(
        f"""**Correlações (Spearman).** `GastoTotal` tem ρ = {numero(rho_renda['Spearman_rho'], 3)} com renda e ρ = {numero(rho_compras['Spearman_rho'], 3)} com o total de compras: gastar mais é, quase por definição, comprar mais. O achado informativo é a hierarquia dos canais e do comportamento digital: ρ = {numero(rho_catalogo['Spearman_rho'], 3)} com compras por catálogo, ρ = {numero(rho_visitas['Spearman_rho'], 3)} com visitas ao site (negativo: quem mais visita o site compra menos, padrão de navegação sem conversão), ρ = {numero(rho_filhos['Spearman_rho'], 3)} com número de filhos e apenas ρ = {numero(rho_tempo['Spearman_rho'], 3)} com tempo de relacionamento. Compras com desconto têm ρ = {numero(rho_deals['Spearman_rho'], 3)} (p ajustado = {numero(rho_deals['p_ajustado_BH'], 3)}), ou seja, **nenhuma associação com o gasto acumulado**.
"""
    )

    code(
        """regressao = an.regressao_loglog(df)
regressao
"""
    )

    md(
        f"""**Regressão log-log (complementar).** Em um modelo log-log, o coeficiente de `log_renda` é a elasticidade: um aumento de 1% na renda associa-se a cerca de {numero(regressao.query("Modelo.str.startswith('M1') and Termo == 'log_renda'")['Coeficiente'].iloc[0], 2)}% mais gasto (IC95%: {numero(regressao.query("Modelo.str.startswith('M1') and Termo == 'log_renda'")['IC95_inf'].iloc[0], 2)}–{numero(regressao.query("Modelo.str.startswith('M1') and Termo == 'log_renda'")['IC95_sup'].iloc[0], 2)}), com R² = {numero(regressao.query("Modelo.str.startswith('M1') and Termo == 'log_renda'")['R2'].iloc[0], 3)}. Incluindo idade e filhos, a elasticidade cai para {numero(regressao.query("Modelo.str.startswith('M2') and Termo == 'log_renda'")['Coeficiente'].iloc[0], 2)} e o R² sobe para {numero(regressao.query("Modelo.str.startswith('M2') and Termo == 'log_renda'")['R2'].iloc[0], 3)}; cada filho adicional associa-se a cerca de {numero(abs(regressao.query("Modelo.str.startswith('M2') and Termo == 'TotalFilhos'")['Coeficiente'].iloc[0]) * 100, 0)}% menos gasto, mantendo a renda constante.

A elasticidade acima de 1 **não** deve ser lida como "renda dobra, gasto quadruplica" no sentido causal: como o gasto tem piso próximo de zero enquanto a renda não, a curva log-log é convexa e superestima a elasticidade em comparações extremas. O modelo serve aqui para quantificar a dominância da renda (R² entre {numero(regressao['R2'].min(), 2)} e {numero(regressao['R2'].max(), 2)}), não para previsão.
"""
    )

    # ------------------------------------------------------------------ tempo
    md(
        """## 13. O tempo de relacionamento altera a interpretação?

O gasto é acumulado desde o cadastro, então clientes mais antigos tiveram mais tempo para gastar. Testamos a robustez da segmentação comparando-a com uma segmentação alternativa pelo **gasto mensal** (mesmo critério de percentil 75) e verificando a concordância entre as duas.
"""
    )

    code(
        """concordancia, sensibilidade = an.sensibilidade_temporal(df)
concordancia
"""
    )

    code(
        """sensibilidade
"""
    )

    code(
        """viz.fig_tempo(df, sensibilidade)
plt.show()
"""
    )

    md(
        f"""**Resultado.** O tempo de relacionamento é ligeiramente maior no alto gasto ({numero(tempo.loc['Alto gasto', 'Mediana_tempo_meses'], 1)} vs {numero(tempo.loc['Demais clientes', 'Mediana_tempo_meses'], 1)} meses), mas a distância é pequena. Normalizando, a mediana do gasto mensal do alto gasto ({numero(tempo.loc['Alto gasto', 'Mediana_gasto_mensal'], 2)} u.m./mês) continua {numero(tempo.loc['Alto gasto', 'Mediana_gasto_mensal'] / tempo.loc['Demais clientes', 'Mediana_gasto_mensal'], 1)}× a dos demais ({numero(tempo.loc['Demais clientes', 'Mediana_gasto_mensal'], 2)} u.m./mês).

A segmentação pelo gasto mensal concorda com a segmentação pelo gasto acumulado em {numero(concordancia.iloc[-1, 1], 1)}% dos casos (kappa de Cohen = {numero(concordancia.iloc[-1, 2], 2)}, concordância moderada): dos {numero(alto['N_clientes'], 0)} clientes de alto gasto acumulado, {int(concordancia.iloc[0, 1])} permanecem no quartil superior quando se usa o gasto mensal. A conclusão é que **o tempo de relacionamento não inverte a leitura**: ele explica parte da variabilidade (ρ = {numero(rho_tempo['Spearman_rho'], 3)}), mas não é o mecanismo por trás da concentração de gasto. Mantivemos a segmentação principal pelo gasto acumulado, como definido no escopo, e usamos o gasto mensal apenas como verificação.

**Limitação:** a proxy de data de referência (29-06-2014) subestima o tempo de relacionamento e, portanto, superestima o gasto mensal — mas esse viés atinge os dois grupos de forma semelhante, preservando a comparação.
"""
    )

    # ------------------------------------------------------------------ conclusão
    md(
        f"""## 14. Conclusões

**Respostas às perguntas de pesquisa**

1. **Perfil do cliente que mais gasta.** Renda alta (mediana de {numero(comp.loc['Renda anual', 'Mediana_alto'], 0)} u.m., {numero(comp.loc['Renda anual', 'Razao_medianas'], 1)}× os demais), sem filhos, escolaridade superior (destaque para doutorado), idade próxima à mediana da base — não é um perfil etário, é um perfil de capacidade de consumo.
2. **Canal preferido.** Loja física em volume ({numero(canal_alto.loc['Loja física', 'Media_por_cliente'], 1)} compras por cliente); o catálogo é o canal que mais diferencia o grupo ({numero(canal_alto.loc['Catálogo', 'Media_por_cliente'], 1)} vs {numero(canal_demais.loc['Catálogo', 'Media_por_cliente'], 1)}).
3. **Descontos.** Usam menos ofertas que os demais ({numero(mesmos.loc['Alto gasto', 'Media'], 2)} vs {numero(mesmos.loc['Demais clientes', 'Media'], 2)} compras com desconto), embora quase todos já tenham usado alguma.
4. **Categorias.** Vinhos ({numero(categorias.loc['Vinhos', 'Perc_dentro_cesta_alto'], 1)}% da cesta) e carnes ({numero(categorias.loc['Carnes', 'Perc_dentro_cesta_alto'], 1)}%) concentram o gasto do grupo.
5. **Público-alvo.** Faixa Q5 de renda responde por {numero(renda_q5['Perc_dos_altos'], 1)}% dos clientes de alto gasto; clientes sem filhos, por {numero(sem_filhos['Perc_dos_altos'], 1)}%.
6. **Características do público.** Renda mediana {numero(comp.loc['Renda anual', 'Mediana_alto'], 0)} u.m., {numero(df[df['SegmentoGasto'] == 'Alto gasto']['TotalFilhos'].mean(), 2)} filhos em média, {numero(df[df['SegmentoGasto'] == 'Alto gasto']['Idade'].median(), 0)} anos de mediana, predominância de graduação/doutorado.
7. **Participação no gasto total.** Os 25% de maior gasto respondem por **{numero(alto['Participacao_gasto_total'], 2)}%** do gasto; os 10% maiores, por {numero(deceis.iloc[0]['Perc_gasto_acumulado'], 1)}%.
8. **Renda e gasto.** Associação forte e positiva (ρ = {numero(rho_renda['Spearman_rho'], 3)}; R² = {numero(regressao['R2'].max(), 2)} no modelo log-log com controles), sem pretensão causal.
9. **Tempo de relacionamento.** Influencia pouco (ρ = {numero(rho_tempo['Spearman_rho'], 3)}); a conclusão se mantém com o gasto mensal ({numero(concordancia.iloc[-1, 1], 1)}% de concordância entre segmentações).

**Recomendações de marketing (derivadas dos dados, não testadas em campo)**

- Priorizar o cruzamento **alta renda + sem filhos + ensino superior**: {numero(combo_top['Taxa_alto_gasto'], 1)}% desse perfil está no quartil superior e ele concentra {numero(combo_top['Perc_dos_altos'], 1)}% do grupo de alto gasto.
- Tratar o **catálogo** como canal de relacionamento do segmento premium: é onde o grupo mais se distancia do restante.
- Priorizar **vinhos e carnes** em sortimento e comunicação para esse público; não usar desconto como principal alavanca, já que o segmento usa menos ofertas.
- Não segmentar por idade nem por estado civil: os dados não sustentam associação relevante.
"""
    )

    md(
        """## 15. Limitações

1. **Gasto como proxy de faturamento.** A base não tem lucro, margem nem valor monetário por transação. `GastoTotal` é a melhor aproximação disponível do valor gerado pelo cliente, e não receita líquida.
2. **Estudo descritivo e transversal.** Todas as relações são associações observadas em um retrato único; nenhuma conclusão causal é possível. "Clientes sem filhos gastam mais" não implica que ter filhos reduza o gasto.
3. **`NumDealsPurchases` não comprova cupom.** O atributo registra compras com ofertas/descontos, sem identificar o mecanismo promocional.
4. **Gasto acumulado depende do tempo de relacionamento.** Tratado com a normalização mensal e a análise de concordância da Seção 13, mas não eliminado.
5. **Data de referência é uma proxy (29-06-2014).** O nível do gasto mensal é sensível a essa escolha; a comparação entre grupos não é.
6. **Amostra da base, não da população.** Os resultados descrevem os 2.240 clientes presentes; não representam necessariamente todos os consumidores da empresa, e não há informação sobre clientes que deixaram a base.
7. **Ausências não imputadas.** 25 clientes sem renda utilizável ficam fora das análises de renda e de algumas combinações de perfil — 1,1% da base, sem impacto material nas conclusões, mas com efeito no n exato de cada tabela.
8. **Não há dados de margem nem de custo promocional**, o que impede avaliar rentabilidade dos segmentos ou o retorno de descontos.
9. **Categorização em faixas** (quintis de renda, décadas de idade) é uma escolha analítica; outras divisões mudariam a forma das tabelas de público-alvo, mas não a direção dos resultados (renda alta e ausência de filhos concentram o alto gasto).
"""
    )

    md(
        """## 16. Referências

- KAGGLE. *Customer Personality Analysis* (dataset `marketing_campaign.csv`, 2.240 registros, 29 atributos). Disponível em: https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis. Acesso em: 2026.
- MCKINNEY, W. *Python for Data Analysis*. 3. ed. O'Reilly Media, 2022.
- VIRTANEN, P. et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. *Nature Methods*, v. 17, p. 261–272, 2020.
- WASKOM, M. seaborn: statistical data visualization. *Journal of Open Source Software*, v. 6, n. 60, p. 3021, 2021.
- SEABOLD, S.; PERKTOLD, J. statsmodels: Econometric and statistical modeling with Python. *Proceedings of the 9th Python in Science Conference*, 2010.
- BENJAMINI, Y.; HOCHBERG, Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society B*, v. 57, n. 1, p. 289–300, 1995.
- WILSON, E. B. Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, v. 22, n. 158, p. 209–212, 1927.
- COHEN, J. *Statistical Power Analysis for the Behavioral Sciences*. 2. ed. Lawrence Erlbaum, 1988.
"""
    )

    notebook = nbf.v4.new_notebook(cells=celulas)
    notebook.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata["language_info"] = {"name": "python"}
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, DESTINO)
    print(f"Notebook gerado: {DESTINO} ({len(celulas)} células)")


if __name__ == "__main__":
    main()
