# Análise de produtos e avaliações da Amazon

Projeto de ETL desenvolvido em Python para preparar uma base de produtos da Amazon para análise exploratória e visualização no Power BI. O processo valida a estrutura da fonte, padroniza campos numéricos, cria indicadores de preço, desconto, categoria e satisfação e exporta tabelas tratadas acompanhadas de um relatório de validação.

## Visão geral

A base de origem contém **1.465 registros e 16 colunas**. Após a preparação, os dados são organizados em dois arquivos analíticos:

- **Produtos:** 1.351 registros, com um registro por `product_id`. Quando um produto aparece mais de uma vez, é mantida a linha com maior quantidade de avaliações.
- **Feedback:** 1.465 registros, preservando os títulos e conteúdos de avaliação associados às linhas da origem.

A base contém informações de produtos comercializados na Amazon Índia. Os valores monetários são preservados em **INR (rúpias indianas)**; o script não realiza conversão cambial.

## Estrutura do projeto

```text
.
├── amazon.csv                         # Base original
├── etl.py                             # Script de preparação e validação
├── README.md
└── dados_tratados/
    ├── amazon_produtos_tratado.csv    # Dimensão de produtos
    ├── amazon_feedback_tratado.csv   # Dados para análise de avaliações
    └── relatorio_validacao.csv        # Indicadores de qualidade da execução
```

## Requisitos

- Python 3.10 ou superior
- pandas

Instale a dependência em um ambiente Python:

```bash
python -m pip install pandas
```

## Como executar

Na pasta do projeto, execute:

```bash
python etl.py
```

O script lê `amazon.csv` localizado junto ao `etl.py`, valida a presença das colunas necessárias e grava os três arquivos CSV em `dados_tratados/`. A pasta de saída é criada automaticamente quando necessário. Os arquivos tratados são escritos em UTF-8 com BOM para facilitar a abertura em ferramentas como Excel e Power BI.

## Etapas da ETL

1. **Leitura e validação:** carrega o CSV em UTF-8 e verifica se estão presentes os campos necessários de identificação, categoria, preço, avaliação e feedback.
2. **Padronização:** remove espaços nas extremidades de campos de texto e converte preços, percentuais e quantidade de avaliações para valores numéricos, removendo símbolos, separadores e caracteres não numéricos.
3. **Qualidade das avaliações:** converte `rating` para número, registra avaliações inválidas ou fora da escala de 0 a 5 e define como nulas as avaliações que não podem ser usadas em médias e rankings.
4. **Enriquecimento:** separa a hierarquia de categorias e calcula economia em INR, percentual de desconto calculado, divergência em pontos percentuais, faixa de satisfação e faixa de engajamento.
5. **Modelagem:** gera uma tabela de produtos deduplicada por `product_id` e uma tabela de feedback que mantém o texto da origem e inclui `id_registro_origem`.
6. **Validação:** exporta métricas de volume, duplicidade e consistência dos principais campos.

## Arquivos tratados

### `amazon_produtos_tratado.csv`

Tabela de produtos para análises de portfólio, preço e avaliação. Mantém as colunas originais e acrescenta, entre outras:

| Campo | Descrição |
|---|---|
| `preco_descontado_inr`, `preco_original_inr` | Preços convertidos para número, em INR |
| `desconto_percentual` | Percentual de desconto informado na origem, em número |
| `avaliacao`, `quantidade_avaliacoes` | Avaliação e volume de avaliações convertidos para número |
| `categoria_principal`, `subcategoria_1`, `subcategoria_2`, `nivel_categoria` | Níveis derivados da hierarquia de categorias |
| `economia_inr` | Diferença entre preço original e preço descontado |
| `desconto_percentual_calculado` | Desconto recalculado a partir dos preços |
| `divergencia_desconto_pp`, `flag_divergencia_desconto` | Diferença absoluta entre o desconto informado e o calculado; sinaliza diferença superior a 1 ponto percentual |
| `faixa_satisfacao` | Classificação da avaliação em Baixa, Regular, Boa, Excelente ou Sem avaliação válida |
| `faixa_engajamento` | Faixa de quantidade de avaliações baseada em quartis dos produtos |
| `flag_avaliacao_invalida`, `flag_avaliacao_fora_intervalo` | Indicadores de qualidade da avaliação original |

### `amazon_feedback_tratado.csv`

Tabela voltada à análise de Customer Insights. Inclui identificador do registro de origem, produto, categoria principal, avaliação, indicadores de qualidade e os campos `review_title` e `review_content` preservados da fonte.

### `relatorio_validacao.csv`

Arquivo em formato indicador/quantidade, com os totais verificados na execução da ETL.

## Resultado da validação disponível

Os números abaixo correspondem ao relatório atualmente presente em `dados_tratados/relatorio_validacao.csv`:

| Indicador | Resultado |
|---|---:|
| Linhas lidas | 1.465 |
| Colunas lidas | 16 |
| Linhas totalmente duplicadas | 0 |
| Produtos únicos após deduplicação | 1.351 |
| Repetições de `product_id` na origem | 114 |
| Avaliações inválidas | 1 |
| Quantidades de avaliações ausentes | 2 |
| Preços originais ou descontados inválidos | 0 |
| Descontos fora do intervalo de 0 a 100 | 0 |
| Avaliações fora do intervalo de 0 a 5 | 0 |
| Preço descontado maior que o original | 0 |
| Divergências de desconto superiores a 1 ponto percentual | 0 |

O relatório é atualizado sempre que `etl.py` é executado; portanto, os resultados podem mudar se a base de origem for alterada.

## Uso no Power BI

1. Execute a ETL para atualizar os arquivos tratados.
2. No Power BI Desktop, importe `amazon_produtos_tratado.csv` e `amazon_feedback_tratado.csv`.
3. Use `product_id` como chave para relacionar produtos e feedback. A tabela de feedback pode conter mais de uma linha por produto.
4. Importe `relatorio_validacao.csv` para acompanhar os indicadores de qualidade.

## Observações sobre os dados

- Valores monetários estão em INR e refletem os valores registrados na fonte.
- `faixa_engajamento` usa quartis da quantidade de avaliações entre os produtos; empates podem reduzir o número efetivo de grupos.
- O relatório de validação calcula parte das métricas sobre a tabela de produtos deduplicada, conforme a implementação de `etl.py`.
- A ETL prepara os dados e não executa análise de sentimento sobre o texto das avaliações.
