import polars as pl
import time
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from loguru import logger
from config import PROCESSED_DIR

def treinar_preditor_crescimento():
    logger.info("="*60)
    logger.info("PREDITOR DE CRESCIMENTO E ESCALA (MEI -> ME)")
    logger.info("="*60)
    start_time = time.time()

    # 1. Carrega as tabelas do seu Star Schema
    logger.info("[1/4] Carregando e unindo os dados do Star Schema...")
    fato = pl.read_parquet(PROCESSED_DIR / "fato_estabelecimentos.parquet")
    dim_loc = pl.read_parquet(PROCESSED_DIR / "dim_localidades.parquet")
    dim_ativ = pl.read_parquet(PROCESSED_DIR / "dim_atividades_economicas.parquet")
    dim_sit = pl.read_parquet(PROCESSED_DIR / "dim_situacoes.parquet")
    dim_data = pl.read_parquet(PROCESSED_DIR / "dim_data.parquet")

    # 2. Faz o Join
    abt = (
        fato
        .join(dim_loc, left_on="LOCALIDADE", right_on="ID_LOCALIDADE", how="inner")
        .join(dim_ativ, left_on="ATIVIDADE", right_on="ID_ATIVIDADE", how="inner")
        .join(dim_sit, left_on="SITUACAO", right_on="ID_SITUACAO", how="inner")
        .join(dim_data, left_on="DATA_INICIO", right_on="ID_DATA", how="left")
        .rename({"DATA": "DATA_INICIO_REAL"})
    )
    logger.success("Dados carregados e unidos com sucesso!")

    # 3. Engenharia de Variáveis
    logger.info("[2/4] Preparando o Alvo (Quem conseguiu crescer?)...")
    data_atual = datetime.now().date()
    abt = abt.with_columns([
        (pl.lit(data_atual) - pl.col("DATA_INICIO_REAL")).dt.total_days().alias("IDADE_DIAS")
    ])

    # Definindo quem é a empresa de Sucesso
    # Condição: Tem data de exclusão do MEI (Saiu do MEI) E continua ATIVA (Código 2). 
    # Ou seja, não faliu, apenas cresceu de tamanho!
    abt = abt.with_columns(
        pl.when(pl.col("DATA_EXCLUSAO_MEI").is_not_null() & (pl.col("CODIGO_SITUACAO") == 2))
        .then(1) # 1 = Cresceu / Escalou
        .otherwise(0) # 0 = Continua pequeno ou faliu
        .alias("TARGET_ESCALOU")
    )

    # Filtramos a base APENAS para quem já passou pelo MEI alguma vez na vida.
    # ADICIONADO: Filtro para garantir que o Bairro não seja nulo
    df_ml = abt.filter(
        (pl.col("DATA_OPCAO_MEI").is_not_null() | pl.col("DATA_EXCLUSAO_MEI").is_not_null()) &
        pl.col("IDADE_DIAS").is_not_null() &
        pl.col("MUNICIPIO").is_not_null() &
        pl.col("BAIRRO").is_not_null() # <-- Garantia de qualidade dos dados
    ).to_pandas()

    logger.info(f"      -> {len(df_ml)} microempresendedores encontrados para análise.")

    # 4. Codificando Texto para Número (IA não lê texto)
    le_cnae = LabelEncoder()
    le_municipio = LabelEncoder()
    le_bairro = LabelEncoder() # <-- Novo codificador para o Bairro
    
    df_ml['CNAE_COD'] = le_cnae.fit_transform(df_ml['CNAE_FISCAL_PRINCIPAL'])
    df_ml['MUNICIPIO_COD'] = le_municipio.fit_transform(df_ml['MUNICIPIO'])
    df_ml['BAIRRO_COD'] = le_bairro.fit_transform(df_ml['BAIRRO']) # <-- Codificando o Bairro

    # 5. Separando Pistas (X) e Resposta (y)
    # REMOVIDO: MATRIZ_FILIAL para evitar o Vazamento de Dados (Data Leakage)
    X = df_ml[['IDADE_DIAS', 'CNAE_COD', 'MUNICIPIO_COD', 'BAIRRO_COD']]
    y = df_ml['TARGET_ESCALOU']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    logger.success("Dados preparados para o modelo de Machine Learning!")
    # 6. Treinamento da IA
    logger.info("[3/4] Treinando a Inteligência Artificial...")
    
    # ADICIONADO: class_weight='balanced' para forçar a IA a dar peso igual aos acertos e falhas
    modelo = RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=42, n_jobs=-1)
    modelo.fit(X_train, y_train)

    logger.info("\n[4/4] RESULTADOS DA IA (A PROVA FINAL)")
    previsoes = modelo.predict(X_test)
    
    logger.info("\n-> Matriz de Confusão (0 = Não Cresceu, 1 = Escalou para ME):")
    logger.info(confusion_matrix(y_test, previsoes))
    logger.info("\n-> Relatório de Métricas:")
    print(classification_report(y_test, previsoes))

    # ==========================================
    # SALVANDO OS MODELOS PARA O STREAMLIT
    # ==========================================
    
    # CORREÇÃO DE CAMINHO: Força a criação da pasta 'data/models' exatamente 
    # no mesmo diretório (project) onde este script está salvo.
    BASE_DIR = Path(__file__).resolve().parent
    MODELS_DIR = BASE_DIR / "data" / "models"
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Salva o "Cérebro" da IA
    logger.info(" Salvando o modelo de Machine Learning...")
    joblib.dump(modelo, MODELS_DIR / "modelo_crescimento.joblib")
    
    # Salva os "Tradutores" (Extremamente importante para a UI interativa depois)
    logger.info(" Salvando os encoders...")
    joblib.dump(le_cnae, MODELS_DIR / "le_cnae.joblib")
    joblib.dump(le_municipio, MODELS_DIR / "le_municipio.joblib")
    joblib.dump(le_bairro, MODELS_DIR / "le_bairro.joblib")

    logger.success(f"\n✅ Execução concluída em {time.time() - start_time:.2f} segundos!")
    logger.info(f"📁 Modelos e Encoders salvos na pasta: {MODELS_DIR}")

if __name__ == "__main__":
    treinar_preditor_crescimento()