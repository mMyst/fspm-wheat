import os
import glob
import re
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def plot_tiller_mstruct_facet_density(base_dir="darwinkel", 
                                      target_file="hiddenzones_outputs.csv", 
                                      colonne_verification="mstruct", 
                                      filter_buffer=0.5,
                                      meteo_file="Darwinkel_open-meteo_since19101976.csv"):
    
    search_pattern = os.path.join(base_dir, "**", "outputs*")
    post_folders = glob.glob(search_pattern, recursive=True)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Analyse de l'évolution de '{colonne_verification}' (metamer 1) dans '{target_file}'...")
    
    # --- 1. CHARGEMENT ET CORRESPONDANCE T/DATE DU FICHIER MÉTÉO ---
    meteo_df = None
    if os.path.exists(meteo_file):
        try:
            # Lecture du fichier en ignorant les commentaires éventuels
            meteo_df = pd.read_csv(meteo_file, comment='#')
            
            # Détection automatique de la colonne date si 'date' n'est pas son nom exact
            date_col = None
            if 'Date' in meteo_df.columns:
                date_col = 'Date'
            else:
                possible_cols = [col for col in meteo_df.columns if 'time' in col or 'Date' in col]
                if possible_cols:
                    date_col = possible_cols[0]
            
            if 't' in meteo_df.columns and date_col:
                # Convertir en datetime puis formater directement en jj/mm pour optimiser la recherche future
                meteo_df['date_formatted'] = pd.to_datetime(meteo_df[date_col]).dt.strftime('%d/%m')
                print(f"📅 Fichier météo chargé ({len(meteo_df)} lignes). Correspondance t/date active via les colonnes '{date_col}' and 't'.")
            else:
                print(f"⚠️ Les colonnes 't' ou de date sont introuvables dans {meteo_file}. Mode fallback activé.")
                meteo_df = None
        except Exception as e:
            print(f"⚠️ Erreur de lecture de {meteo_file} ({e}). Mode fallback activé.")
            meteo_df = None
    else:
        print(f"⚠️ Fichier météo '{meteo_file}' introuvable. Mode fallback activé (calcul théorique basé sur le 19/10/1976).")

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
                
            # Filtrer pour les talles et le metamer 1
            df_tillers = df[(df['axis'] != 'MS') & (df['metamer'] == 1)].copy()
            df_tillers[colonne_verification] = pd.to_numeric(df_tillers[colonne_verification], errors='coerce')
            
            # Suppression des valeurs nulles
            df_tillers = df_tillers.dropna(subset=[colonne_verification])
            
            if df_tillers.empty:
                continue
            
            # Récupérer les paramètres via le nom du dossier
            match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder)
            
            if match:
                df_tillers['GAIc'] = float(match.group(1))
                df_tillers['Density'] = int(float(match.group(2)))
                df_tillers['Delay'] = float(match.group(3))
                df_tillers['Buffer'] = float(match.group(4))
                
                cols_to_keep = ['axis', 't', colonne_verification, 'GAIc', 'Density', 'Delay', 'Buffer']
                all_dataframes.append(df_tillers[cols_to_keep])
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {file_path} : {e}")

    if not all_dataframes:
        print(f"❌ Aucune donnée valide trouvée.")
        return

    master_df = pd.concat(all_dataframes, ignore_index=True)
    master_df_filtered = master_df[master_df['Buffer'] == filter_buffer]
    
    if master_df_filtered.empty:
        print(f"❌ ATTENTION : Aucune donnée ne correspond au Buffer = {filter_buffer}.")
        return
        
    master_df = master_df_filtered
    print(f"✅ Données compilées ({len(master_df)} points). Création du facet plot par densité...")

    # Extraire les valeurs uniques
    unique_density = sorted(master_df['Density'].unique())
    unique_axes = sorted(master_df['axis'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    unique_gaic = sorted(master_df['GAIc'].unique())
    
    # Configuration du Facet Grid (max 3 colonnes)
    n_dens = len(unique_density)
    ncols = min(n_dens, 3) 
    nrows = math.ceil(n_dens / ncols)

    # Création de la figure
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, 
                             figsize=(5 * ncols + 2, 4 * nrows + 1), 
                             sharex=True, sharey=True, squeeze=False, 
                             constrained_layout=True)
    
    axes_flat = axes.flatten()
    
    # Couleurs par Talle (Axe)
    colors = plt.cm.tab10.colors 
    color_map = {axis: colors[i % len(colors)] for i, axis in enumerate(unique_axes)}
    
    # Style de ligne par Délai
    line_styles = ['-', '--', ':', '-.']
    delay_style_map = {delay: line_styles[i % len(line_styles)] for i, delay in enumerate(unique_delays)}

    # Remplissage des sous-graphes
    for idx, dens in enumerate(unique_density):
        ax = axes_flat[idx]
        subset_dens = master_df[master_df['Density'] == dens]
        
        for axis in unique_axes:
            for delay in unique_delays:
                for gaic in unique_gaic:
                    grp = subset_dens[(subset_dens['axis'] == axis) & 
                                      (subset_dens['Delay'] == delay) & 
                                      (subset_dens['GAIc'] == gaic)].sort_values(by='t')
                    
                    if not grp.empty:
                        ax.plot(grp['t'], grp[colonne_verification], 
                                color=color_map[axis], 
                                linestyle=delay_style_map[delay], 
                                linewidth=2, 
                                alpha=0.8)

        # Ajustement du titre avec 'pad' pour laisser la place aux dates au-dessus
        ax.set_title(f"Densité = {dens} pl/m²", fontweight='bold', fontsize=12, pad=35)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Gestion intelligente des labels d'axes globaux
        if idx >= len(unique_density) - ncols: 
            ax.set_xlabel("Temps (t, heures après semis)", fontsize=10)
        if idx % ncols == 0: 
            ax.set_ylabel(f"Valeur de {colonne_verification}", fontsize=10)

    # Masquer les sous-graphes excédentaires
    for idx in range(n_dens, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    # --- 2. AJOUT DU DEUXIÈME AXE X (DATES EN HAUT VIA RECHERCHE DIRECTE) ---
    for i, ax in enumerate(axes_flat):
        if not ax.get_visible():
            continue
            
        # Créer un axe miroir en haut
        ax2 = ax.twiny()
        ax2.set_xlim(ax.get_xlim())
        
        # Récupérer les graduations calculées automatiquement sur l'axe principal (heures)
        primary_ticks = ax.get_xticks()
        valid_ticks = []
        tick_labels = []
        
        for t in primary_ticks:
            # Ne garder que les graduations actuellement visibles dans la zone de zoom du graphique
            if ax.get_xlim()[0] <= t <= ax.get_xlim()[1]:
                if meteo_df is not None:
                    try:
                        # Trouver l'index de la ligne du fichier météo où 't' est le plus proche de la graduation
                        closest_idx = (meteo_df['t'] - t).abs().idxmin()
                        date_str = meteo_df.loc[closest_idx, 'date_formatted']
                        tick_labels.append(date_str)
                        valid_ticks.append(t)
                    except:
                        pass
                else:
                    # Fallback si le fichier météo est inaccessible (calcul théorique en heures sur base du 19/10/1976)
                    try:
                        start_date = pd.to_datetime("1976-10-19")
                        date_val = start_date + pd.Timedelta(hours=float(t))
                        tick_labels.append(date_val.strftime('%d/%m'))
                        valid_ticks.append(t)
                    except:
                        pass
                    
        ax2.set_xticks(valid_ticks)
        ax2.set_xticklabels(tick_labels, fontsize=9)
        
        # Label de l'axe des dates uniquement sur la première ligne pour la clarté visuelle
        if i < ncols:
            ax2.set_xlabel("Date (jj/mm)", fontsize=10, labelpad=10)

    # --- LÉGENDE GLOBALE ---
    legend_elements = [Line2D([0], [0], color='w', label=r'$\bf{Talles \ (Axe)}$')]
    for axis, color in color_map.items():
        legend_elements.append(Line2D([0], [0], color=color, lw=2, label=f'Axe {axis}'))
        
    legend_elements.append(Line2D([0], [0], color='w', label=r'$\bf{Délais \ (Delay)}$'))
    for delay, style in delay_style_map.items():
        legend_elements.append(Line2D([0], [0], color='black', linestyle=style, lw=2, label=f'Delay {delay}'))
        
    fig.legend(handles=legend_elements, loc='outside right center', fontsize=11, frameon=True)
    fig.suptitle(f"Évolution de '{colonne_verification}' (Metamer 1 | Buffer={filter_buffer})", fontsize=15, fontweight='bold')

    output_image = os.path.join(base_dir, f"FACET_DATE_MAPPING_{colonne_verification}_Buffer_{filter_buffer}.png")
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    plt.show()

if __name__ == "__main__":
    COLONNE_A_TESTER = "mstruct"  
    BUFFER_A_TESTER = 0.5 
    
    plot_tiller_mstruct_facet_density(
        base_dir="darwinkel",
        target_file="hiddenzones_outputs.csv",
        colonne_verification=COLONNE_A_TESTER,
        filter_buffer=BUFFER_A_TESTER,
        meteo_file="inputs\Darwinkel_open-meteo_since19101976.csv"
    )