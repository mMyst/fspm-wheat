import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt

def plot_green_area_with_axis_emergence(base_dir="parallel_tests", 
                                        elem_file="elements_outputs.csv", 
                                        hiddenzones_file="hiddenzones_outputs.csv",
                                        filter_buffer=1):
    """
    Trace l'évolution de 'green_area' (depuis elements_outputs) et ajoute 
    des lignes verticales pour l'apparition de chaque axe secondaire en 
    cherchant t min où mstruct > 0 (depuis hiddenzones_outputs).
    """
    
    search_pattern = os.path.join(base_dir, "outputs_*")
    post_folders = glob.glob(search_pattern)
    
    if not post_folders:
        print(f"❌ Aucun dossier trouvé : {search_pattern}")
        return

    all_data = []

    for folder in sorted(post_folders):
        folder_name = os.path.basename(folder)
        match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder_name)
        
        if not match: continue
        
        gaic, density, delay, buf = float(match.group(1)), int(float(match.group(2))), float(match.group(3)), float(match.group(4))
        if buf != filter_buffer: continue

        path_elem = os.path.join(folder, elem_file)
        path_hz = os.path.join(folder, hiddenzones_file)

        if os.path.exists(path_elem) and os.path.exists(path_hz):
            try:
                # 1. Somme de green_area par pas de temps (t)
                df_elem = pd.read_csv(path_elem)
                df_summed = df_elem.groupby('t')['green_area'].sum().reset_index()

                # 2. Identification de l'apparition de CHAQUE axe secondaire via mstruct
                df_hz = pd.read_csv(path_hz)
                
                if 'axis' in df_hz.columns and 'mstruct' in df_hz.columns:
                    # Filtre : Axes non-MS ET masse structurelle non nulle (> 0)
                    non_ms_active = df_hz[(df_hz['axis'] != 'MS') & (df_hz['mstruct'] > 0) & (df_hz['metamer'] == 1)]
                    t_emergences = non_ms_active.groupby('axis')['t'].min().tolist() if not non_ms_active.empty else []
                else:
                    print(f"⚠️ Colonne 'axis' ou 'mstruct' introuvable dans {folder_name}/{hiddenzones_file}")
                    t_emergences = []

                all_data.append({
                    'GAIc': gaic, 'Density': density, 'Delay': delay,
                    't_emergences': t_emergences, 'data': df_summed
                })
            except Exception as e:
                print(f"⚠️ Erreur dans {folder_name}: {e}")

    # --- Configuration de la Grille ---
    if not all_data:
        print("❌ Aucune donnée valide n'a pu être extraite.")
        return

    master_df = pd.DataFrame(all_data)
    unique_gaic = sorted(master_df['GAIc'].unique())
    unique_delays = sorted(master_df['Delay'].unique())
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    color_map = {d: colors[i % len(colors)] for i, d in enumerate(sorted(master_df['Density'].unique()))}

    fig, axes = plt.subplots(len(unique_gaic), len(unique_delays), 
                             figsize=(15, 10), sharex=True, sharey=True, squeeze=False)

    for r, gaic in enumerate(unique_gaic):
        for c, delay in enumerate(unique_delays):
            ax = axes[r, c]
            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            for _, row in subset.iterrows():
                # Courbe de surface verte
                line, = ax.plot(row['data']['t'], row['data']['green_area'], 
                                color=color_map[row['Density']], label=f"Dens: {row['Density']}")
                
                # Ligne verticale pour l'apparition de CHAQUE axe
                for t_emerg in row['t_emergences']:
                    ax.axvline(x=t_emerg, color=line.get_color(), 
                               linestyle='--', alpha=0.6, linewidth=1.2)

            ax.set_title(f"GAIc {gaic} | Delay {delay}")
            if r == len(unique_gaic)-1: ax.set_xlabel("Temps (t)")
            if c == 0: ax.set_ylabel("Somme Green Area")
            
            # Afficher la légende uniquement s'il y a des tracés
            if not subset.empty:
                handles, labels = ax.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                ax.legend(by_label.values(), by_label.keys())

    plt.tight_layout()
    plt.savefig("green_area_with_emergence.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    plot_green_area_with_axis_emergence()