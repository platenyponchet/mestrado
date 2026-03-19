import os
import pandas as pd
import json

data_path = "data"
output_path = "output"

# Criar pasta output se não existir
os.makedirs(output_path, exist_ok=True)

# 🔥 Limpar tudo dentro da pasta output
for f in os.listdir(output_path):
    file_to_remove = os.path.join(output_path, f)
    if os.path.isfile(file_to_remove):
        os.remove(file_to_remove)

files = [f for f in os.listdir(data_path) if f.endswith(".csv")]

for file in files:
    file_path = os.path.join(data_path, file)
    
    try:
        df = pd.read_csv(file_path, sep=";", decimal=",", encoding="latin1")
        
        if "Data" in df.columns and "P - Total (W)" in df.columns:
            
            # Converter datetime
            df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y, %H:%M:%S")
            
            # Ordenar
            df = df.sort_values("Data")
            
            # Criar coluna de dia
            df["dia"] = df["Data"].dt.date
            
            # Agrupar por dia
            grupos = df.groupby("dia")
            
            for dia, grupo in grupos:
                
                grupo = grupo.dropna(subset=["P - Total (W)"])
                
                if len(grupo) == 1440:
                    
                    lista_potencia = grupo["P - Total (W)"].tolist()
                    
                    nome_base = file.replace(".csv", "")
                    nome_saida = f"{nome_base}--{dia}.json"
                    caminho_saida = os.path.join(output_path, nome_saida)
                    
                    # 💾 Salvar como JSON (lista pura)
                    with open(caminho_saida, "w") as f:
                        json.dump(lista_potencia, f)
                    
                    print(f"Salvo: {nome_saida}")
        
        else:
            print(f"{file}: colunas necessárias não encontradas")
    
    except Exception as e:
        print(f"{file}: erro -> {e}")