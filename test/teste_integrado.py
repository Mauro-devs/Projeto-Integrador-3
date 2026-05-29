import subprocess
from pathlib import Path
from config import BASE_DIR

def formatar_print(titulo):
    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print(f"{'='*50}")

def testar_tudo():
    formatar_print("INICIANDO TESTE INTEGRADO DO RADAR")

    # Passo 1: Gerar Amostra
    print("Passo 1: Criando base de dados de teste...")
    subprocess.run(["python", str(BASE_DIR / "4_gerar_amostra.py")], check=True)

    # Passo 2: Geocodificar
    print("\nPasso 2: Convertendo enderecos em coordenadas GPS...")
    subprocess.run(["python", str(BASE_DIR / "5_geocodificar.py")], check=True)

    # Passo 3: Analise de Raio
    print("\nPasso 3: Calculando concorrencia e mortalidade no raio...")
    resultado = subprocess.run(
        ["python", str(BASE_DIR / "6_calculo_raio.py")], 
        capture_output=True, 
        text=True
    )
    
    # O "conserto": Agora procuramos por 'RESULTADOS' que o seu script 6 ja imprime
    if "RESULTADOS" in resultado.stdout:
        formatar_print("TESTE CONCLUIDO COM SUCESSO")
        # Filtra as linhas para mostrar o resumo numerico no terminal
        for linha in resultado.stdout.split('\n'):
            if any(x in linha for x in ["Total", "Ativas", "Baixadas"]):
                print(linha.strip())
    else:
        print("Erro: O radar nao retornou os resultados esperados no terminal.")
        print("Dica: Verifique se o script 6_calculo_raio.py imprime a linha '--- RESULTADOS DO RADAR ---'")

if __name__ == "__main__":
    try:
        testar_tudo()
    except Exception as e:
        print(f"\nFalha no teste integrado: {e}")