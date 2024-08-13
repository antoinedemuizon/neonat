import os.path as osp
import pandas as pd
import pytest

from neonat_baby_move import (new_room_alloc_simple, new_room_alloc_cplx,
                              read_input, write_output, SCRIPT_DIR)


def test_new_room_alloc_simple():
    babies = ['bb1', 'bb2', 'bb3', 'bb4']
    old_rooms = ['r1', 'r2', 'r3', 'r4']
    new_rooms = ['r1', 'r2', 'r3']

    result, obj = new_room_alloc_simple(babies_list=babies,
                                        old_rooms_list=old_rooms,
                                        new_rooms_list=new_rooms)
    alloc_babies_rooms = result.reset_index(drop=True)
    assert obj == 3.0
    assert (alloc_babies_rooms == pd.DataFrame([['bb1', 'r1'],
                                               ['bb2', 'r2'],
                                               ['bb3', 'r3'],
                                               ['bb4', 'out']],
                                               columns=['babies', 'all_rooms'])
                                               ).all().all()
    
    print(alloc_babies_rooms)


def call_new_room_alloc_cplx(nrt_name):
    """
    Call new_room_alloc_cplx for nrt tests.
    Input : name of the scenario
    Return : objective function value (float), allocation of babies per rooms
        (pd.DataFrame)
    """
    input_path = osp.join(SCRIPT_DIR, 'tests', nrt_name,
                          'input_' + nrt_name + '.xlsx')
    services, babies, rooms = read_input(input_path)
    result, obj = new_room_alloc_cplx(
        services=services,
        babies=babies,
        rooms=rooms
    )
    alloc_babies_rooms = result.reset_index(drop=True)[['babies', 'new_place']]
    return obj, alloc_babies_rooms


def test_new_room_alloc_cplx_nrt1():
    """
    NRT1 : Test new_room_alloc_cplx function on a simple example.
    """
    obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt1')
    expected_alloc_bb_rooms = pd.DataFrame([['bb1', 'r1'],
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
    assert (alloc_babies_rooms == expected_alloc_bb_rooms).all().all()


def test_new_room_alloc_cplx_nrt2():
    """
    NTR2 : To show that a room can propose one among multiple service.
    """
    obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt2')
    expected_alloc_bb_rooms = pd.DataFrame([['bb1', 'r1'],
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
    assert (alloc_babies_rooms == expected_alloc_bb_rooms).all().all()


def test_new_room_alloc_cplx_prio():
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
    obj, alloc_babies_rooms = call_new_room_alloc_cplx('test_priority')
    expected_alloc_bb_rooms = pd.DataFrame([['bb1', 'r5'],
                                            ['bb2', 'r6'],
                                            ['bb3', 'r10'],
                                            ['bb4', 'r9']],
                                            columns=['babies', 'new_place']
                                            )
    expected_obj = 4

    assert obj == expected_obj
    assert (alloc_babies_rooms == expected_alloc_bb_rooms).all().all()


def test_new_room_alloc_cplx_nrt3():
    """
    NRT3 : Not enough place in rea.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt3')

    assert str(e_info.value) == ('Problem is IntegerInfeasible.'
                                 ' There might be a problem of data.')


def test_new_room_alloc_cplx_nrt4():
    """
    NRT4 : specific treatments.
    """
    obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt4')
    expected_alloc_bb_rooms = pd.DataFrame([['bb1', 'r3'],
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
    assert (alloc_babies_rooms == expected_alloc_bb_rooms).all().all()


def test_new_room_alloc_cplx_nrt5(capsys):
    """
    NRT5 : causing errors with data errors.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt5')

    captured = capsys.readouterr()
    assert captured.out == ('Error in babies_potential data.\n'
                            'Error in old_alloc_list data.\n'
                            'Error in treatment data.\n'
                            'Error in new_rooms_service data.\n'
                            "The duos ('service', 'treatment') >>> "
                            "[('soins', 'catheter'), ('neoe', 'no_treatment')]"
                            " <<< do not exist in rooms data.\n")

    assert str(e_info.value) == ('There is some errors in your dataset mappings,'
                                 ' please reconsider it.')


def test_new_room_alloc_cplx_nrt7(capsys):
    """
    NRT7 : causing errors data incoherence.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt7')

    captured = capsys.readouterr()
    assert captured.out == (
            "The duos ('service', 'treatment') "
            ">>> [('rea', 'not_vi')] <<< do not exist in rooms data.\n"
            )

    assert str(e_info.value) == ('There is some errors in your dataset mappings,'
                                 ' please reconsider it.')
