import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt

def plot_green_area_and_leaves(base_dir="parallel_tests", 
                               elem_file="elements_postprocessing.csv", 
                               axes_file="axes_postprocessing.csv",
                               filter_buffer=0.5):
    """
    Visualizes the temporal evolution of the Green Area Index (GAI) and overlays 
    leaf appearance events. Draws continuous GAI curves and adds vertical dashed lines 
    and annotations whenever the total number of leaves increases in the simulation.
    """
    
    search_pattern = os.path.join(base_dir, "postprocessing_*")
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
        path_axes = os.path.join(folder, axes_file)

        if os.path.exists(path_elem) and os.path.exists(path_axes):
            try:
                df_elem = pd.read_csv(path_elem)
                df_sum_elem = df_elem.groupby('t')['green_area'].sum().reset_index()
                df_sum_elem['gai'] = df_sum_elem['green_area'] * density

                df_axes = pd.read_csv(path_axes)
                df_sum_axes = df_axes.groupby('t')['nb_leaves'].sum().reset_index().sort_values('t')
                
                # Identification des intervalles de nombre de feuilles
                change_mask = df_sum_axes['nb_leaves'].diff() != 0
                change_mask.iloc[0] = True
                df_changes = df_sum_axes[change_mask].copy()
                t_max = df_sum_axes['t'].max()
                intervals = []
                for i in range(len(df_changes)):
                    t_start, val = df_changes.iloc[i]['t'], df_changes.iloc[i]['nb_leaves']
                    t_end = df_changes.iloc[i+1]['t'] if i+1 < len(df_changes) else t_max
                    if t_end > t_start:
                        intervals.append({'start': t_start, 'end': t_end, 'val': val})

                all_data.append({'GAIc': gaic, 'Density': density, 'Delay': delay,
                                 'elem_data': df_sum_elem, 'intervals': intervals})
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
                             figsize=(16, 12), sharex=True, sharey=True, squeeze=False)

    unique_densities = sorted(master_df['Density'].unique())

    for r, gaic in enumerate(unique_gaic):
        for c, delay in enumerate(unique_delays):
            ax = axes[r, c]

            # Ligne horizontale pour le seuil GAIc
            ax.axhline(y=gaic, color='black', linestyle=':', linewidth=1.2, alpha=0.6,
                       label="GAIc Threshold" if (r == 0 and c == 0) else "")

            subset = master_df[(master_df['GAIc'] == gaic) & (master_df['Delay'] == delay)]
            
            for _, row in subset.iterrows():
                density = row['Density']
                color = color_map[density]
                # Courbe GAI (ligne pleine)
                ax.plot(row['elem_data']['t'], row['elem_data']['gai'], 
                        color=color, label=f"{density}")
                
                # Apparition des feuilles (lignes et texte)
                y_text = 0.98 - (unique_densities.index(density) * 0.035)
                for inter in row['intervals']:
                # Always draw vertical lines for leaf appearance
                    if inter['start'] > row['elem_data']['t'].min():
                        ax.axvline(x=inter['start'], color=color, linestyle='--', alpha=0.3, linewidth=0.8)

                # Skip displaying text labels if GAI in this zone is already above GAIc threshold
                    zone_gai = row['elem_data'][(row['elem_data']['t'] >= inter['start']) & 
                                            (row['elem_data']['t'] <= inter['end'])]['gai']
                    if not zone_gai.empty and zone_gai.max() > gaic:
                        continue

                    # Combined label: Number of leaves and Tiller index (TN = nb_leaves - (1 + delay))
                    n_tiller = int(inter['val'] - (1 + delay))
                    ax.text((inter['start'] + inter['end'])/2, y_text, f"F{int(inter['val'])} T{n_tiller}",
                            color=color, transform=ax.get_xaxis_transform(),
                            ha='center', va='top', fontsize=6.5, alpha=0.8)

            ax.set_title(f"GAIc {gaic} | Delay {delay}", fontweight='bold')
            if r == len(unique_gaic)-1: ax.set_xlabel("Temps (t)")
            if c == 0: ax.set_ylabel("GAI (Lines) | Leaf Appearance (Vlines)")
            
            if r == 0 and c == 0:
                ax.legend(loc='upper left', fontsize='small')

    plt.tight_layout()
    plt.savefig("green_area_and_leaves.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    plot_green_area_and_leaves("darwinkel")