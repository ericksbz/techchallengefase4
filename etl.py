"""ETL da base Amazon Sales para consumo no Power BI."""

from pathlib import Path

import pandas as pd


ARQUIVO_ORIGEM = Path(__file__).with_name("amazon.csv")
PASTA_SAIDA = Path(__file__).with_name("dados_tratados")
COLUNAS_OBRIGATORIAS = {
    "product_id", "product_name", "category", "discounted_price", "actual_price",
    "discount_percentage", "rating", "rating_count", "about_product",
    "review_title", "review_content",
}


def para_numero(serie: pd.Series) -> pd.Series:
    """Remove símbolos monetários, percentuais e separadores de milhar."""
    texto = serie.astype("string").str.replace(r"[^0-9.]", "", regex=True)
    return pd.to_numeric(texto, errors="coerce")


def validar_estrutura(df: pd.DataFrame) -> None:
    colunas_ausentes = COLUNAS_OBRIGATORIAS.difference(df.columns)
    if colunas_ausentes:
        raise ValueError(
            "O CSV não possui as colunas obrigatórias: "
            f"{', '.join(sorted(colunas_ausentes))}"
        )


def tratar_dados(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dados = df.copy()

    colunas_texto = dados.select_dtypes(include="string").columns
    dados[colunas_texto] = dados[colunas_texto].apply(lambda coluna: coluna.str.strip())

    dados["preco_descontado_inr"] = para_numero(dados["discounted_price"])
    dados["preco_original_inr"] = para_numero(dados["actual_price"])
    dados["desconto_percentual"] = para_numero(dados["discount_percentage"])
    avaliacao_convertida = pd.to_numeric(dados["rating"], errors="coerce")
    dados["flag_avaliacao_invalida"] = avaliacao_convertida.isna()
    dados["flag_avaliacao_fora_intervalo"] = (
        avaliacao_convertida.notna() & ~avaliacao_convertida.between(0, 5)
    )
    # Ratings ausentes, não numéricos ou fora da escala de 0 a 5 ficam nulos.
    # Assim, não participam de médias e rankings no Power BI.
    dados["avaliacao"] = avaliacao_convertida.mask(
        dados["flag_avaliacao_invalida"]
        | dados["flag_avaliacao_fora_intervalo"]
    )
    dados["quantidade_avaliacoes"] = para_numero(dados["rating_count"])

    partes_categoria = dados["category"].str.split("|")
    dados["categoria_principal"] = partes_categoria.str[0]
    dados["subcategoria_1"] = partes_categoria.str[1]
    dados["subcategoria_2"] = partes_categoria.str[2]
    dados["nivel_categoria"] = partes_categoria.str.len()

    dados["economia_inr"] = (
        dados["preco_original_inr"] - dados["preco_descontado_inr"]
    ).round(2)
    dados["desconto_percentual_calculado"] = (
        dados["economia_inr"].div(dados["preco_original_inr"]).mul(100).round(2)
    )
    dados["divergencia_desconto_pp"] = (
        dados["desconto_percentual"] - dados["desconto_percentual_calculado"]
    ).abs().round(2)
    dados["flag_divergencia_desconto"] = dados["divergencia_desconto_pp"].gt(1)

    dados["faixa_satisfacao"] = pd.cut(
        dados["avaliacao"],
        bins=[0, 3.5, 4.0, 4.5, 5.0],
        labels=["Baixa", "Regular", "Boa", "Excelente"],
        include_lowest=True,
    ).astype("string").fillna("Sem avaliação válida")

    # Preserva o texto de origem para análise de Customer Insights no Power BI.
    feedback = dados[
        ["product_id", "product_name", "categoria_principal", "avaliacao",
         "flag_avaliacao_invalida", "flag_avaliacao_fora_intervalo",
         "review_title", "review_content"]
    ].copy()
    feedback.insert(0, "id_registro_origem", dados.index + 1)

    # O mesmo produto aparece em mais de uma linha na fonte. Para análise de
    # portfólio, mantém-se a linha com a maior quantidade de avaliações.
    produtos = (
        dados.sort_values("quantidade_avaliacoes", ascending=False, na_position="last")
        .drop_duplicates(subset="product_id", keep="first")
        .copy()
    )
    produtos["faixa_engajamento"] = pd.qcut(
        produtos["quantidade_avaliacoes"],
        q=4,
        labels=["Baixo", "Médio", "Alto", "Muito alto"],
        duplicates="drop",
    ).astype("string").fillna("Sem dados")

    return produtos, feedback


def gerar_relatorio_validacao(origem: pd.DataFrame, produtos: pd.DataFrame) -> pd.DataFrame:
    metricas = [
        ("linhas_lidas", len(origem)),
        ("colunas_lidas", len(origem.columns)),
        ("linhas_duplicadas", int(origem.duplicated().sum())),
        ("produtos_unicos", int(produtos["product_id"].nunique())),
        ("product_id_duplicados_na_origem", int(origem["product_id"].duplicated().sum())),
        ("rating_invalido", int(produtos["flag_avaliacao_invalida"].sum())),
        ("quantidade_avaliacoes_ausente", int(produtos["quantidade_avaliacoes"].isna().sum())),
        ("preco_original_invalido", int(produtos["preco_original_inr"].isna().sum())),
        ("preco_descontado_invalido", int(produtos["preco_descontado_inr"].isna().sum())),
        ("desconto_fora_do_intervalo", int((~produtos["desconto_percentual"].between(0, 100)).sum())),
        ("avaliacao_fora_do_intervalo", int(produtos["flag_avaliacao_fora_intervalo"].sum())),
        ("preco_descontado_maior_que_original", int((produtos["preco_descontado_inr"] > produtos["preco_original_inr"]).sum())),
        ("divergencia_desconto_maior_que_1pp", int(produtos["flag_divergencia_desconto"].sum())),
    ]
    return pd.DataFrame(metricas, columns=["indicador", "quantidade"])


def main() -> None:
    origem = pd.read_csv(ARQUIVO_ORIGEM, encoding="utf-8")
    validar_estrutura(origem)
    produtos, feedback = tratar_dados(origem)
    validacao = gerar_relatorio_validacao(origem, produtos)

    PASTA_SAIDA.mkdir(exist_ok=True)
    produtos.to_csv(PASTA_SAIDA / "amazon_produtos_tratado.csv", index=False, encoding="utf-8-sig")
    feedback.to_csv(PASTA_SAIDA / "amazon_feedback_tratado.csv", index=False, encoding="utf-8-sig")
    validacao.to_csv(PASTA_SAIDA / "relatorio_validacao.csv", index=False, encoding="utf-8-sig")

    print("ETL concluído.")
    print(f"Produtos tratados: {len(produtos)}")
    print(f"Registros de feedback: {len(feedback)}")
    print(f"Arquivos gerados em: {PASTA_SAIDA}")
    print(validacao.to_string(index=False))


if __name__ == "__main__":
    main()
