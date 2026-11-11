# Customer Personality Analysis

Projeto acadêmico de Ciência de Dados: análise exploratória, estatística descritiva e testes de hipótese sobre 2.240 clientes de uma empresa de varejo, com o objetivo de **identificar e caracterizar os clientes de maior gasto** e medir sua participação no gasto total.

## Resultados principais

| Indicador | Valor |
|---|---|
| Limite do quartil superior de gasto (P75) | 1.045,50 u.m. |
| Clientes de alto gasto | 560 (25,00%) |
| Participação desse grupo no gasto total | **61,51%** |
| Participação dos 10% maiores gastadores | 30,16% |
| Gasto médio: alto gasto x demais | 1.490,48 x 310,91 u.m. (4,79x) |
| Renda mediana: alto gasto x demais | 75.295,50 x 42.691,00 u.m. (1,76x) |
| Canal mais usado (volume) | Loja física (8,48 compras/cliente no alto gasto) |
| Canal que mais diferencia o segmento | Catálogo (5,91 x 1,58 compras/cliente) |
| Categorias que concentram a cesta do alto gasto | Vinhos (49,6%) e carnes (30,7%) |
| Perfil mais associado ao alto gasto | Alta renda + sem filhos + ensino superior (83,4% de alto gasto) |

Relatório completo com metodologia, tabelas e interpretação: [`report/relatorio_final.md`](report/relatorio_final.md).

## Estrutura

```
.
├── data/
│   ├── raw/marketing_campaign.csv              # base original (não modificada)
│   └── processed/customer_personality_processado.csv
├── notebooks/
│   └── analise_customer_personality.ipynb      # análise narrada, já executada
├── src/
│   ├── preprocessing.py                        # leitura, inspeção, qualidade, limpeza
│   ├── feature_engineering.py                  # atributos derivados e segmentação
│   ├── analysis.py                             # tabelas, comparações e testes
│   ├── visualization.py                        # 16 figuras
│   └── run_all.py                              # executa o pipeline completo
├── scripts/build_notebook.py                   # regenera o notebook com números reais
├── tests/test_pipeline.py                      # verificações automáticas
├── outputs/
│   ├── figures/                                # PNGs numerados (01–16)
│   └── tables/                                 # CSVs (T01–T20)
├── report/relatorio_final.md
├── requirements.txt
└── README.md
```

## Como executar

Requer Python 3.11+ (testado em 3.14).

```bash
python -m pip install -r requirements.txt   # 1. dependências

python src/run_all.py                       # 2. pipeline completo:
                                            #    limpeza, atributos, 23 tabelas, 16 figuras,
                                            #    validações internas e base processada

python -m jupyter notebook notebooks/analise_customer_personality.ipynb   # 3. notebook
# ou, sem interface:
python -m nbconvert --to notebook --execute --inplace notebooks/analise_customer_personality.ipynb

python tests/test_pipeline.py               # 4. verificações (ou: pytest tests/)
```

O notebook é **autoexecutável** e reimporta os módulos de `src/`; ele pode ser regenerado com `python scripts/build_notebook.py` (que roda o pipeline e injeta os valores calculados nos textos).

## Dados

Base pública **Customer Personality Analysis** (`marketing_campaign.csv`, separada por tabulação, 2.240 clientes, 29 atributos): https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis

A empresa não é identificada e a moeda não é informada; os valores monetários são tratados como **unidades monetárias (u.m.)**. O arquivo original é preservado em `data/raw/`; todas as transformações são feitas em memória e salvas em `data/processed/`.

## Decisões metodológicas centrais

1. **GastoTotal** = soma das seis categorias (`MntWines`, `MntFruits`, `MntMeatProducts`, `MntFishProducts`, `MntSweetProducts`, `MntGoldProds`), usado como **proxy do faturamento** do cliente (a base não traz lucro nem margem).
2. **Segmentação:** "Alto gasto" = `GastoTotal` ≥ percentil 75, incluindo todos os empates no limite. Nesta base o P75 = 1.045,50 e não há empates, resultando em exatamente 560 clientes (25%).
3. **Data de referência:** a base não documenta a data de coleta. Usa-se a proxy **29-06-2014** (maior `Dt_Customer`), justificada por ser limite inferior da data real. Viés constante entre clientes; não altera comparações.
4. **Gasto mensal** = `GastoTotal` / meses de relacionamento; ausente apenas para os 2 clientes com tempo zero (nunca infinito).
5. **Limpeza sem descarte de clientes:** renda ausente (24) e renda implausível (1) não são imputadas; 3 idades impossíveis (> 100 anos) viram ausentes; estados civis não padronizados são mapeados (`Alone`→Solteiro(a), `Absurd`/`YOLO`→Outros); colunas constantes `Z_CostContact` e `Z_Revenue` removidas.
6. **Estatística:** Mann-Whitney e qui-quadrado (normalidade rejeitada; assimetria forte), com r rank-biserial / V de Cramér como tamanho de efeito e correção de Benjamini-Hochberg para comparações múltiplas.
7. **Limitações explícitas:** análise descritiva (sem causalidade); `NumDealsPurchases` não comprova uso de cupom; não há valor monetário por canal; a base descreve seus próprios clientes, não toda a população.

## Saídas geradas

- `outputs/figures/01_…` a `16_…png` — 16 figuras com título, eixos rotulados e anotações dos valores relevantes.
- `outputs/tables/` — 23 tabelas (`T01`…`T20`, com `T02b`, `T13b` e `T15b`) em UTF-8 com separador `;` e vírgula decimal (abrem direto no Excel pt-BR).
- `data/processed/customer_personality_processado.csv` — base analítica com atributos derivados.
- `notebooks/analise_customer_personality.ipynb` — análise narrada, executada de ponta a ponta sem erros.
