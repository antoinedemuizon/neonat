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


def test_new_room_alloc_cplx1():
    """
    Test new_room_alloc_cplx function on excel NRT1
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
    assert obj == 5
    assert (alloc_babies_rooms == expected_alloc_bb_rooms).all().all()


def test_new_room_alloc_cplx_mltpl_srv_per_room():
    """
    To show that a room can propose one among multiple service.
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
                                            ['bb10', 'out']],
                                            columns=['babies', 'new_place']
                                            )
    assert obj == 5
    assert (alloc_babies_rooms == expected_alloc_bb_rooms).all().all()


def test_new_room_alloc_cplx_unfeas():
    """
    Test new_room_alloc_cplx function NRT3.
    Not enough place in rea.
    """
    with pytest.raises(Exception) as e_info:
        obj, alloc_babies_rooms = call_new_room_alloc_cplx('nrt3')

    assert str(e_info.value) == ('Problem is IntegerInfeasible.'
                                 ' There might be a problem of data.')

