import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def plot_custom_grid_mpl(base_dir="parallel_tests", 
                         target_file="axes_postprocessing.csv", 
                         target_column="sum_dry_mass_shoot", 
                         x_axis="t",
                         filter_axis="MS", 
                         filter_plant=1):
    """
    Crée une matrice de graphiques (Lignes = GAIc, Colonnes = Delay),
    filtre sur Buffer = 0.1, et colore les courbes par Densité.
    """
    
    search_pattern = os.path.join(base_dir, "postprocessing_*")
    post_folders = glob.glob(search_pattern)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Compilation des données pour '{target_column}' depuis '{target_file}'...")
    
    all_dataframes = []

    # 1. LECTURE ET EXTRACTION DES FACTEURS
    for folder in sorted(post_folders):
        file_path = os.path.join(folder, target_file)
        
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            if 'plant' in df.columns and filter_plant is not None:
                df = df[df['plant'] == filter_plant]
            if 'axis' in df.columns and filter_axis is not None:
                df = df[df['axis'] == filter_axis]
            
            if x_axis not in df.columns or target_column not in df.columns:
                continue
                
            folder_name = os.path.basename(folder)
            match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder_name)
            
            if match:
                df['GAIc'] = float(match.group(1))
                df['Density'] = int(float(match.group(2)))
                df['Delay'] = float(match.group(3))
                df['Buffer'] = float(match.group(4))
            else:
                continue

            df_subset = df[[x_axis, target_column, 'GAIc', 'Density', 'Delay', 'Buffer']].copy()
            all_dataframes.append(df_subset)
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {file_path} : {e}")

    if not all_dataframes:
        print("❌ Aucune donnée valide n'a pu être compilée.")
        return

    # 2. FUSION ET FILTRAGE (On ne garde que Buffer == 0.1)
    master_df = pd.concat(all_dataframes, ignore_index=True)
    
    master_df = master_df[master_df['Buffer'] == 1]
    
    if master_df.empty:
        print("❌ Aucune donnée restante après avoir filtré sur Buffer = 0.1.")
        return
        
    print(f"✅ Données compilées ({len(master_df)} lignes pour Buffer=0.1). Création de la grille...")

    # 3. IDENTIFICATION DES AXES DE LA GRILLE
    unique_gaic = sorted(master_df['GAIc'].unique())       # Lignes
    unique_delays = sorted(master_df['Delay'].unique())    # Colonnes
    unique_density = sorted(master_df['Density'].unique()) # Couleurs

    # Palette de couleurs distinctes pour les densités
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color_map = {val: colors[i % len(colors)] for i, val in enumerate(unique_density)}

    # 4. CRÉATION DE LA GRILLE MATPLOTLIB
    fig, axes = plt.subplots(nrows=len(unique_gaic), ncols=len(unique_delays), 
                             figsize=(6 * len(unique_delays), 4.5 * len(unique_gaic)), 
                             sharex=True, sharey=True, squeeze=False)

    # 5. REMPLISSAGE DES GRAPHIQUES
    for row_idx, gaic in enumerate(unique_gaic):
        for col_idx, delay in enumerate(unique_delays):
            ax = axes[row_idx, col_idx]
            
            # Sous-ensemble pour la case actuelle de la matrice
            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            # Traçage : on groupe uniquement par Densité puisqu'elle définit la couleur
            for dens, grp in subset.groupby('Density'):
                grp = grp.sort_values(by=x_axis)
                
                ax.plot(grp[x_axis], grp[target_column], 
                        color=color_map[dens], 
                        linewidth=2.5,
                        alpha=0.85)

            # Titres de la case
            ax.set_title(f"GAIc = {gaic} | Delay = {delay}", fontweight='bold', fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.6)
            
            # Étiquettes uniquement sur les bords extérieurs
            if row_idx == len(unique_gaic) - 1:
                ax.set_xlabel(f"Temps ({x_axis})", fontsize=10)
            if col_idx == 0:
                ax.set_ylabel(target_column, fontsize=10)

# 6. CRÉATION DE LA LÉGENDE PERSONNALISÉE (Pour la Densité)
    legend_elements = [Line2D([0], [0], color='w', label=r'$\bf{Densité \ (pl/m^2)}$')]
    for dens, color in color_map.items():
        legend_elements.append(Line2D([0], [0], color=color, lw=3, label=f'{dens}'))
        

    # 1. On force les graphiques à s'arrêter à 82% de la largeur de l'image
    #    et à 90% de la hauteur (pour laisser la place au titre en haut)
    fig.subplots_adjust(top=0.90, right=0.82)
    
    # 2. On place la légende dans cet espace vide (à 84% de la largeur de la figure)
    fig.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(0.84, 0.5), fontsize=11, frameon=True)

    # Titre global
    fig.suptitle(f"Évolution de '{target_column}' (Buffer = 0.1)", fontsize=16, fontweight='bold')
    
    # Sauvegarde classique (sans bbox_inches qui cause les coupures)
    output_image = os.path.join(base_dir, f"GRILLE_GAIc_Delay_{target_column}.png")
    plt.savefig(output_image, dpi=300)
    
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    
    plt.show()

if __name__ == "__main__":
    
    FICHIER_CIBLE = "axes_postprocessing.csv"  
    COLONNE_CIBLE = "sum_dry_mass_shoot"       #"Total_Photosynthesis"#
    AXE_X = "t"                                
    
    plot_custom_grid_mpl(
        base_dir="parallel_tests",
        target_file=FICHIER_CIBLE,
        target_column=COLONNE_CIBLE,
        x_axis=AXE_X
    )