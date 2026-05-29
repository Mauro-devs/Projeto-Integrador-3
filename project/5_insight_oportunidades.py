import polars as pl
import time
from config import PROCESSED_DIR
from loguru import logger
def calcular_fato_oportunidades():
    logger.info("="*70)
    logger.info("🌊 GERANDO INSIGHTS DE OPORTUNIDADES")
    logger.info("="*70)
    start_time = time.time()

    logger.info("[1/4] Carregando Fato e Dimensões...")
    fato = pl.read_parquet(PROCESSED_DIR / "fato_estabelecimentos.parquet")
    dim_loc = pl.read_parquet(PROCESSED_DIR / "dim_localidades.parquet")
    dim_ativ = pl.read_parquet(PROCESSED_DIR / "dim_atividades_economicas.parquet")
    dim_sit = pl.read_parquet(PROCESSED_DIR / "dim_situacoes.parquet")

    # Reconstrói a base plana apenas com ativas para o cálculo
    abt = (
        fato
        .join(dim_loc, left_on="LOCALIDADE", right_on="ID_LOCALIDADE", how="inner")
        .join(dim_ativ, left_on="ATIVIDADE", right_on="ID_ATIVIDADE", how="inner")
        .join(dim_sit, left_on="SITUACAO", right_on="ID_SITUACAO", how="inner")
        .filter(pl.col("CODIGO_SITUACAO") == 2) 
        .filter(pl.col("BAIRRO").is_not_null() & (pl.col("BAIRRO") != ""))
    )
    logger.success("Dados de Fato e Dimensoes carregados com sucesso!")

    logger.info("[2/4] Calculando densidade média do Estado...")
    total_empresas_estado = abt.height
    
    # Peso de cada CNAE no estado inteiro
    df_estado = (
        abt.group_by("ATIVIDADE").len()
        .with_columns((pl.col("len") / total_empresas_estado).alias("PROPORCAO_ESTADO"))
        .rename({"len": "QTD_ESTADO"})
    )

    # Considera qualquer setor que tenha pelo menos 20 CNPJs ativos no estado inteiro
    # (Assim a gente pega farmácias e veterinários, mas tira fora absurdos como "Fábrica de Sinos")
    top_cnaes = df_estado.filter(pl.col("QTD_ESTADO") >= 20)
    logger.success("Densidade média calculada e CNAEs relevantes selecionados!")

    logger.info("[3/4] Mapeando a concorrência bairro a bairro...")
    # Agrupa por Bairro
    total_por_bairro = abt.group_by(["MUNICIPIO", "BAIRRO"]).len().rename({"len": "TOTAL_NO_BAIRRO"})
    
    # Agrupa por Bairro + Setor (ID_ATIVIDADE)
    ativ_por_bairro = abt.group_by(["MUNICIPIO", "BAIRRO", "ATIVIDADE"]).len().rename({"len": "QTD_NO_BAIRRO"})
    

    logger.info("[4/4] Aplicando Quociente Locacional e vinculando IDs...")
    radar = (
        ativ_por_bairro
        .join(total_por_bairro, on=["MUNICIPIO", "BAIRRO"])
        .filter(pl.col("TOTAL_NO_BAIRRO") >= 100) # Filtro de relevância comercial
        .join(top_cnaes, on="ATIVIDADE", how="inner")
        .with_columns((pl.col("QTD_NO_BAIRRO") / pl.col("TOTAL_NO_BAIRRO")).alias("PROPORCAO_BAIRRO"))
    )

    # O Cálculo do Índice de Saturação (QL)
    radar = radar.with_columns(
        (pl.col("PROPORCAO_BAIRRO") / pl.col("PROPORCAO_ESTADO")).round(2).alias("INDICE_SATURACAO")
    )

    # Regras de Negócio para o Dashboard
    radar = radar.with_columns(
        pl.when(pl.col("INDICE_SATURACAO") >= 1.5).then(pl.lit("🔴 Saturação (Oceano Vermelho)"))
        .when(pl.col("INDICE_SATURACAO") <= 0.6).then(pl.lit("🌊 Oportunidade (Oceano Azul)"))
        .otherwise(pl.lit("🟡 Equilibrado"))
        .alias("CLASSIFICACAO_MERCADO")
    )

    # SELEÇÃO FINAL DAS COLUNAS
    radar_final = radar.select([
        pl.col("ATIVIDADE").alias("ID_ATIVIDADE"), # Chave Estrangeira
        pl.col("MUNICIPIO"),                       # Chave de Localidade (Nível Bairro)
        pl.col("BAIRRO"),                          # Chave de Localidade (Nível Bairro)
        pl.col("QTD_NO_BAIRRO"),                   # Métrica
        pl.col("INDICE_SATURACAO"),                # Métrica (QL)
        pl.col("CLASSIFICACAO_MERCADO"),           # Dimensão Descritiva
        pl.col("TOTAL_NO_BAIRRO")                  # Métrica
    ]).sort(["MUNICIPIO", "BAIRRO", "INDICE_SATURACAO"], descending=[False, False, True])

    # Alterado para fato_oportunidades.parquet
    radar_final.write_parquet(PROCESSED_DIR / "fato_oportunidades.parquet")
    logger.success(f"\n✅ Tabela Fato Agregada gerada em {time.time() - start_time:.2f}s!")
    logger.info(f"📁 Arquivo salvo em: {PROCESSED_DIR / 'fato_oportunidades.parquet'}")
    
    return radar_final, dim_ativ

def testar_fato_no_terminal(fato_df, dim_ativ, bairro_alvo):
    logger.info(f"\n\n🔍 TESTANDO A TABELA FATO: '{bairro_alvo}'")
    
    # Filtra a Fato e faz Join com a Dimensão para pegar o nome
    dados_bairro = (
        fato_df.filter(pl.col("BAIRRO").str.to_uppercase().str.contains(bairro_alvo.upper()))
        .join(dim_ativ, left_on="ID_ATIVIDADE", right_on="ID_ATIVIDADE", how="left")
    )

    if dados_bairro.height == 0:
        logger.error("❌ Bairro não possui dados suficientes.")
        return

    bairro_exato = dados_bairro['BAIRRO'][0]
    total_empresas = dados_bairro['TOTAL_NO_BAIRRO'][0]

    logger.info(f"📍 {bairro_exato} | {total_empresas} empresas ativas.")

    saturados = dados_bairro.filter(pl.col("INDICE_SATURACAO") >= 1.5).sort("INDICE_SATURACAO", descending=True).head(3)
    oportunidades = dados_bairro.filter(pl.col("INDICE_SATURACAO") <= 0.6).sort("INDICE_SATURACAO", descending=False).head(3)

    logger.info("\n🚨 Saturação (Oceano Vermelho):")
    for row in saturados.to_dicts():
        logger.info(f"   [{row['ID_ATIVIDADE']}] {row['CNAE_FISCAL_PRINCIPAL'][:45]}... | {row['INDICE_SATURACAO']}x")

    logger.info("\n🌊 Oportunidade (Oceano Azul):")
    for row in oportunidades.to_dicts():
        logger.info(f"   [{row['ID_ATIVIDADE']}] {row['CNAE_FISCAL_PRINCIPAL'][:45]}... | {row['INDICE_SATURACAO']}x")

if __name__ == "__main__":
    fato_df, dim_ativ = calcular_fato_oportunidades()
    
    testar_fato_no_terminal(fato_df, dim_ativ, "PRAIA DA COSTA")