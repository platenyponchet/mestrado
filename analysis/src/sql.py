import duckdb
import pandas as pd
from datetime import datetime
import argparse
import sys
import os
import readline

HISTORY_FILE = ".sql_history"

def setup_readline():
    # carregar histórico anterior (se existir)
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)

    # tamanho máximo do histórico
    readline.set_history_length(1000)

    # habilitar navegação e busca tipo bash
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode emacs")
    readline.parse_and_bind('"\\e[A": previous-history')  # seta ↑
    readline.parse_and_bind('"\\e[B": next-history')      # seta ↓
    readline.parse_and_bind('"\\C-r": reverse-search-history')  # Ctrl+R


def save_history():
    readline.write_history_file(HISTORY_FILE)


def main():
    parser = argparse.ArgumentParser(description="Console SQL interativo para CSV")
    parser.add_argument("--csv", type=str, required=True, help="Caminho do arquivo CSV")
    parser.add_argument("--log", type=str, default="query_log.txt", help="Arquivo de log")

    args = parser.parse_args()

    # setup readline
    setup_readline()

    # carregar CSV
    try:
        df = pd.read_csv(args.csv)
    except Exception as e:
        print(f"Erro ao carregar CSV: {e}")
        sys.exit(1)

    # conectar DuckDB
    con = duckdb.connect()
    con.register("df", df)

    print(f"CSV carregado: {args.csv}")
    print("Console SQL interativo (↑ ↓ histórico | Ctrl+R busca | Ctrl+C sair)\n")

    try:
        while True:
            try:
                query = input("SQL> ").strip()
            except EOFError:
                break

            if query.lower() in ["sair", "exit", "quit"]:
                print("Encerrando...")
                break

            if not query:
                continue

            # salva no histórico
            readline.add_history(query)

            try:
                resultado = con.execute(query).df()

                print(resultado.head(20).to_string(index=False))

                with open(args.log, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now()}]\n")
                    f.write(query + "\n")
                    f.write(resultado.to_string(index=False) + "\n")

            except Exception as e:
                print(f"Erro: {e}")
                with open(args.log, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now()}]\n")
                    f.write(query + "\n")
                    f.write(f"ERRO: {e}\n")

    except KeyboardInterrupt:
        print("\nEncerrado via Ctrl+C 👋")

    finally:
        save_history()


if __name__ == "__main__":
    main()