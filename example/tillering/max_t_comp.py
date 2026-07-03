import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def plot_max_time_bars(base_dir="parallel_tests", 
                       target_file="axes_postprocessing.csv", 
                       filter_buffer=1):
    """
    Parses multiple parallel simulation output folders to extract the maximum 
    simulated time ('t_max') reached before termination. Generates a grid of 
    bar plots visualizing simulation survival duration grouped by density, 
    GAIc, and delay parameters.
    """
    
    search_pattern = os.path.join(base_dir, "postprocessing_*")
    post_folders = glob.glob(search_pattern)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Analyse du temps maximum 't_max' atteint dans '{target_file}'...")
    
    all_data = []

    # 1. LECTURE ET EXTRACTION DU t_max
    for folder in sorted(post_folders):
        file_path = os.path.join(folder, target_file)
        
        if not os.path.exists(file_path):
            continue
            
        try:
            # On ne lit que la colonne 't' pour gagner de la mémoire et de la vitesse
            df = pd.read_csv(file_path, usecols=['t'])
            
            if df.empty:
                continue
                
            t_max = df['t'].max()
            
            # --- Extraction des facteurs via Regex ---
            folder_name = os.path.basename(folder)
            match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder_name)
            
            if match:
                gaic = float(match.group(1))
                density = int(float(match.group(2)))
                delay = float(match.group(3))
                buffer_val = float(match.group(4))
                
                all_data.append({
                    'GAIc': gaic,
                    'Density': density,
                    'Delay': delay,
                    'Buffer': buffer_val,
                    't_max': t_max
                })
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {file_path} : {e}")

    if not all_data:
        print("❌ Aucune donnée n'a pu être compilée.")
        return

    # 2. CONVERSION EN DATAFRAME ET FILTRAGE
    master_df = pd.DataFrame(all_data)
    master_df = master_df[master_df['Buffer'] == filter_buffer]
    
    if master_df.empty:
        print(f"❌ Aucune donnée restante après avoir filtré sur Buffer = {filter_buffer}.")
        return
        
    print(f"✅ Données compilées ({len(master_df)} simulations analysées). Création de la grille...")

    # 3. IDENTIFICATION DES AXES
    unique_gaic = sorted(master_df['GAIc'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    unique_density = sorted(master_df['Density'].unique())

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color_map = {val: colors[i % len(colors)] for i, val in enumerate(unique_density)}

    # 4. CRÉATION DE LA GRILLE MATPLOTLIB
    fig, axes = plt.subplots(nrows=len(unique_gaic), ncols=len(unique_delays), 
                             figsize=(5 * len(unique_delays), 4 * len(unique_gaic)), 
                             sharex=True, sharey=True, squeeze=False)

    # 5. REMPLISSAGE DES GRAPHIQUES
    for row_idx, gaic in enumerate(unique_gaic):
        for col_idx, delay in enumerate(unique_delays):
            ax = axes[row_idx, col_idx]
            
            # Récupérer les données de la case
            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            # S'assurer que c'est trié par densité pour l'axe X
            subset = subset.sort_values(by='Density')
            
            if subset.empty:
                continue

            # Création des positions X (0, 1, 2...)
            x_pos = np.arange(len(subset))
            
            # Couleurs correspondantes aux densités présentes
            bar_colors = [color_map[d] for d in subset['Density']]

            # Tracer les barres
            bars = ax.bar(x_pos, subset['t_max'], 
                          color=bar_colors, 
                          edgecolor='black', 
                          linewidth=1,
                          alpha=0.85)

            # Ajouter la valeur numérique au-dessus de chaque barre pour une lecture rapide
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points au-dessus de la barre
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

            ax.set_title(f"GAIc = {gaic} | Delay = {delay}", fontweight='bold', fontsize=11)
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            
            # Placement des étiquettes X (les densités)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(subset['Density'])
            
            if row_idx == len(unique_gaic) - 1:
                ax.set_xlabel(r"Densité (pl/m$^2$)", fontsize=11, fontweight='bold')
            if col_idx == 0:
                ax.set_ylabel("Valeur max de t (heures)", fontsize=11, fontweight='bold')
                
            # Limite Y fixe à un peu plus que 4000 pour que toutes les barres respirent
            ax.set_ylim(0, 4500)

    # 6. MISE EN PAGE FINALE
    fig.suptitle(f"Survie de la simulation : Valeur maximale de 't' (Buffer = {filter_buffer})", 
                 fontsize=16, fontweight='bold', y=0.98)

    fig.tight_layout()
    # On ajuste un peu le top pour le suptitle après le tight_layout
    fig.subplots_adjust(top=0.92)

    # Sauvegarde
    output_image = os.path.join(base_dir, f"T_MAX_SURVIE_Buffer_{filter_buffer}.png")
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    
    plt.show()

if __name__ == "__main__":
    
    # Le fichier "axes_postprocessing.csv" est parfait car il contient 
    # toujours les pas de temps généraux de la simulation.
    FICHIER_CIBLE = "axes_postprocessing.csv"  
    BUFFER_A_TESTER = 1
    
    plot_max_time_bars(
        base_dir="parallel_tests",
        target_file=FICHIER_CIBLE,
        filter_buffer=BUFFER_A_TESTER
    )