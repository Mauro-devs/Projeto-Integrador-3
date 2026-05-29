import time
from pathlib import Path
from file_handler import batch_zip_to_csv
from config import ZIP_DIR, CSV_DIR

def run_extraction():
    dir_origem = Path(ZIP_DIR)
    
    # Caso a pasta não exista
    if not dir_origem.exists():
        print(f"[Erro] A pasta de origem não existe: {dir_origem}")
        print("Você deve criar esta pasta e colocar os .zips dentro!!!")
        return

    # apenas pega arquivos .zip dentro da pasta
    zips_names = [item.name for item in dir_origem.glob('*.zip')]
    
    if not zips_names:
        print(f"[Aviso] Nenhum arquivo .zip encontrado em {dir_origem}")
        return

    print("Iniciando ETL: Extração e Conversão...")
    start_time = time.time()

    # Conversão
    batch_zip_to_csv(ZIP_DIR, zips_names, CSV_DIR)
    
    # Tempo de duração
    elapsed = time.time() - start_time
    print(f"Tempo total de extração: {elapsed:.2f} segundos.")




if __name__ == '__main__':
    run_extraction()