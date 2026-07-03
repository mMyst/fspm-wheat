import os
import glob
import re
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def plot_leaf1_element_facet_density(base_dir="darwinkel", 
                                     target_file="elements_postprocessing.csv", 
                                     target_column="length",
                                     filter_buffer=0.5,
                                     meteo_file="inputs/Darwinkel_open-meteo_since19101976.csv"):
    """
    Analyse les fichiers 'elements_postprocessing.csv' pour tracer l'évolution 
    d'une variable spécifique (target_column) de la feuille 1 (metamer=1, organ='blade') 
    de chaque talle (axis != 'MS'). Affichage en Facet par Densité avec axe des dates 
    et barres verticales de repère.
    """
    
    search_pattern = os.path.join(base_dir, "**", "postprocessing*")
    post_folders = glob.glob(search_pattern, recursive=True)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé avec le motif : {search_pattern}")
        return

    print(f"📂 Analyse de l'évolution de '{target_column}' (Feuille 1) dans '{target_file}'...")
    
    # --- 1. CHARGEMENT ET CORRESPONDANCE T/DATE DU FICHIER MÉTÉO ---
    meteo_df = None
    if os.path.exists(meteo_file):
        try:
            meteo_df = pd.read_csv(meteo_file, comment='#')
            
            # Détection de la colonne de date (Priorité à 'Date' avec majuscule)
            date_col = None
            if 'Date' in meteo_df.columns:
                date_col = 'Date'
            elif 'date' in meteo_df.columns:
                date_col = 'date'
            else:
                possible_cols = [col for col in meteo_df.columns if 'time' in col.lower() or 'date' in col.lower()]
                if possible_cols:
                    date_col = possible_cols[0]
            
            if 't' in meteo_df.columns and date_col:
                # Convertir en datetime puis formater en jj/mm
                meteo_df['date_formatted'] = pd.to_datetime(meteo_df[date_col]).dt.strftime('%d/%m')
                print(f"📅 Fichier météo chargé. Correspondance t/date active via les colonnes '{date_col}' et 't'.")
            else:
                print(f"⚠️ Les colonnes 't' ou '{date_col}' sont introuvables dans {meteo_file}. Mode fallback activé.")
                meteo_df = None
        except Exception as e:
            print(f"⚠️ Erreur de lecture de {meteo_file} ({e}). Mode fallback activé.")
            meteo_df = None
    else:
        print(f"⚠️ Fichier météo '{meteo_file}' introuvable. Mode fallback activé (calcul théorique).")

    # --- 1bis. CONVERSION DES DATES CIBLES EN 'T' (HEURES) ---
    dates_a_marquer = ["18/02", "07/03", "24/03", "04/04"] # Format normalisé jj/mm
    t_marques = []
    
    if meteo_df is not None:
        for d in dates_a_marquer:
            matches = meteo_df[meteo_df['date_formatted'] == d]
            if not matches.empty:
                # On prend la première heure correspondant à ce jour
                t_marques.append(matches['t'].iloc[0])
    else:
        start_date = pd.to_datetime("1976-10-19")
        for d in dates_a_marquer:
            jour, mois = d.split('/')
            # On assume l'année suivante (1977) vu le semis en octobre
            dt_obj = pd.to_datetime(f"1977-{mois}-{jour}")
            t_val = (dt_obj - start_date).total_seconds() / 3600.0
            t_marques.append(t_val)

    all_dataframes = []

    # --- 2. LECTURE ET EXTRACTION ---
    for folder in sorted(post_folders):
        file_path = os.path.join(folder, target_file)
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            # Vérification de sécurité des colonnes
            expected_cols = ['t', 'axis', 'metamer', 'organ', target_column]
            if not all(col in df.columns for col in expected_cols):
                print(f"⚠️ Colonne '{target_column}' ou colonnes de base introuvables dans {file_path}")
                continue
                
            # Filtrer pour les talles, le metamer 1, et l'organe limbe (blade)
            df_tillers = df[(df['axis'] != 'MS') & (df['metamer'] == 1) & (df['organ'] == 'blade')].copy()
            df_tillers[target_column] = pd.to_numeric(df_tillers[target_column], errors='coerce')
            
            # Nettoyage des valeurs nulles
            df_tillers = df_tillers.dropna(subset=[target_column])
            
            if df_tillers.empty:
                continue
                
            # Nettoyage du nom des axes (ex: "b'T1'" devient "T1")
            df_tillers['axis_clean'] = df_tillers['axis'].str.replace(r"b'|'", "", regex=True)
            
            # Grouper par 't' et 'axis_clean' et sommer la colonne cible 
            df_grouped = df_tillers.groupby(['t', 'axis_clean'])[target_column].sum().reset_index()
            
            # Extraction des paramètres depuis le nom du dossier parent
            match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder)
            
            if match:
                df_grouped['GAIc'] = float(match.group(1))
                df_grouped['Density'] = int(float(match.group(2)))
                df_grouped['Delay'] = float(match.group(3))
                df_grouped['Buffer'] = float(match.group(4))
                all_dataframes.append(df_grouped)
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {file_path} : {e}")

    if not all_dataframes:
        print(f"❌ Aucune donnée valide trouvée pour '{target_column}'.")
        return

    # --- 3. FUSION ET FILTRAGE ---
    master_df = pd.concat(all_dataframes, ignore_index=True)
    master_df_filtered = master_df[master_df['Buffer'] == filter_buffer]
    
    if master_df_filtered.empty:
        print(f"❌ ATTENTION : Aucune donnée ne correspond au Buffer = {filter_buffer}.")
        return
        
    master_df = master_df_filtered
    print(f"✅ Données compilées ({len(master_df)} points). Création du facet plot par densité...")

    # --- 4. CONFIGURATION DE LA GRILLE MATPLOTLIB ---
    unique_density = sorted(master_df['Density'].unique())
    unique_axes = sorted(master_df['axis_clean'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    unique_gaic = sorted(master_df['GAIc'].unique())
    
    # Configuration du Facet (max 3 colonnes)
    n_dens = len(unique_density)
    ncols = min(n_dens, 3) 
    nrows = math.ceil(n_dens / ncols)

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, 
                             figsize=(5 * ncols + 2, 4 * nrows + 1), 
                             sharex=True, sharey=True, squeeze=False, 
                             constrained_layout=True)
    
    axes_flat = axes.flatten()

    # Couleurs par Talle (Axe)
    colors = plt.cm.tab10.colors 
    color_map = {axis: colors[i % len(colors)] for i, axis in enumerate(unique_axes)}
    
    # Styles de ligne par Délai
    line_styles = ['-', '--', ':', '-.']
    delay_style_map = {delay: line_styles[i % len(line_styles)] for i, delay in enumerate(unique_delays)}

    # --- 5. REMPLISSAGE DES GRAPHIQUES ---
    for idx, dens in enumerate(unique_density):
        ax = axes_flat[idx]
        subset_dens = master_df[master_df['Density'] == dens]
        
        for axis_name in unique_axes:
            for delay in unique_delays:
                for gaic in unique_gaic:
                    grp = subset_dens[(subset_dens['axis_clean'] == axis_name) & 
                                      (subset_dens['Delay'] == delay) & 
                                      (subset_dens['GAIc'] == gaic)].sort_values('t')
                    
                    if not grp.empty:
                        ax.plot(grp['t'], grp[target_column], 
                                color=color_map[axis_name], 
                                linestyle=delay_style_map[delay],
                                linewidth=2 if axis_name == 'T1' else 1.5, 
                                alpha=0.85)

        # Ajout des barres verticales pour les dates d'intérêt
        for t_val in t_marques:
            ax.axvline(x=t_val, color='red', linestyle='--', linewidth=1.5, alpha=0.6, zorder=1)

        # Ajustement du titre avec 'pad' pour les dates
        ax.set_title(f"Densité = {dens} pl/m²", fontweight='bold', fontsize=12, pad=35)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Labels d'axes
        if idx >= len(unique_density) - ncols: 
            ax.set_xlabel("Temps (t, heures après semis)", fontsize=10)
        if idx % ncols == 0: 
            ax.set_ylabel(f"{target_column} (Feuille 1)", fontsize=10)

    # Masquer les sous-graphes vides
    for idx in range(n_dens, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    # --- 6. AJOUT DU DEUXIÈME AXE X (DATES) ---
    for i, ax in enumerate(axes_flat):
        if not ax.get_visible():
            continue
            
        ax2 = ax.twiny()
        ax2.set_xlim(ax.get_xlim())
        
        primary_ticks = ax.get_xticks()
        valid_ticks = []
        tick_labels = []
        
        for t in primary_ticks:
            if ax.get_xlim()[0] <= t <= ax.get_xlim()[1]:
                if meteo_df is not None:
                    try:
                        closest_idx = (meteo_df['t'] - t).abs().idxmin()
                        date_str = meteo_df.loc[closest_idx, 'date_formatted']
                        tick_labels.append(date_str)
                        valid_ticks.append(t)
                    except:
                        pass
                else:
                    try:
                        start_date = pd.to_datetime("1976-10-19")
                        date_val = start_date + pd.Timedelta(hours=float(t))
                        tick_labels.append(date_val.strftime('%d/%m'))
                        valid_ticks.append(t)
                    except:
                        pass
                    
        ax2.set_xticks(valid_ticks)
        ax2.set_xticklabels(tick_labels, fontsize=9)
        
        if i < ncols:
            ax2.set_xlabel("Date (jj/mm)", fontsize=10, labelpad=10)

    # --- 7. LÉGENDE GLOBALE ---
    legend_elements = [Line2D([0], [0], color='w', label=r'$\bf{Axe \ (Talle)}$')]
    for axis_name, color in color_map.items():
        legend_elements.append(Line2D([0], [0], color=color, lw=2, label=f'{axis_name}'))
        
    legend_elements.append(Line2D([0], [0], color='w', label='')) 
    
    legend_elements.append(Line2D([0], [0], color='w', label=r'$\bf{Délais \ (Delay)}$'))
    for delay, style in delay_style_map.items():
        legend_elements.append(Line2D([0], [0], color='black', linestyle=style, lw=2, label=f'Delay {delay}'))

    legend_elements.append(Line2D([0], [0], color='w', label=''))
    
    # Ajout du repère pour les barres verticales
    legend_elements.append(Line2D([0], [0], color='w', label=r'$\bf{Repères}$'))
    legend_elements.append(Line2D([0], [0], color='red', linestyle='--', lw=1.5, label='Tiller Obsvervation Dates'))

    fig.legend(handles=legend_elements, loc='outside right center', fontsize=11, frameon=True)
    fig.suptitle(f"Évolution de '{target_column}' (Feuille 1 | Buffer={filter_buffer})", fontsize=15, fontweight='bold')

    safe_col_name = target_column.replace("/", "_").replace("\\", "_").upper()
    output_image = os.path.join(base_dir, f"FACET_DATE_{safe_col_name}_F1_Buffer_{filter_buffer}.png")
    
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"💾 Graphique sauvegardé sous : {output_image}")
    plt.show()


if __name__ == "__main__":
    
    # === PARAMÈTRES À MODIFIER ICI ===
    COLONNE_A_TESTER = "length"  # Remplace par 'PARa', 'green_area', 'length', etc.
    BUFFER_A_TESTER = 0.5 
    # =================================
    
    # Correction apportée : on utilise un slash '/' (ou on préfixe avec r"") pour éviter les erreurs d'échappement sous Windows.
    plot_leaf1_element_facet_density(
        base_dir="darwinkel",
        target_file="elements_postprocessing.csv",
        target_column=COLONNE_A_TESTER,
        filter_buffer=BUFFER_A_TESTER,
        meteo_file="inputs/Darwinkel_open-meteo_since19101976.csv"
    )