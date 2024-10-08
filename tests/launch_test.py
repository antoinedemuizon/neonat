import os.path as osp
import pandas as pd
import pytest
import logging

from run_bed_allocation import set_logging

from scripts.read_input import ReadInput
from scripts.calc_bed_allocation import (CalcBedAllocation, SCRIPT_DIR)


def call_calc_bed_allocation(nrt_name):
    """
    Call calc_bed_allocation for nrt tests.
    Input : name of the scenario
    Return : objective function value (float), allocation of babies per beds
        (pd.DataFrame)
    """
    input_path = osp.join(SCRIPT_DIR, '../tests', nrt_name,
                          'input_' + nrt_name + '.xlsx')

    bed_alloc_dataset = ReadInput(input_path)
    bed_alloc_dataset.read_input_from_excel()
    bed_alloc_scenario = CalcBedAllocation(
        inputs=bed_alloc_dataset
    )
    bed_alloc_scenario.declare_model()
    bed_alloc_scenario.solve_model()

    obj = bed_alloc_scenario.obj
    result = bed_alloc_scenario.result_summary
    alloc_babies_beds = result.reset_index(drop=True)[['babies', 'new_place']]
    return obj, alloc_babies_beds


def test_calc_bed_allocation_nrt1():
    """
    NRT1 : Test calc_bed_allocation function on a simple example.
    """
    obj, alloc_babies_beds = call_calc_bed_allocation('nrt1')
    expected_alloc_bb_beds = pd.DataFrame([['bb1', 'r1'],
                                            ['bb2', 'r2'],
                                            ['bb3', 'r3'],
                                            ['bb4', 'r6'],
                                            ['bb5', 'r5'],
                                            ['bb6', 'r4'],
                                            ['bb7', 'r7'],
                                            ['bb8', 'out'],
                                            ['bb9', 'out'],
                                            ['bb10', 'out']],
                                            columns=['babies', 'new_place']
                                            )
    expected_obj = 5

    assert obj == expected_obj
    assert (alloc_babies_beds == expected_alloc_bb_beds).all().all()


def test_calc_bed_allocation_nrt2():
    """
    NTR2 : To show that a bed can propose one among multiple service.
    """
    obj, alloc_babies_beds = call_calc_bed_allocation('nrt2')
    expected_alloc_bb_beds = pd.DataFrame([['bb1', 'r1'],
                                            ['bb2', 'r2'],
                                            ['bb3', 'r3'],
                                            ['bb4', 'r4'],
                                            ['bb5', 'r5'],
                                            ['bb6', 'r7'],
                                            ['bb7', 'r6'],
                                            ['bb8', 'out'],
                                            ['bb9', 'out'],
                                            ['bb10', 'out'],
                                            ['bb11', 'out']],
                                            columns=['babies', 'new_place']
                                            )
    expected_obj = 6

    assert obj == expected_obj
    assert (alloc_babies_beds == expected_alloc_bb_beds).all().all()


def test_calc_bed_allocation_prio():
    """
    To ensure the priority is well taken into account.
    Solution without priority :
   babies new_place
0     bb1        r5
1     bb2        r6
2     bb3        r7
3     bb4        r8
    Here, priority optimum switch bb3 and bb4 from r7 and r8
    to r10 and r9, because r7 and r9 "soins" is deprecated.
    """
    obj, alloc_babies_beds = call_calc_bed_allocation('test_priority')
    expected_alloc_bb_beds = pd.DataFrame([['bb1', 'r5'],
                                            ['bb2', 'r6'],
                                            ['bb3', 'r10'],
                                            ['bb4', 'r9']],
                                            columns=['babies', 'new_place']
                                            )
    expected_obj = 4

    assert obj == expected_obj
    assert (alloc_babies_beds == expected_alloc_bb_beds).all().all()


def test_calc_bed_allocation_nrt3():
    """
    NRT3 : Not enough place in rea.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_beds = call_calc_bed_allocation('nrt3')

    assert str(e_info.value) == ('There is a risk of unfeasability '
                                 'in your dataset, please reconsider it.')


def test_calc_bed_allocation_nrt4():
    """
    NRT4 : specific treatments.
    """
    obj, alloc_babies_beds = call_calc_bed_allocation('nrt4')
    expected_alloc_bb_beds = pd.DataFrame([['bb1', 'r3'],
                                            ['bb2', 'r2'],
                                            ['bb3', 'r1'],
                                            ['bb4', 'r6'],
                                            ['bb5', 'r4'],
                                            ['bb6', 'r5'],
                                            ['bb7', 'r7'],
                                            ['bb8', 'out'],
                                            ['bb9', 'out'],
                                            ['bb10', 'out']],
                                            columns=['babies', 'new_place']
                                            )
    expected_obj = 8

    assert obj == expected_obj
    assert (alloc_babies_beds == expected_alloc_bb_beds).all().all()


def test_calc_bed_allocation_nrt5(caplog):
    """
    NRT5 : causing errors with data errors.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_beds = call_calc_bed_allocation('nrt5')

    caplog.set_level(logging.INFO)
    assert caplog.messages == ["Be careful, there might be an error in >>> babies_service <<< data : are the element >>> ['neoe'] <<< present in other relevant datasets ?",
                               "Be careful, there might be an error in >>> old_alloc_list <<< data : are the element >>> ['r19'] <<< present in other relevant datasets ?",
                               "Be careful, there might be an error in >>> treatment <<< data : are the element >>> ['catheter'] <<< present in other relevant datasets ?",
                               "Be careful, there might be an error in >>> new_beds_service <<< data : are the element >>> ['reak'] <<< present in other relevant datasets ?",
                               "Be careful, the pairs ('service', 'treatment') >>> [('soins', 'catheter'), ('neoe', 'no_treatment')] <<< do not exist in beds data."]

    assert str(e_info.value) == ('There is some errors in your dataset mappings,'
                                 ' please reconsider it.')


def test_calc_bed_allocation_nrt6(caplog):
    """
    NRT6 : causing errors data incoherence.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_beds = call_calc_bed_allocation('nrt6')

    caplog.set_level(logging.INFO)
    assert caplog.messages == ["Be careful, not enough beds in ['neo', 'rea'] service(s)."]

    assert str(e_info.value) == ('There is a risk of unfeasability '
                                 'in your dataset, please reconsider it.')


def test_calc_bed_allocation_nrt7(caplog):
    """
    NRT7 : causing errors data incoherence.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_beds = call_calc_bed_allocation('nrt7')

    caplog.set_level(logging.INFO)
    assert caplog.messages == [
            "Be careful, the pairs ('service', 'treatment') "
            ">>> [('rea', 'not_vi')] <<< do not exist in beds data."
    ]

    assert str(e_info.value) == ('There is some errors in your dataset mappings,'
                                 ' please reconsider it.')


def test_calc_bed_allocation_log():
    """
    Test log file generation.
    """
    test_name = 'test_log'
    log_path = osp.join(SCRIPT_DIR, '../tests', test_name, 'log_' + test_name + '.log')
    set_logging(log_path)

    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_beds = call_calc_bed_allocation(test_name)

    assert str(e_info.value) == ('There is some errors in your dataset mappings,'
                                 ' please reconsider it.')

    log_file = open(log_path, "r")
    content = log_file.read()

    assert content == (
        "WARNING:root:Be careful, there might be an error in >>> babies_service <<< data :"
        " are the element >>> ['neoe'] <<< present in other relevant datasets ?\n"
        "WARNING:root:Be careful, there might be an error in >>> old_alloc_list <<< data :"
        " are the element >>> ['r19'] <<< present in other relevant datasets ?\n"
        "WARNING:root:Be careful, there might be an error in >>> treatment <<< data :"
        " are the element >>> ['catheter'] <<< present in other relevant datasets ?\n"
        "WARNING:root:Be careful, there might be an error in >>> new_beds_service <<< data :"
        " are the element >>> ['reak'] <<< present in other relevant datasets ?\n"
        "WARNING:root:Be careful, the pairs ('service', 'treatment')"
        " >>> [('soins', 'catheter'), ('neoe', 'no_treatment')] <<< do not exist in beds data.\n")
    log_file.close()
