import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import sys

def main():
    # 1. Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description='Visualiza resultados de compressão (Ondas KDE).')
    parser.add_argument('--dataset', type=str, required=True, help='Caminho para o arquivo CSV')
    parser.add_argument('--algoritmo', type=str, required=True, help='Nome do algoritmo para filtrar')
    parser.add_argument('--target_cr', type=float, required=True, help='Target Compression Ratio (ex: 0.8)')
    parser.add_argument('--janela', type=int, required=True, help='Tamanho da janela para filtrar')
    
    args = parser.parse_args()

    # 2. Carregar e Filtrar os Dados
    try:
        df_full = pd.read_csv(args.dataset)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        sys.exit(1)

    # Filtragem rigorosa conforme solicitado
    df = df_full[
        (df_full['algoritmo'] == args.algoritmo) & 
        (df_full['target_cr'] == args.target_cr) & 
        (df_full['janela'] == args.janela)
    ].copy()

    if df.empty:
        print(f"Aviso: Nenhum dado encontrado para Algoritmo={args.algoritmo}, Target={args.target_cr}, Janela={args.janela}")
        sys.exit(0)

    # 3. Configuração Estética (Publicação Acadêmica)
    sns.set_theme(style="white", font_scale=1.1)
    
    # Criar o JointGrid (Eixo X: compression_ratio, Eixo Y: SSIM)
    g = sns.JointGrid(data=df, x='compression_ratio', y='SSIM', space=0, height=8)

    # --- Centro: Dispersão com transparência ---
    g.plot_joint(sns.scatterplot, alpha=0.5, color='#2c7fb8', edgecolor='none', s=25)
    
    # Linha de tendência para mostrar o trade-off
    sns.regplot(data=df, x='compression_ratio', y='SSIM', ax=g.ax_joint, 
                scatter=False, color='#e6550d', line_kws={'lw': 2, 'linestyle': '--'})

    # --- Marginais: As "Ondas" (KDE) ---
    g.plot_marginals(sns.kdeplot, fill=True, color='#2c7fb8', alpha=0.3, lw=2)

    # 4. Anotações e Linhas de Referência
    # Linha vertical indicando o Target CR real nos dados
    g.ax_joint.axvline(args.target_cr, color='#e6550d', linestyle='-', linewidth=1.5, label=f'Target ({args.target_cr})')
    g.ax_marg_x.axvline(args.target_cr, color='#e6550d', linestyle='-', linewidth=1.5)

    # Títulos e Labels
    g.ax_joint.set_xlabel('Achieved Compression Ratio', fontweight='bold')
    g.ax_joint.set_ylabel('SSIM (Quality Metric)', fontweight='bold')
    
    # Título superior com os parâmetros do filtro
    plt.suptitle(f"Algoritmo: {args.algoritmo} | Target CR: {args.target_cr} | Janela: {args.janela}", 
                 y=1.02, fontsize=14, fontweight='bold')

    plt.tight_layout()
    
    # Salvar automaticamente com nome sugestivo
    import os
    pasta_saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'views')
    os.makedirs(pasta_saida, exist_ok=True)
    nome_saida = os.path.join(pasta_saida, f"plot_{args.algoritmo}_cr{args.target_cr}_w{args.janela}.png")
    plt.savefig(nome_saida, dpi=300, bbox_inches='tight')
    print(f"Gráfico salvo com sucesso: {nome_saida}")

    plt.show()

if __name__ == "__main__":
    main()