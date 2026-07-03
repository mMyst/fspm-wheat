import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

def plot_tiller_status_evolution(base_dir="darwinkel", 
                                 target_file="axes_outputs.csv", 
                                 filter_buffer=0.5):
    
    search_pattern = os.path.join(base_dir, "**", "outputs*")
    post_folders = glob.glob(search_pattern, recursive=True)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Analyse de l'évolution du 'status' dans '{target_file}'...")
    
    all_dataframes = []
    
    # Les statuts que l'on souhaite suivre (dans l'ordre chronologique)
    target_statuses = ['primordia', 'vegetative', 'reproductive']

    for folder in sorted(post_folders):
        file_path = os.path.join(folder, target_file)
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            # Vérification des colonnes nécessaires
            required_cols = ['axis', 'status', 't']
            if not all(col in df.columns for col in required_cols):
                print(f"⚠️ Colonnes manquantes dans {file_path}")
                continue
                
            # Exclure le Main Stem (MS) si besoin, et filtrer les statuts valides
            df_tillers = df[(df['axis'] != 'MS') & (df['status'].isin(target_statuses))].copy()
            
            if df_tillers.empty:
                continue
                
            # Trouver le t_min pour chaque axe ET chaque statut
            emergence_t = df_tillers.groupby(['axis', 'status'])['t'].min().reset_index()
            emergence_t.rename(columns={'t': 't_min'}, inplace=True)
            
            # Extraction des métadonnées depuis le nom du dossier
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
    print(f"✅ Données compilées ({len(master_df)} événements d'état trouvés). Création des graphiques...")

    unique_gaic = sorted(master_df['GAIc'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    unique_density = sorted(master_df['Density'].unique())
    
    tiller_order = sorted(master_df['axis'].unique())
    tiller_mapping = {talle: idx for idx, talle in enumerate(tiller_order)}

    # Configuration visuelle
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color_map = {val: colors[i % len(colors)] for i, val in enumerate(unique_density)}
    
    # Marqueurs pour différencier les stades
    marker_map = {
        'primordia': 'o',  # Cercle
        'vegetative': 's', # Carré
        'reproductive': '^' # Triangle
    }

    fig, axes = plt.subplots(nrows=len(unique_gaic), ncols=len(unique_delays), 
                             figsize=(14, 8), sharex=True, sharey=True, squeeze=False,
                             constrained_layout=True)

    for row_idx, gaic in enumerate(unique_gaic):
        for col_idx, delay in enumerate(unique_delays):
            ax = axes[row_idx, col_idx]
            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            for dens_idx, dens in enumerate(unique_density):
                grp_dens = subset[subset['Density'] == dens]
                if grp_dens.empty: continue
                
                # Pour chaque axe dans cette densité, on trace l'évolution
                for axis in tiller_order:
                    grp_axis = grp_dens[grp_dens['axis'] == axis].sort_values(
                        by='status', 
                        key=lambda x: x.map({k: i for i, k in enumerate(target_statuses)})
                    )
                    
                    if grp_axis.empty: continue
                    
                    x_pos = tiller_mapping[axis]
                    # Décalage léger sur l'axe X pour ne pas superposer les densités
                    offset = (dens_idx - (len(unique_density) - 1) / 2) * 0.15 
                    x_vals = [x_pos + offset] * len(grp_axis)
                    y_vals = grp_axis['t_min'].values
                    statuses = grp_axis['status'].values
                    
                    # Tracer une ligne reliant les stades pour un même axe
                    ax.plot(x_vals, y_vals, color=color_map[dens], alpha=0.4, linestyle='-', linewidth=1.5)
                    
                    # Tracer les points selon leur stade
                    for x, y, status in zip(x_vals, y_vals, statuses):
                        ax.scatter(x, y, color=color_map[dens], marker=marker_map[status], 
                                   edgecolor='black', s=50, zorder=3, alpha=0.85)

            ax.set_title(f"GAIc = {gaic} | Delay = {delay}", fontweight='bold', fontsize=11)
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            
            ax.set_xticks(range(len(tiller_order)))
            ax.set_xticklabels(tiller_order)
            
            if row_idx == len(unique_gaic) - 1: ax.set_xlabel("Talle (axe)", fontsize=10)
            if col_idx == 0: ax.set_ylabel("Temps (t)", fontsize=10)

    # --- LÉGENDES ---
    legend_elements = [Line2D([0], [0], color='w', label=r'$\bf{Densité \ (pl/m^2)}$')]
    for dens, color in color_map.items():
        legend_elements.append(Patch(facecolor=color, edgecolor='black', label=f'{dens}'))
        
    legend_elements.append(Line2D([0], [0], color='w', label='')) # Espace
    legend_elements.append(Line2D([0], [0], color='w', label=r'$\bf{Stade \ (Status)}$'))
    
    for status, marker in marker_map.items():
        legend_elements.append(Line2D([0], [0], marker=marker, color='w', markerfacecolor='gray', 
                                      markeredgecolor='black', markersize=8, label=status.capitalize()))
        
    fig.legend(handles=legend_elements, loc='outside right center', fontsize=11, frameon=True)
    fig.suptitle(f"Évolution des stades par axe (Buffer={filter_buffer})", fontsize=16, fontweight='bold')

    output_image = os.path.join(base_dir, f"EVOLUTION_STATUS_Buffer_{filter_buffer}.png")
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    plt.show()

if __name__ == "__main__":
    BUFFER_A_TESTER = 0.5 
    
    plot_tiller_status_evolution(
        base_dir="darwinkel",
        target_file="axes_outputs.csv",
        filter_buffer=BUFFER_A_TESTER
    )