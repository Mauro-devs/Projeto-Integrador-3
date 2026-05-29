import polars as pl
import numpy as np
from config import PROCESSED_DIR
from loguru import logger
INPUT_PATH = PROCESSED_DIR / "data" / "processed" / "amostra_geocodificada.parquet"

"""
    Calcula a distância em metros entre duas coordenadas geográficas usando a fórmula de Haversine.
"""
def calcular_distancia_metros(lat_origem: float, lon_origem: float, lat_destino: float, lon_destino: float) -> float:
    RAIO_TERRA_METROS = 6371000 
    
    # Converte coordenadas de graus para radianos
    lat1_rad = np.radians(lat_origem)
    lat2_rad = np.radians(lat_destino)
    delta_lat_rad = np.radians(lat_destino - lat_origem)
    delta_lon_rad = np.radians(lon_destino - lon_origem)
    
    # Aplicação da fórmula matemática (Haversine)
    a = np.sin(delta_lat_rad / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon_rad / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return RAIO_TERRA_METROS * c

# Simula a análise de viabilidade de um ponto comercial.
def analisar_ponto_comercial(lat_usuario, lon_usuario, raio_metros=1000):
    if not INPUT_PATH.exists():
        logger.error(f"Erro: Arquivo {INPUT_PATH} nao encontrado.")
        return

    df = pl.read_parquet(INPUT_PATH).filter(pl.col("latitude").is_not_null())
    
    distancias = [
        calcular_distancia_metros(lat_usuario, lon_usuario, lat, lon)
        for lat, lon in zip(df["latitude"], df["longitude"])
    ]
    
    df = df.with_columns(pl.Series(name="distancia_m", values=distancias))
    vizinhos = df.filter(pl.col("distancia_m") <= raio_metros)
    
    total_ativas = vizinhos.filter(pl.col("situacao_cadastral") == 2).height
    total_baixadas = vizinhos.filter(pl.col("situacao_cadastral") == 8).height
    
    logger.info(f"\n--- RESULTADOS DO RADAR ---")
    logger.info(f"Total de estabelecimentos no raio: {vizinhos.height}")
    logger.info(f"Ativas: {total_ativas}")
    logger.info(f"Baixadas: {total_baixadas}")

if __name__ == "__main__":
    # Coordenadas de teste em Jardim Camburi
    lat_teste, lon_teste = -20.2603, -40.2695
    analisar_ponto_comercial(lat_teste, lon_teste, raio_metros=1000)