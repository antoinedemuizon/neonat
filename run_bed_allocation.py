import os.path as osp
import pandas as pd
import argparse
import logging

from scripts.read_input import ReadInput
from scripts.calc_bed_allocation import (CalcBedAllocation, SCRIPT_DIR)


pd.options.mode.copy_on_write = True


def set_logging(log_path):
    logging.basicConfig(filename=log_path, filemode='w', force=True)


def run_neonat():
    """
    From a scenario_name, run a scenario of new bed allocation.
    Scenario_name is the name of the folder,
    which include an Excel file "input.xls" to be read by the script.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario_name')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    scenario_name = args.scenario_name
    force = args.force
    xls_input_path = osp.join(SCRIPT_DIR, '../scenarios', scenario_name,
                              'input_' + scenario_name + '.xlsx')
    xls_output_path = osp.join(SCRIPT_DIR, '../scenarios', scenario_name,
                               'output_' + scenario_name + '.xlsx')
    log_path = osp.join(SCRIPT_DIR, '../scenarios', scenario_name,
                        'log_' + scenario_name + '.log')

    set_logging(log_path=log_path)

    bed_alloc_dataset = ReadInput(input_path=xls_input_path, force=force)
    bed_alloc_dataset.read_input_from_excel()

    bed_alloc_scenario = CalcBedAllocation(
        inputs=bed_alloc_dataset,
        output_path=xls_output_path
    )
    bed_alloc_scenario.declare_model()
    bed_alloc_scenario.run_model()
    bed_alloc_scenario.write_output()

    result = bed_alloc_scenario.result_summary
    baby_move_nb = result['should_move'].sum()
    print(f'{baby_move_nb} out of {len(result)} babies should change beds.')
    print(result)
    ###
    print(f'obj fun is equal to {bed_alloc_scenario.obj}')


if __name__ == '__main__':
    run_neonat()
