import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons, Slider

# Dictionnaire des zones fixes mis à jour (Âge v2 removed)
ZONES_DATA = {
    'DD Sol': {
        2: (264, 335),
        3: (264, 335),
        4: (336, 431),
        5: (552, 647),
        6: (744, 1079),
        7: (1368, 1487),
        8: (1584, 1799),
        9: (1920, 2039),
        10: (2304, 2447),
        11: (2544, 2783)
    },
    'Âge': {
        2: (140, 194),
        3: (288, 354),
        4: (371, 469),
        5: (593, 695),
        6: (1025, 1311),
        7: (1437, 1559),
        8: (1762, 1896),
        9: (2013, 2239),
        10: (2388, 2512),
        11: (2727, 3031)
    }
}

def load_all_data(base_dir="parallel_tests", 
                  elem_file="elements_postprocessing.csv", 
                  filter_buffer=1):
    search_pattern = os.path.join(base_dir, "postprocessing_*")
    post_folders = glob.glob(search_pattern)
    data_store = {}

    print("🔍 Pre-loading data from parallel_tests...")
    for folder in sorted(post_folders):
        folder_name = os.path.basename(folder)
        match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder_name)
        if not match: continue
        
        gaic = float(match.group(1))
        density = int(float(match.group(2)))
        buf = float(match.group(4))
        
        if buf != filter_buffer: continue

        path_elem = os.path.join(folder, elem_file)

        if os.path.exists(path_elem):
            try:
                df_elem = pd.read_csv(path_elem)
                # Filter out 'HiddenElement' before aggregating
                df_elem_filtered = df_elem[df_elem['element'] != 'HiddenElement']
                df_sum_elem = df_elem_filtered.groupby('t')['green_area'].sum().reset_index()
                df_sum_elem['gai'] = df_sum_elem['green_area'] * density

                key = gaic
                if key not in data_store: data_store[key] = []
                
                existing_densities = [item['density'] for item in data_store[key]]
                if density not in existing_densities:
                    data_store[key].append({'density': density, 'elem_data': df_sum_elem})
            except Exception as e:
                print(f"⚠️ Warning: Could not process {folder_name} ({e})")
    return data_store

def plot_interactive():
    data_store = load_all_data()
    if not data_store:
        print("❌ Error: No valid simulation data found in parallel_tests.")
        return

    unique_gaics = sorted(list(data_store.keys()))

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 1, height_ratios=[7, 1], hspace=0.05)
    
    ax = fig.add_subplot(gs[0])
    ax_timeline = fig.add_subplot(gs[1], sharex=ax)
    
    plt.subplots_adjust(left=0.20, bottom=0.15, right=0.78)

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    state = {'gaic': unique_gaics[0], 'zone_type': 'DD Sol'}

    def update_plot():
        ax.clear()
        ax_timeline.clear()
        
        available_gaics = sorted(list(data_store.keys()))
        sim_gaic = min(available_gaics, key=lambda x: abs(x - state['gaic']))
        key = sim_gaic
        
        active_zones = ZONES_DATA[state['zone_type']]
        
        # --- 1. Dessin de la Timeline ---
        grouped_zones = {}
        for m, (start, end) in active_zones.items():
            if (start, end) not in grouped_zones:
                grouped_zones[(start, end)] = []
            grouped_zones[(start, end)].append(m)

        for (start, end), m_list in grouped_zones.items():
            label = "M" + "/M".join(map(str, m_list))
            ax_timeline.add_patch(plt.Rectangle((start, 0.2), end - start, 0.6, 
                                                color='#e0e0e0', ec='#a0a0a0', lw=1.5))
            ax_timeline.text((start + end) / 2, 0.5, label, 
                             ha='center', va='center', fontsize=9, fontweight='bold', color='#333333')
            ax.axvspan(start, end, color='gray', alpha=0.08)

        ax_timeline.set_ylim(0, 1)
        ax_timeline.set_yticks([])
        ax_timeline.set_xlabel("Time (t)", fontweight='bold')
        ax_timeline.spines['top'].set_visible(False)
        ax_timeline.spines['right'].set_visible(False)
        ax_timeline.spines['left'].set_visible(False)
        ax_timeline.set_ylabel(state['zone_type'], fontweight='bold', rotation=0, labelpad=35, va='center')

        # --- 2. Dessin du Graphique Principal ---
        ax.tick_params(labelbottom=False)
        
        if key in data_store:
            subset = sorted(data_store[key], key=lambda x: x['density'])
            all_densities = [s['density'] for s in subset]
            color_map = {d: colors[i % len(colors)] for i, d in enumerate(all_densities)}
            
            ax.axhline(y=state['gaic'], color='black', linestyle=':', linewidth=1.5, alpha=0.7, label=f"Threshold (GAIc={state['gaic']:.2f})")
            
            for row in subset:
                density, color = row['density'], color_map[row['density']]
                ax.plot(row['elem_data']['t'], row['elem_data']['gai'], color=color, label=f"Density {density}", linewidth=2)
                
                # --- LOGIQUE DE POSITIONNEMENT DES LABELS ---
                y_base = 0.98 - (all_densities.index(density) * 0.12)
                labels_to_plot = []
                
                for (start, end), m_list in grouped_zones.items():
                    zone_data = row['elem_data'][(row['elem_data']['t'] >= start) & (row['elem_data']['t'] <= end)]
                    
                    if not zone_data.empty and zone_data['gai'].max() <= state['gaic']:
                        for m in m_list:
                            labels_to_plot.append({
                                'text': f"F{m} T{int(m - 1)}",
                                'x_ideal': (start + end)/2
                            })
                
                # Dessiner les labels en quinconce (staggered) pour éviter les collisions
                for i, lbl in enumerate(labels_to_plot):
                    y_offset = (i % 2) * 0.05
                    y_final = y_base - y_offset
                    
                    ax.text(lbl['x_ideal'], y_final, lbl['text'],
                            color=color, transform=ax.get_xaxis_transform(),
                            ha='center', va='top', fontsize=8.5, fontweight='bold',
                            bbox=dict(facecolor='#ffffff', edgecolor=color, alpha=0.85, boxstyle='round,pad=0.25', linewidth=1))

        ax.set_title(f"Interactive Analysis: Threshold {state['gaic']:.2f} | Sim GAIc {sim_gaic}", fontweight='bold', pad=15)
        ax.set_ylabel("GAI (Green Area Index)", fontweight='bold')
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=True, shadow=True, fontsize='small')
        ax.grid(True, linestyle=':', alpha=0.5)
        
        plt.draw()

    # --- 3. Création des Widgets ---
    ax_gaic_wdgt = plt.axes([0.25, 0.03, 0.45, 0.03], facecolor='#fdfdfd')
    slider_gaic = Slider(ax_gaic_wdgt, 'GAIc Threshold ', 0.0, 0.40, valinit=state['gaic'], valstep=0.01)
    
    # Hauteur réduite à 0.15 car il n'y a plus que 2 options
    ax_zone_wdgt = plt.axes([0.02, 0.40, 0.12, 0.15], facecolor='#fdfdfd')
    radio_zone = RadioButtons(ax_zone_wdgt, ['DD Sol', 'Âge'])
    ax_zone_wdgt.set_title('Type de Zone', fontweight='bold')

    slider_gaic.on_changed(lambda val: (state.update({'gaic': val}), update_plot()))
    radio_zone.on_clicked(lambda label: (state.update({'zone_type': label}), update_plot()))

    update_plot()
    print("✅ Ready! Use the widgets to explore zones and parameters.")
    plt.show()

if __name__ == "__main__":
    plot_interactive()