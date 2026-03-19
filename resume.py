import os
import pandas as pd

data_path = "data"

files = [f for f in os.listdir(data_path) if f.endswith(".csv")]

dias_completos = 0
dias_incompletos = 0

arquivos_sem_dia_completo = []

for file in files:
    file_path = os.path.join(data_path, file)
    
    try:
        df = pd.read_csv(file_path, sep=";", decimal=",", encoding="latin1")
        
        if "Data" in df.columns and "P - Total (W)" in df.columns:
            
            # Converter para datetime
            df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y, %H:%M:%S")
            
            # Extrair apenas o dia
            df["dia"] = df["Data"].dt.date
            
            # Contar medições válidas por dia
            contagem = df.dropna(subset=["P - Total (W)"]).groupby("dia").size()
            
            tem_dia_completo = False
            
            for dia, qtd in contagem.items():
                print(f"{file} - {dia}: {qtd} medições")
                
                if qtd == 1440:
                    dias_completos += 1
                    tem_dia_completo = True
                else:
                    dias_incompletos += 1
            
            # Verificar se nenhum dia foi completo
            if not tem_dia_completo:
                arquivos_sem_dia_completo.append(file)
        
        else:
            print(f"{file}: colunas necessárias não encontradas")
    
    except Exception as e:
        print(f"{file}: erro -> {e}")

# 🔥 Resumo final
print("\n===== RESUMO =====")
print(f"Dias com 1440 medições: {dias_completos}")
print(f"Dias incompletos: {dias_incompletos}")

print("\nArquivos sem nenhum dia completo:")
for arq in arquivos_sem_dia_completo:
    print(f"- {arq}")