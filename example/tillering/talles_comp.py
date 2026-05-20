import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

def plot_tiller_emergence_bars(base_dir="parallel_tests", 
                               target_file="hiddenzones_postprocessing.csv", 
                               colonne_verification="mstruct", 
                               filter_buffer=1):
    """
    Extrait le t minimum où le metamer 1 devient NUMÉRIQUE et > 0 pour chaque talle.
    Crée une grille Lignes=GAIc, Colonnes=Delay, avec un diagramme en barres groupées par Densité.
    """
    
    search_pattern = os.path.join(base_dir, "outputs_*")
    post_folders = glob.glob(search_pattern)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Analyse de l'apparition du metamer 1 (via '{colonne_verification}' > 0) dans '{target_file}'...")
    
    all_dataframes = []

    # 1. LECTURE ET EXTRACTION
    for folder in sorted(post_folders):
        file_path = os.path.join(folder, target_file)
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            if 'axis' not in df.columns or 'metamer' not in df.columns or 't' not in df.columns:
                continue
            if colonne_verification not in df.columns:
                continue
                
            df_tillers = df[(df['axis'] != 'MS') & (df['metamer'] == 1)].copy()
            df_tillers[colonne_verification] = pd.to_numeric(df_tillers[colonne_verification], errors='coerce')
            df_tillers_valid = df_tillers[df_tillers[colonne_verification] > 0]
            
            if df_tillers_valid.empty:
                continue
                
            emergence_t = df_tillers_valid.groupby('axis')['t'].min().reset_index()
            emergence_t.rename(columns={'t': 't_min'}, inplace=True)
            
            folder_name = os.path.basename(folder)
            match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder_name)
            
            if match:
                emergence_t['GAIc'] = float(match.group(1))
                emergence_t['Density'] = int(float(match.group(2)))
                emergence_t['Delay'] = float(match.group(3))
                emergence_t['Buffer'] = float(match.group(4))
            else:
                continue

            all_dataframes.append(emergence_t)
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {file_path} : {e}")

    if not all_dataframes:
        print(f"❌ Aucune donnée valide. Vérifiez que la colonne {colonne_verification} dépasse bien 0.")
        return

    # 2. FUSION ET FILTRAGE
    master_df = pd.concat(all_dataframes, ignore_index=True)
    master_df = master_df[master_df['Buffer'] == filter_buffer]
    
    if master_df.empty:
        print(f"❌ Aucune donnée restante après avoir filtré sur Buffer = {filter_buffer}.")
        return
        
    print(f"✅ Données compilées ({len(master_df)} événements trouvés). Création des barplots...")

    # 3. IDENTIFICATION DES AXES ET CATÉGORIES
    unique_gaic = sorted(master_df['GAIc'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    unique_density = sorted(master_df['Density'].unique())
    n_densities = len(unique_density)
    
    tiller_order = sorted(master_df['axis'].unique())
    tiller_mapping = {talle: idx for idx, talle in enumerate(tiller_order)}

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color_map = {val: colors[i % len(colors)] for i, val in enumerate(unique_density)}

    # Calcul de la largeur des barres pour qu'elles tiennent toutes dans un espace de "0.8" autour du tick central
    bar_width = 0.8 / n_densities

    # 4. CRÉATION DE LA GRILLE MATPLOTLIB
    fig, axes = plt.subplots(nrows=len(unique_gaic), ncols=len(unique_delays), 
                             figsize=(6 * len(unique_delays), 4.5 * len(unique_gaic)), 
                             sharex=True, sharey=True, squeeze=True)

    # 5. REMPLISSAGE DES GRAPHIQUES (BARRES GROUPÉES)
    for row_idx, gaic in enumerate(unique_gaic):
        for col_idx, delay in enumerate(unique_delays):
            ax = axes[row_idx, col_idx]
            
            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            # On boucle sur chaque densité pour créer son set de barres avec le bon décalage
            for dens_idx, dens in enumerate(unique_density):
                grp = subset[subset['Density'] == dens].sort_values(by='axis')
                
                if grp.empty:
                    continue
                
                # Récupération des positions X de base pour les talles présentes
                x_base = np.array([tiller_mapping[talle] for talle in grp['axis']])
                
                # Calcul de l'offset pour cette densité spécifique
                # Centre les barres autour de la position de la talle
                offset = (dens_idx - (n_densities - 1) / 2) * bar_width
                
                ax.bar(x_base + offset, grp['t_min'], 
                       width=bar_width, 
                       color=color_map[dens], 
                       alpha=0.85,
                       edgecolor='white', # Petite bordure pour bien séparer les barres
                       linewidth=1)

            ax.set_title(f"GAIc = {gaic} | Delay = {delay}", fontweight='bold', fontsize=11)
            ax.grid(True, axis='y', linestyle='--', alpha=0.6) # Grille uniquement horizontale pour les barplots
            
            # Étiquettes X : au centre des groupes de barres
            ax.set_xticks(range(len(tiller_order)))
            ax.set_xticklabels(tiller_order)
            
            if row_idx == len(unique_gaic) - 1:
                ax.set_xlabel("Talle (axe)", fontsize=10)
            if col_idx == 0:
                ax.set_ylabel("Temps d'apparition (t)", fontsize=10)

    # 6. LÉGENDE (Mise à jour pour des rectangles colorés)
    legend_elements = [Line2D([0], [0], color='w', label=r'$\bf{Densité \ (pl/m^2)}$')]
    for dens, color in color_map.items():
        # Utilisation de Patch pour dessiner un rectangle dans la légende
        legend_elements.append(Patch(facecolor=color, edgecolor='black', label=f'{dens}'))
        
    fig.subplots_adjust(top=0.90, right=0.82)
    fig.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(0.84, 0.5), fontsize=11, frameon=True)

    fig.suptitle(f"Émergence : t min où '{colonne_verification}' > 0 (Buffer={filter_buffer})", fontsize=16, fontweight='bold', y=0.97)

    output_image = os.path.join(base_dir, f"EMERGENCE_BARPLOT_{colonne_verification}_Buffer_{filter_buffer}.png")
    plt.savefig(output_image, dpi=300)
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    
    plt.show()

if __name__ == "__main__":
    
    COLONNE_A_TESTER = "mstruct"  
    BUFFER_A_TESTER = 1
    
    plot_tiller_emergence_bars(
        base_dir="parallel_tests",
        target_file="hiddenzones_outputs.csv",
        colonne_verification=COLONNE_A_TESTER,
        filter_buffer=BUFFER_A_TESTER
    )