import multiprocessing
import itertools
import os
import time
import main as fspm_main

def run_single_simulation(params):
    """
    Worker function for multiprocessing. Configures unique output directories and 
    executes a single FSPM simulation instance using a specific combination of 
    GAIc, density, delay, and buffer parameters provided via a tuple.
    """
    gaic, density, coef_delay, coef_buffer = params
    
    # Définition du dossier parent
    base_dir = "darwinkel"
    
    # Création du nom du dossier spécifique à cette simulation (la référence)
    sim_ref_name = f"GAIc_{gaic}_dens_{density}_delay_{coef_delay}_buf_{coef_buffer}"
    sim_dir = os.path.join(base_dir, sim_ref_name)
    
    # Définition des chemins pour les sous-dossiers
    output_path = os.path.join(sim_dir, "outputs")
    post_path = os.path.join(sim_dir, "postprocessing")
    graph_path = os.path.join(sim_dir, "graphs")

    # Création des répertoires (exist_ok=True prévient les erreurs en multi-processus)
    for path in [output_path, post_path, graph_path]:
        os.makedirs(path, exist_ok=True)

    print(f">>> Démarrage : GAIc={gaic}, Density={density}, Delay={coef_delay}, Buffer={coef_buffer} (PID: {os.getpid()})")

    try:
        # Appel du main avec les paramètres et les nouveaux dossiers
        fspm_main.main(
            simulation_length=4000,
            forced_start_time=800,
            run_simu=True,
            run_postprocessing=True,
            generate_graphs=True,
            show_3Dplant=False,  # Important : désactivé pour le parallélisme
            PLANT_DENSITY={1: density},
            N_fertilizations={2949: 357143, 4029: 1000000},
            GAIc=gaic,
            coef_delay_til=coef_delay,
            coef_buffer_til=coef_buffer,
            OUTPUTS_DIRPATH=output_path,
            POSTPROCESSING_DIRPATH=post_path,
            GRAPHS_DIRPATH=graph_path,
            METEO_FILENAME='Darwinkel_open-meteo_since19101976.csv'
        )
        print(f"✅ OK : Terminé pour GAIc={gaic}, Dens={density}, Delay={coef_delay}, Buf={coef_buffer}")
    except Exception as e:
        print(f"❌ ERREUR sur GAIc={gaic}, Dens={density}, Delay={coef_delay}, Buf={coef_buffer} : {e}")

if __name__ == '__main__':
    # 1. Définition des plages de valeurs à tester
    gaic_values = [0.11]
    density_values = [100, 200, 250, 400, 800]
    coef_delay_values = [2.0]   
    coef_buffer_values = [0.5] 

    # 2. Génération de toutes les combinaisons
    tasks = list(itertools.product(gaic_values, density_values, coef_delay_values, coef_buffer_values))

    # 3. Configuration matérielle (20 cœurs disponibles, on en garde 2 pour le système)
    MAX_CORES = os.cpu_count() - 2
    num_cpus = min(MAX_CORES, len(tasks))
    
    # Définition pour l'affichage
    base_dir = "darwinkel"
    
    print("====================================================")
    print(f"Préparation de {len(tasks)} simulations FSPM.")
    print(f"Toutes les sorties iront dans le dossier racine : '{base_dir}'")
    print(f"Chaque simulation aura son propre sous-dossier de référence.")
    print(f"Lancement du pool sur {num_cpus} cœurs (sur {os.cpu_count()} dispo).")
    print("====================================================\n")

    start_time = time.time()

    # 4. Exécution parallèle
    with multiprocessing.Pool(processes=num_cpus) as pool:
        pool.map(run_single_simulation, tasks)

    end_time = time.time()
    execution_time = end_time - start_time
    
    # Formatage du temps total d'exécution
    hours, rem = divmod(execution_time, 3600)
    minutes, seconds = divmod(rem, 60)

    print("\n====================================================")
    print("Toutes les simulations parallèles sont terminées.")
    print(f"Temps total d'exécution : {int(hours)}h {int(minutes)}m {int(seconds)}s")
    print("====================================================")