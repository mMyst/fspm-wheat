import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

def load_all_data(base_dir="darwinkel", 
                  elem_file="elements_postprocessing.csv", 
                  axes_file="axes_postprocessing.csv",
                  filter_buffer=0.5):
    """
    Loads data recursively using Darwinkel's dynamic leaf extraction logic.
    """
    search_pattern = os.path.join(base_dir, "**", "postprocessing*")
    post_folders = glob.glob(search_pattern, recursive=True)
    data_store = {}

    print("🔍 Pre-loading data from Darwinkel...")
    for folder in sorted(post_folders):
        folder_name = os.path.basename(folder)
        match = re.search(r'GAIc_([\d\.]+)_dens_([\d\.]+)_delay_([\d\.]+)_buf_([\d\.]+)', folder)
        
        if not match: continue
        
        gaic = float(match.group(1))
        density = int(float(match.group(2)))
        delay = float(match.group(3))
        buf = float(match.group(4))
        
        if buf != filter_buffer: continue

        path_elem = os.path.join(folder, elem_file)
        path_axes = os.path.join(folder, axes_file)

        if os.path.exists(path_elem) and os.path.exists(path_axes):
            try:
                # Calculate GAI
                df_elem = pd.read_csv(path_elem)

                # Filter out 'HiddenElement' before aggregating
                df_elem_filtered = df_elem[df_elem['element'] != 'HiddenElement']

                df_sum_elem = df_elem_filtered.groupby('t')['green_area'].sum().reset_index()
                df_sum_elem['gai'] = df_sum_elem['green_area'] * density

                # Calculate dynamic intervals based on nb_leaves
                df_axes = pd.read_csv(path_axes)
                df_sum_axes = df_axes.groupby('t')['nb_leaves'].sum().reset_index().sort_values('t')
                
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
                
                # Store grouped by GAIc and Delay
                key = (gaic, delay)
                if key not in data_store: data_store[key] = []
                
                existing_densities = [item['density'] for item in data_store[key]]
                if density not in existing_densities:
                    data_store[key].append({
                        'density': density, 
                        'elem_data': df_sum_elem,
                        'intervals': intervals
                    })
            except Exception as e:
                print(f"⚠️ Warning: Could not process {folder_name} ({e})")
                
    return data_store

def plot_interactive():
    data_store = load_all_data()
    if not data_store:
        print("❌ Error: No valid simulation data found in the darwinkel directory.")
        return

    unique_gaics = sorted(list(set([k[0] for k in data_store.keys()])))
    unique_delays = sorted(list(set([k[1] for k in data_store.keys()])))

    fig, ax = plt.subplots(figsize=(14, 8))
    plt.subplots_adjust(left=0.10, bottom=0.25, right=0.85)

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    state = {'gaic': unique_gaics[0], 'delay': unique_delays[0], 'buffer': 1.0}

    def update_plot():
        ax.clear()
        
        sim_gaic = min(unique_gaics, key=lambda x: abs(x - state['gaic']))
        sim_delay = min(unique_delays, key=lambda x: abs(x - state['delay']))
        key = (sim_gaic, sim_delay)
        
        if key in data_store:
            subset = sorted(data_store[key], key=lambda x: x['density'])
            all_densities = [s['density'] for s in subset]
            color_map = {d: colors[i % len(colors)] for i, d in enumerate(all_densities)}
            
            ax.axhline(y=state['gaic'], color='black', linestyle=':', linewidth=1.5, alpha=0.7, 
                       label=f"Threshold (GAIc={state['gaic']:.2f})")
            
            for row in subset:
                density = row['density']
                color = color_map[density]
                
                ax.plot(row['elem_data']['t'], row['elem_data']['gai'], color=color, 
                        label=f"Density {density}", linewidth=2)
                
                y_text_base = 0.98 - (all_densities.index(density) * 0.04)
                
                for inter in row['intervals']:
                    # Dynamic checking window scaling
                    duration = inter['end'] - inter['start']
                    dynamic_end = inter['start'] + (duration * state['buffer'])

                    if inter['start'] > row['elem_data']['t'].min():
                        # Draw Start Line
                        ax.axvline(x=inter['start'], color=color, linestyle='--', alpha=0.4, linewidth=1)
                        # Draw Dynamic End Line
                        ax.axvline(x=dynamic_end, color=color, linestyle=':', alpha=0.4, linewidth=1)
                        # Lightly shade the active checking window
                        ax.axvspan(inter['start'], dynamic_end, color=color, alpha=0.05)

                    # Check GAI strictly within the buffered time window
                    zone_gai = row['elem_data'][(row['elem_data']['t'] >= inter['start']) & 
                                                (row['elem_data']['t'] <= dynamic_end)]['gai']
                    
                    if not zone_gai.empty and zone_gai.max() <= state['gaic']:
                        n_tiller = int(inter['val'] - (1 + sim_delay))
                        label_text = f"F{int(inter['val'])} T{n_tiller}"
                        
                        ax.text((inter['start'] + inter['end']) / 2, y_text_base, label_text,
                                color=color, transform=ax.get_xaxis_transform(),
                                ha='center', va='top', fontsize=7.5, alpha=0.9, fontweight='bold',
                                bbox=dict(facecolor='#ffffff', edgecolor=color, alpha=0.7, boxstyle='round,pad=0.2', linewidth=0.5))

        ax.set_title(f"Darwinkel Dynamic Analysis: Threshold {state['gaic']:.2f} | Delay {sim_delay:.2f} | Window {state['buffer']:.0%}", fontweight='bold', pad=15)
        ax.set_ylabel("GAI / Leaf Appearance", fontweight='bold')
        ax.set_xlabel("Time (t)", fontweight='bold')
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=True, shadow=True, fontsize='small')
        ax.grid(True, linestyle=':', alpha=0.5)
        
        plt.draw()

    # --- Create Sliders ---
    ax_gaic_wdgt = plt.axes([0.15, 0.13, 0.70, 0.03], facecolor='#fdfdfd')
    slider_gaic = Slider(ax_gaic_wdgt, 'GAIc Threshold ', 0.0, 0.50, valinit=state['gaic'], valstep=0.01)

    ax_delay_wdgt = plt.axes([0.15, 0.08, 0.70, 0.03], facecolor='#fdfdfd')
    delay_step = unique_delays[1] - unique_delays[0] if len(unique_delays) > 1 else 0.5
    slider_delay = Slider(ax_delay_wdgt, 'Delay', min(unique_delays), max(unique_delays), valinit=state['delay'], valstep=delay_step)

    ax_buffer_wdgt = plt.axes([0.15, 0.03, 0.70, 0.03], facecolor='#fdfdfd')
    slider_buffer = Slider(ax_buffer_wdgt, 'Window Buffer', 0.1, 1.0, valinit=state['buffer'], valstep=0.05)

    slider_gaic.on_changed(lambda val: (state.update({'gaic': val}), update_plot()))
    slider_delay.on_changed(lambda val: (state.update({'delay': val}), update_plot()))
    slider_buffer.on_changed(lambda val: (state.update({'buffer': val}), update_plot()))

    update_plot()
    print("✅ Ready! Use the sliders to adjust Threshold, Delay, and Window scale.")
    plt.show()

if __name__ == "__main__":
    plot_interactive()