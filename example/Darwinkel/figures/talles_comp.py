import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

def plot_tiller_emergence_bars(base_dir="darwinkel", 
                               target_file="hiddenzones_outputs.csv", 
                               colonne_verification="leaf_is_growing", 
                               filter_buffer=0.5):
    
    search_pattern = os.path.join(base_dir, "**", "outputs*")
    post_folders = glob.glob(search_pattern, recursive=True)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Analyse de l'apparition du metamer 1 (via '{colonne_verification}' == True) dans '{target_file}'...")
    
    all_dataframes = []

    for folder in sorted(post_folders):
        file_path = os.path.join(folder, target_file)
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            if 'axis' not in df.columns or 'metamer' not in df.columns or 't' not in df.columns:
                continue
            if colonne_verification not in df.columns:
                print(f"⚠️ Colonne '{colonne_verification}' introuvable dans {file_path}")
                continue
                
            df_tillers = df[(df['axis'] != 'MS') & (df['metamer'] == 1)].copy()
            
            is_true_mask = df_tillers[colonne_verification].astype(str).str.strip().str.lower() == 'true'
            df_tillers_valid = df_tillers[is_true_mask]
            
            if df_tillers_valid.empty:
                continue
                
            emergence_t = df_tillers_valid.groupby('axis')['t'].min().reset_index()
            emergence_t.rename(columns={'t': 't_min'}, inplace=True)
            
            match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder)
            
            if match:
                emergence_t['GAIc'] = float(match.group(1))
                emergence_t['Density'] = int(float(match.group(2)))
                emergence_t['Delay'] = float(match.group(3))
                emergence_t['Buffer'] = float(match.group(4))
                all_dataframes.append(emergence_t)
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {file_path} : {e}")

    if not all_dataframes:
        print(f"❌ Aucune donnée valide trouvée. Le dataframe final est vide.")
        return

    master_df = pd.concat(all_dataframes, ignore_index=True)
    master_df_filtered = master_df[master_df['Buffer'] == filter_buffer]
    
    if master_df_filtered.empty:
        print(f"❌ ATTENTION : Aucune donnée ne correspond au Buffer = {filter_buffer}.")
        return
        
    master_df = master_df_filtered
    print(f"✅ Données compilées ({len(master_df)} événements trouvés). Création des barplots...")

    unique_gaic = sorted(master_df['GAIc'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    unique_density = sorted(master_df['Density'].unique())
    n_densities = len(unique_density)
    
    tiller_order = sorted(master_df['axis'].unique())
    tiller_mapping = {talle: idx for idx, talle in enumerate(tiller_order)}

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color_map = {val: colors[i % len(colors)] for i, val in enumerate(unique_density)}
    bar_width = 0.8 / max(1, n_densities)

    # Création de la figure avec constrained_layout=True
    fig, axes = plt.subplots(nrows=len(unique_gaic), ncols=len(unique_delays), 
                             figsize=(12, 7), sharex=True, sharey=True, squeeze=False,
                             constrained_layout=True)

    for row_idx, gaic in enumerate(unique_gaic):
        for col_idx, delay in enumerate(unique_delays):
            ax = axes[row_idx, col_idx]
            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            for dens_idx, dens in enumerate(unique_density):
                grp = subset[subset['Density'] == dens].sort_values(by='axis')
                if grp.empty: continue
                
                x_base = np.array([tiller_mapping[talle] for talle in grp['axis']])
                offset = (dens_idx - (n_densities - 1) / 2) * bar_width
                
                ax.bar(x_base + offset, grp['t_min'], width=bar_width, 
                       color=color_map[dens], alpha=0.85, edgecolor='white', linewidth=1)

            ax.set_title(f"GAIc = {gaic} | Delay = {delay}", fontweight='bold', fontsize=11)
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            
            ax.set_xticks(range(len(tiller_order)))
            ax.set_xticklabels(tiller_order)
            
            if row_idx == len(unique_gaic) - 1: ax.set_xlabel("Talle (axe)", fontsize=10)
            if col_idx == 0: ax.set_ylabel("Temps d'apparition (t)", fontsize=10)

    # --- LE NOUVEAU CORRECTIF EST ICI ---
    legend_elements = [Line2D([0], [0], color='w', label=r'$\bf{Densité \ (pl/m^2)}$')]
    for dens, color in color_map.items():
        legend_elements.append(Patch(facecolor=color, edgecolor='black', label=f'{dens}'))
        
    # L'argument loc='outside right center'
    fig.legend(handles=legend_elements, loc='outside right center', fontsize=11, frameon=True)
    fig.suptitle(f"Émergence : t min où '{colonne_verification}' == True (Buffer={filter_buffer})", fontsize=16, fontweight='bold')

    output_image = os.path.join(base_dir, f"EMERGENCE_BARPLOT_{colonne_verification}_Buffer_{filter_buffer}.png")
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    plt.show()

if __name__ == "__main__":
    COLONNE_A_TESTER = "leaf_is_growing"  
    BUFFER_A_TESTER = 0.5 
    
    plot_tiller_emergence_bars(
        base_dir="darwinkel",
        target_file="hiddenzones_outputs.csv",
        colonne_verification=COLONNE_A_TESTER,
        filter_buffer=BUFFER_A_TESTER
    )

#ne fonctionne pas en l'état : on passe 1 fois dans elongwheat avant d'éteindre le talle, donc la feuille est mise en "is growing"
    