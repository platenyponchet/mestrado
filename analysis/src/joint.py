import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import sys

def main():
    # 1. Argumentos
    parser = argparse.ArgumentParser(description='Visualiza resultados de compressão (comparação de algoritmos).')
    parser.add_argument('--dataset', type=str, required=True)
    parser.add_argument('--algoritmos', type=str, nargs=2, required=True, help='Dois algoritmos para comparar')
    parser.add_argument('--target_cr', type=float, required=True)
    parser.add_argument('--janela', type=int, required=True)
    parser.add_argument('--metrica', type=str, required=True, help='Métrica para eixo Y (ex: SSIM, MSE, PeakRecall)')
    
    args = parser.parse_args()

    # 2. Carregar dados
    try:
        df_full = pd.read_csv(args.dataset)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        sys.exit(1)

    # Validar métrica
    if args.metrica not in df_full.columns:
        print(f"Métrica '{args.metrica}' não encontrada no dataset.")
        print(f"Colunas disponíveis: {list(df_full.columns)}")
        sys.exit(1)

    # Filtrar dados
    df = df_full[
        (df_full['algoritmo'].isin(args.algoritmos)) &
        (df_full['target_cr'] == args.target_cr) & 
        (df_full['janela'] == args.janela)
    ].copy()

    if df.empty:
        print("Nenhum dado encontrado.")
        sys.exit(0)

    # 3. Estilo
    sns.set_theme(style="white", font_scale=1.1)

    cores = {
        args.algoritmos[0]: '#2c7fb8',
        args.algoritmos[1]: '#d95f0e'
    }

    g = sns.JointGrid(data=df, x='compression_ratio', y=args.metrica, space=0, height=8)

    # --- Scatter por algoritmo ---
    for alg in args.algoritmos:
        subset = df[df['algoritmo'] == alg]

        g.ax_joint.scatter(
            subset['compression_ratio'],
            subset[args.metrica],
            alpha=0.5,
            s=25,
            label=alg,
            color=cores[alg]
        )

        # KDE marginais
        sns.kdeplot(
            x=subset['compression_ratio'],
            ax=g.ax_marg_x,
            fill=True,
            alpha=0.3,
            lw=2,
            color=cores[alg]
        )

        sns.kdeplot(
            y=subset[args.metrica],
            ax=g.ax_marg_y,
            fill=True,
            alpha=0.3,
            lw=2,
            color=cores[alg]
        )

    # Linha target
    g.ax_joint.axvline(args.target_cr, color='black', linestyle='-', linewidth=1.5)
    g.ax_marg_x.axvline(args.target_cr, color='black', linestyle='-', linewidth=1.5)

    # Labels
    g.ax_joint.set_xlabel('Achieved Compression Ratio', fontweight='bold')
    g.ax_joint.set_ylabel(args.metrica, fontweight='bold')

    # Legenda
    g.ax_joint.legend(title="Algoritmo")

    plt.suptitle(
        f"Comparação | Métrica: {args.metrica} | Target CR: {args.target_cr} | Janela: {args.janela}",
        y=1.02,
        fontsize=14,
        fontweight='bold'
    )

    plt.tight_layout()

    # Salvar
    pasta_saida = os.path.join(os.getcwd(), 'views')
    os.makedirs(pasta_saida, exist_ok=True)

    nome_saida = os.path.join(
        pasta_saida,
        f"compare_{args.algoritmos[0]}_{args.algoritmos[1]}_{args.metrica}_cr{args.target_cr}_w{args.janela}.png"
    )

    plt.savefig(nome_saida, dpi=300, bbox_inches='tight')
    print(f"Gráfico salvo: {nome_saida}")


if __name__ == "__main__":
    main()