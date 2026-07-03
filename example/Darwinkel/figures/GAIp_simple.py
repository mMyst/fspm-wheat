import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt

def plot_simple_gai(base_dir="darwinkel"):
    # Find all elements files recursively
    search_pattern = os.path.join(base_dir, "**", "elements_postprocessing.csv")
    files = glob.glob(search_pattern, recursive=True)
    
    if not files:
        print(f"❌ Error: No 'elements_postprocessing.csv' files found in {base_dir}")
        return

    plt.figure(figsize=(12, 7))

    for file in sorted(files):
        # Correctly extract the main simulation folder name from the path
        match_folder = re.search(r'(GAIc_[^\\/]+)', file)
        folder_name = match_folder.group(1) if match_folder else "Unknown_Run"
        
        # Extract density from that folder name to calculate GAIp
        match_dens = re.search(r'dens_([\d\.]+)', folder_name)
        density = int(float(match_dens.group(1))) if match_dens else 1 

        try:
            # Read data
            df = pd.read_csv(file)
            
            # Filter out 'HiddenElement' before aggregating
            df_filtered = df[df['element'] != 'HiddenElement']
            
            # Aggregate and calculate GAIp
            df_sum = df_filtered.groupby('t')['green_area'].sum().reset_index()
            df_sum['gaip'] = df_sum['green_area'] * density
            
            # Plot
            plt.plot(df_sum['t'], df_sum['gaip'], label=folder_name, linewidth=2)
            
        except Exception as e:
            print(f"⚠️ Could not process {folder_name}: {e}")

    # Styling
    plt.title("GAIp over Time by Simulation Folder", fontweight='bold', pad=15)
    plt.xlabel("Time (t)", fontweight='bold')
    plt.ylabel("GAIp", fontweight='bold')
    plt.grid(True, linestyle=':', alpha=0.6)
    
    # Place legend outside the plot area so it doesn't cover the data
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    plt.tight_layout()
    
    print(f"✅ Plotted {len(files)} simulations.")
    plt.show()

if __name__ == "__main__":
    plot_simple_gai()