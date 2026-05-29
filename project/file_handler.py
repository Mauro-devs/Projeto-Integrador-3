"""
    Este módulo possui funções para lidar com os arquivos .zip
"""


import zipfile
import io
from pathlib import Path
from typing import List
from loguru import logger

"""
    Passa o caminho de um .zip que contenha um csv, 
    e o converte para utf-8 e joga o csv extraido para uma pasta de destino

    ex:
        entrada -> zip_path="projeto/data/raw/Empresa.zip", destination_path="projeto/data/processed/"
        
        saída -> Arquivo Empresa.zip vai para projeto/data/processed/Empresa.csv (com a formatação utf-8)
"""
def zip_to_csv(zip_path: str, destination_path: str, og_encoding: str="latin1", dest_encoding: str="utf-8") -> None:
    zip_path: Path = Path(zip_path)
    destination_path: Path = Path(destination_path)
    
    # Garante que a pasta de destino exista (cria ela caso não)
    destination_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Abrindo arquivo: {zip_path.name}")
    
    # Abre o .zip em leitura
    with zipfile.ZipFile(zip_path, 'r') as z:

        # Caso tenha mais de 1 arquivo dentro do .zip
        many = len(z.namelist()) > 1  

        # Itera sobre cada arquivo dentro do .zip
        for i, internal_file_name in enumerate(z.namelist()):

            # Caso tenham mais de 1 arquivo, para não repetir nome
            # .stem retorna o  nome do arquivo sem extensão
            if many:
                file_name = f"{zip_path.stem}_{i}.csv"
            else:
                file_name = f"{zip_path.stem}.csv"

            # Caminho completo final
            final_path = destination_path / file_name

            logger.info(f" -> Convertendo '{internal_file_name}' para {dest_encoding}...")
            
            # Lê o arquivo
            with z.open(internal_file_name, 'r') as arquivo_zipado:
                # Cria um leitor de streams
                text_reader = io.TextIOWrapper(arquivo_zipado, encoding=og_encoding, errors='replace')

                # Escreve cada stream convertendo o encoding no arquivo de saída (.csv)
                with open(final_path, 'w', encoding=dest_encoding) as output_file:
                    for line in text_reader:
                        output_file.write(line)
            logger.success(f" -> Sucesso! Salvo em: {final_path}\n")

"""
    entrada:
        Passa o caminho da pasta dos .zips
        Passa uma lista de nomes de arquivos para processar (nome de cada zip que você quer)
        Passa o caminho da pasta de destino e as codificações de entrada e saída

    saída:
        Pega os .zips do caminho de entrda, converte de latin1 para utf8 
        e grava no caminho da pasta de destino como .csv
"""
def batch_zip_to_csv(source_folder: str, zip_filenames: List[str], destination_folder: str, og_encoding: str="latin1", dest_encoding: str="utf-8") -> None:
    source_folder = Path(source_folder)
    
    # Verifica se a pasta de origem existe
    if not source_folder.exists() or not source_folder.is_dir():
        logger.error(f"[Erro] A pasta de origem não existe ou não é um diretório: {source_folder}")
        return

    logger.info(f"Iniciando processamento em lote de {len(zip_filenames)} arquivo(s)...\n" + "-"*40)

    # Itera sobre os nomes fornecidos na lista
    for zip_name in zip_filenames:
        # Monta o caminho completo: pasta_origem / nome_do_arquivo
        full_zip_path = source_folder / zip_name
        
        # Verifica se o arquivo específico existe antes de tentar abrir
        if not full_zip_path.exists():
            logger.warning(f"[Aviso] Arquivo não encontrado na pasta, ignorando: {zip_name}\n")
            continue
        
        # Tenta processar o arquivo. Se um falhar (ex: ZIP corrompido), o script continua
        try:
            # Chama a função de conversão
            zip_to_csv(
                zip_path=str(full_zip_path),
                destination_path=destination_folder,
                og_encoding=og_encoding,
                dest_encoding=dest_encoding
            )
        except Exception as e:
            message = f"ERRO FATAL: Falha ao converter o arquivo '{zip_name}'. O processamento em lote foi interrompido."
            logger.error(message)
            raise RuntimeError(message) from e
            
    logger.success("-" * 40 + "\nProcessamento em lote concluído!")