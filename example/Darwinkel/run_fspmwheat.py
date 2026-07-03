# -*- coding: latin-1 -*-

from __future__ import print_function

import os
import sys
import getopt

import pandas as pd
from math import exp

from fspmwheat import fspmwheat_postprocessing
from example.emergence import main
from example.emergence import tools
# from example.Scenarios_monoculms import additional_graphs

def exponential_fertilization_rate(V0, K, t, dt, plant_density):
    ferti_per_plant = V0 / K * (exp(-K * (t + dt) / 168) - exp(-K * t / 168))  # g N per plant
    return ferti_per_plant * plant_density * (10 ** 6) / 14  # µmol N m-2


def run_fspmwheat(scenario_id=1, inputs_dir_path='scenarios', outputs_dir_path='scenarios'):
    """
    Run the main.py of fspmwheat using data from a specific scenario

    :param int scenario_id: the index of the scenario to be read in the CSV file containing the list of scenarios
    :param str inputs_dir_path: the path directory of inputs
    :param str outputs_dir_path: the path to save outputs
    """

    # Scenario to be run
    scenarios_df = pd.read_csv(os.path.join(inputs_dir_path, 'scenarios_list.csv'), index_col='Scenario')
    scenario = scenarios_df.loc[scenario_id].to_dict()
    scenario_name = 'Scenario_%.4d' % scenario_id

    # -- SIMULATION PARAMETERS --

    # Create dict of parameters for the scenario
    scenario_parameters = tools.buildDic(scenario)

    # Path of the directory which contains the inputs of the model
    INPUTS_FILENAME = os.path.join(inputs_dir_path, 'inputs', scenario_parameters.get('INPUTS_FILENAME', 'inputs'))
    
    # Do run the simulation?
    RUN_SIMU = scenario_parameters.get('Run_Simulation', True)

    SIMULATION_LENGTH = scenario_parameters.get('Simulation_Length', 3000)

    # Do run the simulation from the output files ?
    RUN_FROM_OUTPUTS = scenario_parameters.get('Run_From_Outputs', False)

    # Do run the postprocessing?
    RUN_POSTPROCESSING = scenario_parameters.get('Run_Postprocessing', True)  #: TODO separate postprocessings coming from other models

    # Do generate the graphs?
    GENERATE_GRAPHS = scenario_parameters.get('Generate_Graphs', False)  #: TODO separate postprocessings coming from other models

    if RUN_SIMU or RUN_POSTPROCESSING or GENERATE_GRAPHS:

        # -- SIMULATION DIRECTORIES --

        # Path of the directory which contains the outputs of the model
        scenario_dirpath = os.path.join(outputs_dir_path, scenario_name)

        # Create the directory of the Scenario where results will be stored
        if not os.path.exists(scenario_dirpath):
            os.mkdir(scenario_dirpath)

        # Create directory paths for graphs, outputs and postprocessings of this scenario
        scenario_graphs_dirpath = os.path.join(scenario_dirpath, 'graphs')
        if not os.path.exists(scenario_graphs_dirpath):
            os.mkdir(scenario_graphs_dirpath)
        # Outputs
        scenario_outputs_dirpath = os.path.join(scenario_dirpath, 'outputs')
        if not os.path.exists(scenario_outputs_dirpath):
            os.mkdir(scenario_outputs_dirpath)
        # Postprocessings
        scenario_postprocessing_dirpath = os.path.join(scenario_dirpath, 'postprocessing')
        if not os.path.exists(scenario_postprocessing_dirpath):
            os.mkdir(scenario_postprocessing_dirpath)

        # Meteo
        meteo = scenario_parameters.get('METEO_FILENAME', 'meteo.csv')
                             
        # -- RUN main fspmwheat --
        print(scenario_name)
        try:
            main.main(simulation_length=SIMULATION_LENGTH, forced_start_time=0,
                      run_simu=RUN_SIMU, run_postprocessing=RUN_POSTPROCESSING,
                      generate_graphs=GENERATE_GRAPHS, run_from_outputs=RUN_FROM_OUTPUTS,
                      show_3Dplant=False, heterogeneous_canopy=True,
                      METEO_FILENAME=meteo,
                      N_fertilizations={3549: 357143, 4029: 1000000},
                      PLANT_DENSITY={1: 250},
                      GRAPHS_DIRPATH=scenario_graphs_dirpath,
                      INPUTS_DIRPATH=INPUTS_FILENAME,
                      OUTPUTS_DIRPATH=scenario_outputs_dirpath,
                      POSTPROCESSING_DIRPATH=scenario_postprocessing_dirpath,
                      tillers_replications={'T1': 0.5, 'T2': 0.5, 'T3': 0.5, 'T4': 0.5},
                      update_parameters_all_models=scenario_parameters)
            # if GENERATE_GRAPHS:
            #     additional_graphs.graph_summary(scenario_id, scenario_graphs_dirpath,
            #                                     graph_list=['LAI', 'sum_dry_mass_axis', 'shoot_roots_ratio_axis', 'N_content_shoot_axis', 'Conc_Amino_acids_phloem', 'Conc_Sucrose_phloem', 'leaf_Lmax',
            #                                                 'green_area_blade'])
            # if RUN_POSTPROCESSING:
            #     fspmwheat_postprocessing.leaf_traits(scenario_outputs_dirpath, scenario_postprocessing_dirpath)
            #     fspmwheat_postprocessing.table_C_usages(scenario_postprocessing_dirpath)
            #     fspmwheat_postprocessing.calculate_performance_indices(scenario_outputs_dirpath, scenario_postprocessing_dirpath, os.path.join(INPUTS_DIRPATH, scenario.get('METEO_FILENAME')),
            #                                                            scenario.get('Plant_Density', 250.))
            #     fspmwheat_postprocessing.canopy_dynamics(scenario_postprocessing_dirpath, os.path.join(INPUTS_DIRPATH, scenario.get('METEO_FILENAME')),
            #                                              scenario.get('Plant_Density', 250.))

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print(message, fname, exc_tb.tb_lineno)


if __name__ == '__main__':
    scenario = 8
    inputs = 'scenarios'
    outputs = 'scenarios'


    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:o:s:d", ["inputs=", "outputs=", "scenario="])
    except getopt.GetoptError as err:
        print(str(err))
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-i", "--inputs"):
            inputs = arg
        elif opt in ("-o", "--outputs"):
            outputs = arg
        elif opt in ("-s", "--scenario"):
            scenario = int(arg)

    run_fspmwheat(inputs_dir_path=inputs, outputs_dir_path=outputs, scenario_id=scenario)
