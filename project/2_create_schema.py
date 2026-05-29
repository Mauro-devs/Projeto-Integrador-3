import polars as pl
from polars import LazyFrame
import time
from pathlib import Path
from config import (
    CSV_DIR, PROCESSED_DIR, TARGET_UF, 
    COLS_EMPRESAS, COLS_ESTAB, COLS_SIMPLES, COLS_CNAES
)

def coletar_cnaes_secundarios(lazy_cnae: LazyFrame) -> dict[str, str]:
    df_cnae = lazy_cnae.collect()
    cnae_map = dict(zip(df_cnae["codigo"], df_cnae["descricao"]))
    return cnae_map

def criar_staging(caminho_estab: str, caminho_empresas, caminho_simples, caminho_cnae, caminho_municipios):
    print("\n[Fase 1] Criando Staging Area...")
    
    # Estabelecimentos filtrados por UF
    lazy_estab = pl.scan_csv(
        caminho_estab, separator=";", has_header=False, 
        new_columns=COLS_ESTAB, infer_schema_length=0
    ).filter(pl.col("uf") == TARGET_UF)

    lazy_cnae = pl.scan_csv(
        caminho_cnae, separator=';', has_header=False,
        new_columns=COLS_CNAES, infer_schema_length=0
    )
    
    cnpjs_validos = lazy_estab.select("cnpj_basico").unique()

    # Empresas
    lazy_empresas = pl.scan_csv(
        caminho_empresas, separator=";", has_header=False, 
        new_columns=COLS_EMPRESAS, infer_schema_length=0
    ).join(cnpjs_validos, on="cnpj_basico", how="inner")

    # Simples/MEI
    lazy_simples = pl.scan_csv(
        caminho_simples, separator=";", has_header=False, 
        new_columns=COLS_SIMPLES, infer_schema_length=0
    ).join(cnpjs_validos, on="cnpj_basico", how="inner")

    # Municípios
    lazy_municipios = pl.scan_csv(
        caminho_municipios, separator=';', has_header=False,
        new_columns=["codigo_mun", "nome_municipio"], infer_schema_length=0
    )

    cnaes_secundarios = coletar_cnaes_secundarios(lazy_cnae=lazy_cnae)

    # Base plana temporária
    staging_lazy = (
        lazy_estab
        .join(lazy_empresas, on="cnpj_basico", how="left")
        .join(lazy_simples, on="cnpj_basico", how="left")
        .join(lazy_cnae, left_on="cnae_principal", right_on="codigo" ,how="left")
        .join(lazy_municipios, left_on="municipio", right_on="codigo_mun", how="left")
        .with_columns([
            pl.concat_str(["cnpj_basico", "cnpj_ordem", "cnpj_dv"]).alias("CNPJ_COMPLETO"),
            pl.concat_str(["tipo_logradouro", pl.lit(" "), "logradouro"]).alias("logradouro_completo"),
            pl.col("cnaes_secundarios").fill_null("").str.split(",").list.eval(pl.element().replace(cnaes_secundarios, default=pl.element())).list.join(" | ")
        ])
        .rename({"cnae_principal": "codigo_cnae", "descricao": "cnae_principal"})
        .drop("municipio")
        .rename({"nome_municipio": "municipio"})
    )

    staging_path = PROCESSED_DIR / "temp_staging.parquet"
    staging_lazy.sink_parquet(staging_path)
    return staging_path

def criacao_dimensoes(staging):
    print("\n[Fase 2] Gerando Dimensões...")

    # --- DIM_LOCALIDADES (COM PRESERVAÇÃO DE GEO) ---
    print("   -> Processando Localidades...")
    nova_dim_loc = (
        staging.select([
            pl.col("cep").alias("CEP"), pl.col("uf").alias("UF"), 
            pl.col("municipio").alias("MUNICIPIO"), pl.col("bairro").alias("BAIRRO"),
            pl.col("logradouro_completo").alias("LOGRADOURO")
        ])
        .drop_nulls().unique().collect()
    )

    caminho_loc = PROCESSED_DIR / "dim_localidades.parquet"
    
    if caminho_loc.exists():
        print("      ⚠️  Base encontrada! Recuperando coordenadas geográficas...")
        dim_antiga_geo = pl.read_parquet(caminho_loc).select([
            "CEP", "LATITUDE", "LONGITUDE"
        ]).unique(subset=["CEP"])
        
        nova_dim_loc = nova_dim_loc.join(dim_antiga_geo, on="CEP", how="left")
    else:
        print("      🆕 Criando colunas de coordenadas vazias...")
        nova_dim_loc = nova_dim_loc.with_columns([
            pl.lit(None).cast(pl.Float64).alias("LATITUDE"),
            pl.lit(None).cast(pl.Float64).alias("LONGITUDE")
        ])

    dim_localidades = nova_dim_loc.with_row_index("ID_LOCALIDADE", offset=1)
    dim_localidades.write_parquet(caminho_loc)

    # --- DIM_ATIVIDADES_ECONOMICAS ---
    print("   -> Processando Atividades...")
    dim_atividades = (
        staging.select([
            pl.col("codigo_cnae").alias("CODIGO_CNAE"),
            pl.col("cnae_principal").alias("CNAE_FISCAL_PRINCIPAL")
        ])
        .drop_nulls(subset=["CNAE_FISCAL_PRINCIPAL"]).unique().collect()
        .with_row_index("ID_ATIVIDADE", offset=1)
    )
    dim_atividades.write_parquet(PROCESSED_DIR / "dim_atividades_economicas.parquet")

    # --- DIM_SITUACOES ---
    dim_situacoes = (
        staging.select(pl.col("situacao_cadastral").cast(pl.Int32).alias("CODIGO_SITUACAO"))
        .drop_nulls().unique().collect()
        .with_row_index("ID_SITUACAO", offset=1)
    )
    dim_situacoes.write_parquet(PROCESSED_DIR / "dim_situacoes.parquet")

    # --- DIM_PERFIS_TRIBUTARIOS ---
    map_simples_mei = {"S": 1, "N": 0}
    dim_perfis = (
        staging.select([
            pl.col("opcao_simples").replace_strict(map_simples_mei, default=None).cast(pl.Int32).alias("OPCAO_SIMPLES"),
            pl.col("opcao_mei").replace_strict(map_simples_mei, default=None).cast(pl.Int32).alias("OPCAO_MEI")
        ])
        .unique().collect()
        .with_row_index("ID_PERFIL", offset=1)
    )
    dim_perfis.write_parquet(PROCESSED_DIR / "dim_perfis_tributarios.parquet")

    # --- DIM_DATA ---
    colunas_de_data = ["data_inicio_atividade", "data_opcao_simples", "data_exclusao_simples", "data_opcao_mei", "data_exclusao_mei"]
    datas_unicas = [staging.select(pl.col(col).alias("DATA_STR")).drop_nulls().unique().collect() for col in colunas_de_data]
    
    dim_data = (
        pl.concat(datas_unicas).unique()
        .filter(pl.col("DATA_STR") != "00000000") 
        .with_row_index("ID_DATA", offset=1)
        .with_columns(pl.col("DATA_STR").str.strptime(pl.Date, "%Y%m%d", strict=False).alias("DATA"))
    )
    dim_data.select(["ID_DATA", "DATA", "DATA_STR"]).write_parquet(PROCESSED_DIR / "dim_data.parquet")

    return dim_localidades, dim_atividades, dim_situacoes, dim_perfis, dim_data, map_simples_mei

def processar_star_schema():
    print(f"Iniciando modelagem Star Schema para UF: {TARGET_UF}")
    start_time = time.time()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    caminho_estab = str(CSV_DIR / "*Estabele*.csv")
    caminho_empresas = str(CSV_DIR / "*Empre*.csv")
    caminho_simples = str(CSV_DIR / "*Simples*.csv")
    caminho_cnae = str(CSV_DIR / "*Cnaes.csv*")
    caminho_municipios = str(CSV_DIR / "*Municipios*.csv")

    staging_path = criar_staging(caminho_estab, caminho_empresas, caminho_simples, caminho_cnae, caminho_municipios)
    staging = pl.scan_parquet(staging_path)

    dim_localidades, dim_atividades, dim_situacoes, dim_perfis, dim_data, map_simples_mei = criacao_dimensoes(staging)

    print("\n[Fase 3] Construindo Tabela Fato...")
    lazy_dim_loc = dim_localidades.lazy()
    lazy_dim_ativ = dim_atividades.lazy()
    lazy_dim_sit = dim_situacoes.lazy()
    lazy_dim_perf = dim_perfis.lazy()
    lazy_dim_data_join = dim_data.select(["ID_DATA", "DATA_STR"]).lazy()

    fato = (
        staging
        .join(lazy_dim_loc, left_on=["cep", "uf", "municipio", "bairro", "logradouro_completo"], 
              right_on=["CEP", "UF", "MUNICIPIO", "BAIRRO", "LOGRADOURO"], how="left")
        .join(lazy_dim_ativ, left_on="cnae_principal", right_on="CNAE_FISCAL_PRINCIPAL", how="left")
        .with_columns(pl.col("situacao_cadastral").cast(pl.Int32).alias("sit_cast"))
        .join(lazy_dim_sit, left_on="sit_cast", right_on="CODIGO_SITUACAO", how="left")
        .with_columns([
            pl.col("opcao_simples").replace_strict(map_simples_mei, default=None).cast(pl.Int32).alias("op_simp_cast"),
            pl.col("opcao_mei").replace_strict(map_simples_mei, default=None).cast(pl.Int32).alias("op_mei_cast")
        ])
        .join(lazy_dim_perf, left_on=["op_simp_cast", "op_mei_cast"], right_on=["OPCAO_SIMPLES", "OPCAO_MEI"], how="left")
        .join(lazy_dim_data_join, left_on="data_inicio_atividade", right_on="DATA_STR", how="left")
        .rename({"ID_DATA": "DATA_INICIO"})
        .join(lazy_dim_data_join, left_on="data_opcao_simples", right_on="DATA_STR", how="left")
        .rename({"ID_DATA": "DATA_OPCAO_SIMPLES"})
        .join(lazy_dim_data_join, left_on="data_exclusao_simples", right_on="DATA_STR", how="left")
        .rename({"ID_DATA": "DATA_EXCLUSAO_SIMPLES"})
        .join(lazy_dim_data_join, left_on="data_opcao_mei", right_on="DATA_STR", how="left")
        .rename({"ID_DATA": "DATA_OPCAO_MEI"})
        .join(lazy_dim_data_join, left_on="data_exclusao_mei", right_on="DATA_STR", how="left")
        .rename({"ID_DATA": "DATA_EXCLUSAO_MEI"})
        .select([
            pl.col("CNPJ_COMPLETO").alias("CNPJ"),
            pl.col("ID_LOCALIDADE").alias("LOCALIDADE"),
            pl.col("ID_ATIVIDADE").alias("ATIVIDADE"),
            pl.col("ID_PERFIL").alias("PERFIL"),
            pl.col("ID_SITUACAO").alias("SITUACAO"),
            pl.col("cnaes_secundarios").fill_null("").str.split(" | ").alias("CNAE_FISCAL_SECUNDARIO"),
            pl.col("DATA_INICIO"),
            pl.col("DATA_OPCAO_SIMPLES"),
            pl.col("DATA_EXCLUSAO_SIMPLES"),
            pl.col("DATA_OPCAO_MEI"),
            pl.col("DATA_EXCLUSAO_MEI"),
            pl.col("identificador_matriz_filial").cast(pl.Int32).alias("MATRIZ_FILIAL")
        ])
    )

    fato.sink_parquet(PROCESSED_DIR / "fato_estabelecimentos.parquet")
    Path(staging_path).unlink(missing_ok=True)

    print(f"\nPROCESSO CONCLUIDO COM SUCESSO. Tempo: {time.time() - start_time:.2f} segundos.")

if __name__ == "__main__":
    processar_star_schema()