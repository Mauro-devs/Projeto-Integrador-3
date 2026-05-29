import polars as pl
import time
from geopy.geocoders import Nominatim
from config import PROCESSED_DIR
from loguru import logger
DIM_PATH = PROCESSED_DIR / "dim_localidades.parquet"

"""
    Fica esperando o servidor docker do Nominatim subir
    tenta a cada 30 segundos 30 vezes.
"""
def aguardar_servidor(geolocator, max_tentativas=30, espera_segundos=10):
    logger.info("Verificando se o servidor Nominatim está pronto")
    for tentativa in range(1, max_tentativas + 1):
        try:
            geolocator.geocode("Vitória - ES, Brasil")
            logger.info("O servidor está ONLINE e pronto.")
            return True
        except Exception:
            logger.info(f"Servidor iniciando... (Tentativa {tentativa}/{max_tentativas}). Aguardando {espera_segundos}s...")
            time.sleep(espera_segundos)
    
    logger.error("O servidor não respondeu a tempo.")
    return False

def geocodificar(geolocator, logradouro, bairro, municipio, uf, cep):
    query_geocodificacao = {
        "street": logradouro,
        "district": bairro,
        "city": municipio,
        "state": uf,
        "postalcode": cep,
        "country": "Brazil"
    }

    try:
        # 1. Tenta a busca principal
        location = geolocator.geocode(query_geocodificacao, addressdetails=True)
        status_log = "OK"
        
        # 2. Tenta o fallback se a principal falhar
        if not location:
            fallback_query = {"postalcode": cep, "country": "Brazil"}
            location = geolocator.geocode(fallback_query, addressdetails=True)
            status_log = "FALLBACK"

        # 3. Verifica se falhou mesmo após o fallback
        if not location:
            return {
                "status": "NÃO ENCONTRADO",
                "latitude": float("nan"),
                "longitude": float("nan"),
                "logradouro": logradouro,
                "bairro": bairro,
                "municipio": municipio,
                "uf": uf,
                "cep": cep
            }
            
        # 4. Caso tenha encontrado (OK ou FALLBACK)
        address = location.raw.get('address', {})
        
        bairro_found = address.get('suburb') or address.get('neighbourhood') or address.get('hamlet') or address.get('township')
        cidade_found = address.get('city') or address.get('town') or address.get('village') or address.get('municipality')
        
        return {
            "status": status_log,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "logradouro": address.get('road') or logradouro,
            "bairro": bairro_found or bairro,
            "municipio": cidade_found or municipio,
            "uf": address.get('state') or uf,
            "cep": address.get('postcode') or cep
        }

    except Exception as e:
        return {
            "status": "ERRO",
            "erro_msg": str(e),
            "latitude": None,
            "longitude": None,
            "logradouro": logradouro,
            "bairro": bairro,
            "municipio": municipio,
            "uf": uf,
            "cep": cep
        }

"""
    Pega todas as localidades do dim_localidades.parquet
    que tiverem as coordenadas null.

    Para cada localidade, utiliza as informações dela (Logradouro, Bairro, Municipio, UF)
    em uma pesquisa indexada no Nominatim para encontrar as coordenadas dessa localização.

    A cada 1000 registros processados ele salva no dim_localidades.parquet
"""
def processar_coordenadas(escolha: int):
    logger.info("Iniciando geocodificação da dimensão de localidades")
    
    df = pl.read_parquet(DIM_PATH)
    
    # Garante que as colunas de coordenadas existam
    if "LATITUDE" not in df.columns:
        df = df.with_columns([
            pl.lit(None).cast(pl.Float64).alias("LATITUDE"),
            pl.lit(None).cast(pl.Float64).alias("LONGITUDE")
        ])

    
    # Ele pega todas as localidades que não foram processadas ainda
    # ignorando localidades que já foram processadas mas que não encontraram as coordenadas
    if escolha == 1:
        df_pendentes = df.filter(pl.col("LATITUDE").is_null())
    # Ele pega todas as localidades que não foram processadas e que não encontraram as coordenadas
    elif escolha == 2:
        df_pendentes = df.filter((pl.col("LATITUDE").is_nan()) | (pl.col("LATITUDE").is_null()))
    # Ele simplesmente pega todas as localidades (mesmo as já processadas)
    else:
        df_pendentes = df

    qtd_pendentes = df_pendentes.height
    logger.info(f"Total de registros: {df.height} | Pendentes de geocodificação: {qtd_pendentes}\n")

    if qtd_pendentes == 0:
        logger.success("Todos os endereços já possuem coordenadas! Nada a fazer.")
        return

    # Instancia do Nominatim
    geolocator = Nominatim(domain="localhost:8080", scheme="http", user_agent="radar_competitivo_local")

    # Se o servidor não rodar dentro do tempo esperado
    if not aguardar_servidor(geolocator):
        return

    # Listas com os dados processados para inserir na dimensão de volta
    ids_atualizados = []
    latitudes = []
    longitudes = []
    logradouros_list = []
    bairros_list = []
    municipios_list = []
    ufs_list = []
    ceps_list = []

    # Contadores para mostrar na tela
    contador_encontrado = 0
    contador_fallback = 0
    contador_nao_encontrado = 0
    
    # Contador para o log final
    total_processados_agora = 0

    logger.info("-" * 80)
    
    for i, row in enumerate(df_pendentes.to_dicts(), start=1):
        id_localidade = row['ID_LOCALIDADE'] 
        logradouro = row.get('LOGRADOURO', '') or ''
        bairro = row.get('BAIRRO', '') or ''
        municipio = row.get('MUNICIPIO', '') or ''
        uf = row.get('UF', '') or ''
        cep = row.get('CEP', '') or ''

        endereco_completo = f"{logradouro}, {bairro}, {municipio} - {cep} - {uf}, Brasil"
        endereco_curto = endereco_completo[:45].ljust(48, ".")
        logger.info(f"[{i}/{qtd_pendentes}] {endereco_curto}", end="", flush=True)

        resultado = geocodificar(geolocator, logradouro, bairro, municipio, uf, cep)
        
        ids_atualizados.append(id_localidade)
        latitudes.append(resultado["latitude"])
        longitudes.append(resultado["longitude"])
        logradouros_list.append(resultado["logradouro"])
        bairros_list.append(resultado["bairro"])
        municipios_list.append(resultado["municipio"])
        ufs_list.append(resultado["uf"])
        ceps_list.append(resultado["cep"])

        status = resultado["status"]
        if status == "OK":
            contador_encontrado += 1
            logger.success(f" ✅ OK ({resultado['latitude']:.4f}, {resultado['longitude']:.4f})")
        elif status == "FALLBACK":
            contador_fallback += 1
            logger.warning(f" ⚠️ FALLBACK ({resultado['latitude']:.4f}, {resultado['longitude']:.4f})")
        elif status == "NÃO ENCONTRADO":
            contador_nao_encontrado += 1
            logger.error(" ❌ NÃO ENCONTRADO")
        elif status == "ERRO":
            logger.error(f" 💥 ERRO: {resultado['erro_msg']}")

        # A cada 1000 localidades processadas ele salva no dim_localidades
        if i % 1000 == 0:
            logger.info(f"\n[AUTO-SAVE] Salvando lote de 1000 registros no disco... ({i}/{qtd_pendentes})")
            logger.info(f"Total encontrados: {contador_encontrado}")
            logger.info(f"Total fallback: {contador_fallback}")
            logger.info(f"Total não encontrados: {contador_nao_encontrado}")

            df_temp = pl.DataFrame({
                "ID_LOCALIDADE": ids_atualizados,
                "LATITUDE": latitudes,
                "LONGITUDE": longitudes,
                "LOGRADOURO": logradouros_list,
                "BAIRRO": bairros_list,
                "MUNICIPIO": municipios_list,
                "UF": ufs_list,
                "CEP": ceps_list
            })
            
            # Atualiza o DataFrame principal e salva no disco
            df = df.update(df_temp, on="ID_LOCALIDADE")
            df.write_parquet(DIM_PATH)
            
            total_processados_agora += len(ids_atualizados)
            
            # Esvazia as listas para começar o próximo lote limpo
            ids_atualizados.clear()
            latitudes.clear()
            longitudes.clear()
            logradouros_list.clear()
            bairros_list.clear()
            municipios_list.clear()
            ufs_list.clear()
            ceps_list.clear()
            
            logger.info("[AUTO-SAVE] Concluído! Retomando buscas...\n")

    logger.info("-" * 80)

    # Salvamento final dos que sobraram
    if len(ids_atualizados) > 0:
        logger.info(f"\n[FINALIZANDO] Salvando as últimas {len(ids_atualizados)} ruas que restaram...")

        logger.info(f"Total encontrados: {contador_encontrado}")
        logger.info(f"Total fallback: {contador_fallback}")
        logger.info(f"Total não encontrados: {contador_nao_encontrado}")

        df_temp = pl.DataFrame({
            "ID_LOCALIDADE": ids_atualizados,
            "LATITUDE": latitudes,
            "LONGITUDE": longitudes,
            "LOGRADOURO": logradouros_list,
            "BAIRRO": bairros_list,
            "MUNICIPIO": municipios_list,
            "UF": ufs_list,
            "CEP": ceps_list
        })
        df = df.update(df_temp, on="ID_LOCALIDADE")
        df.write_parquet(DIM_PATH)
        total_processados_agora += len(ids_atualizados)

    logger.info(f"\nProcesso 100% concluído! {total_processados_agora} coordenadas processadas nesta sessão e salvas em: {DIM_PATH}")

if __name__ == "__main__":
    logger.info("="*30)
    logger.info("1 - Geocodificar apenas localidades não processadas ainda")
    logger.info("2 - Geocodificar todas as localidades que não foram processadas e que já foram mas não foram encontradas as coordenadas")
    logger.info("3 - Geocodificar todas as localidades")
    logger.info("Outro - Sair")

    escolha = input(">> ")
    logger.info("="*30)

    try:
        escolha = int(escolha)

        if escolha >= 1 and escolha <= 3:
            processar_coordenadas(escolha)
        else:
            logger.info("Bye")

    except Exception:
        logger.info("Bye")