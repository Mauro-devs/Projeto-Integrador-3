import polars as pl
from config import PROCESSED_DIR

OUTPUT_PATH = PROCESSED_DIR / "amostra_espacial.parquet"

def criar_amostra_ficticia():
    """
    Gera um dataset fictício de empresas para testar geocodificação e distâncias.
    """
    print("Gerando dados fictícios para testes espaciais...")
    
    dados = {
        "cnpj_basico": ["11111111", "22222222", "33333333", "44444444", "55555555"],
        "razao_social": ["PADARIA PAO QUENTE", "FARMACIA SAUDE", "MERCADO DO BAIRRO", "ACADEMIA FORCA", "PETSHOP ANIMAL"],
        "cnae_principal": ["1071600", "4771701", "4712300", "9313100", "4789004"],
        "situacao_cadastral": [2, 2, 8, 2, 2], 
        "logradouro": ["AVENIDA CARLOS GOMES DE SA", "RUA CARLOS MARTINS", "RUA VICTORINO CARDOSO", "RUA RANULPHO BARBOSA DOS SANTOS", "RUA JOAO DA CRUZ"],
        "numero": ["100", "500", "250", "800", "150"],
        "bairro": ["JARDIM CAMBURI", "JARDIM CAMBURI", "JARDIM CAMBURI", "JARDIM CAMBURI", "JARDIM CAMBURI"],
        "municipio": ["VITORIA", "VITORIA", "VITORIA", "VITORIA", "VITORIA"],
        "uf": ["ES", "ES", "ES", "ES", "ES"],
        "cep": ["29090-000", "29090-060", "29090-820", "29090-120", "29090-000"]
    }
    
    df_amostra = pl.DataFrame(dados)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_amostra.write_parquet(OUTPUT_PATH)
    
    print(f"Sucesso! Amostra criada e salva em: {OUTPUT_PATH}")

if __name__ == "__main__":
    criar_amostra_ficticia()