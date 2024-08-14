import pandas as pd
import logging


def mapping_creation(df):
    """
    Return a pd.Series adapted to gamspy map object.
    """
    multi_index = pd.MultiIndex.from_frame(df.dropna()).drop_duplicates()
    gamspy_mapping_df = pd.Series(index=multi_index)
    return gamspy_mapping_df


def excel_control(xls_file):
    """
    Control xls_file tabs and columns names.
    """
    validation = True
    dico_columns = {
        'services': ['services'],
        'babies': ['babies', 'babies_potential', 'old_alloc_list', 'treatment'],
        'rooms': ['all_rooms', 'new_rooms', 'old_rooms', 'going_out',
                  'new_rooms_service','old_rooms_service', 'rooms_capacities',
                  'priority', 'treatment']
    }

    validation_tab_names = all(ele in xls_file.sheet_names for ele in dico_columns.keys())
    if not validation_tab_names:
        print('Error in Excel Worksheet names.')
        print('You should have 3 worksheets : "babies", "rooms" and "services".')
        # TODO : raise an error ?
        validation = False
    
    for key in dico_columns.keys():
        columns_ds = pd.Series(dico_columns[key])
        xls_file_df = pd.read_excel(xls_file, key)
        xls_file_col = xls_file_df.columns
        validation_col_names = all(columns_ds.isin(xls_file_col))
        if not validation_col_names:
            print(f'Error in the column names of the tab ***{key}*** (line 1 of the sheet).')
            # TODO : raise an error ?
            validation = False

    return validation


def assert_map_in_set(validation, map_df, xls_col, set_ds):
    """
    Assert if a map with the relevant set (which might be in another worksheet).
    Return False if the map has elts out of set.
    """
    map_index = map_df.index.get_level_values(xls_col).drop_duplicates()
    if not map_index.isin(set_ds).all():
        black_list = map_index[~map_index.isin(set_ds)].to_list()
        logging.warning(f'Be careful, there might be an error in >>> {xls_col} '
                        f'<<< data : are the element >>> {black_list} <<< well written ?')
        validation = False
    return validation


def map_list_control(services, babies, rooms):
    """
    Several inputs we check to ensure the proper use of the tool:
    Ensure the gams objects mapping have no more data than their corresponding sets.
    """
    validation = True

    # Check mapping
    ## Babies should not pretend to a service that is not declared in sheet "services"
    babypot = babies['babies_potential_df']
    srvc = services['services_list']
    validation = assert_map_in_set(validation, babypot, 'babies_potential', srvc)

    ## Babies should not have an old room that is not declared in sheet "rooms"
    bboldalloc = babies['old_alloc_df']
    allr = rooms['all_rooms']
    validation = assert_map_in_set(validation, bboldalloc, 'old_alloc_list', allr)

    ## Babies should not have an treatment that is not declared in sheet "rooms"
    bbtreat = babies['babies_treatment_df']
    alltreat = rooms['treatment']
    validation = assert_map_in_set(validation, bbtreat, 'treatment', alltreat)

    ## Rooms should not have an treatment that is not declared in sheet "rooms"
    roomsrvc = rooms['new_rooms_service_df']
    srvc = services['services_list']
    validation = assert_map_in_set(validation, roomsrvc, 'new_rooms_service', srvc)

    # Tuple ('svc', 'treatment') for babies should be in the one of rooms
    map_svc_treat_bb = pd.concat([bbtreat.reset_index(),
                                    babypot.reset_index()],
                                    axis=1
                                )[['babies_potential', 'treatment']].drop_duplicates()
    map_svc_treat_rm = pd.concat([roomsrvc.reset_index(),
                               rooms['rooms_treatment_df'].reset_index()],
                               axis=1)[['new_rooms_service', 'treatment']].drop_duplicates()
    d1 = pd.MultiIndex.from_frame(map_svc_treat_bb.dropna())
    d2 = pd.MultiIndex.from_frame(map_svc_treat_rm.dropna())

    validation_svc_treat = d1.isin(d2)
    if not validation_svc_treat.all():
        logging.warning("Be careful, the pairs ('service', 'treatment') >>>"
                        f" {d1[~validation_svc_treat].to_list()} "
                        "<<< do not exist in rooms data."
                        )
        validation = False

    return validation


def count_element(mapping, dim1, dim2):
    """
    Function calculating the effective number of place available per service,
    considering babies potential or rooms places.
    If a room propose a place in 'rea' or in 'soins', there is 0.5 place for both.
    Return a pd.Series.
    """
    map_df = pd.DataFrame(mapping)
    dim1_index = map_df.index.get_level_values(dim1)
    tmp = 1/map_df.groupby([dim1_index]).size()
    count_dim1 = tmp.loc[dim1_index].values
    map_df[f'count_{dim1}'] = count_dim1
    count_dim1_per_dim2_df = map_df.groupby([map_df.index.get_level_values(dim2)]).sum()
    count_dim1_per_dim2 = count_dim1_per_dim2_df[f'count_{dim1}']
    if (dim2 in ['new_rooms_service', 'babies_potential']
        and 'leave_hospital' in count_dim1_per_dim2):
        count_dim1_per_dim2 = count_dim1_per_dim2.drop('leave_hospital')

    return count_dim1_per_dim2


def coherence_control(services, babies, rooms):
    """
    Several inputs we check to ensure the proper use of the tool:
    check if there is risk of unfeasibility.
    """
    validation = True

    # Incoherence in total nb of rooms
    room_capacities = rooms['rooms_capacities_df']
    new_rooms = rooms['new_rooms']
    new_rooms_capa = room_capacities[room_capacities['all_rooms'].isin(new_rooms)]
    tot_new_rooms_capa = new_rooms_capa['rooms_capacities'].sum()

    bb_rm_pot_index = babies['babies_potential_df'].index
    mask_babies_room_potential = ~bb_rm_pot_index.get_level_values('babies_potential').isin(['leave_hospital'])
    tot_baby_need = len(bb_rm_pot_index[mask_babies_room_potential])

    # More precisely :
    count_rooms_per_svc = count_element(rooms['new_rooms_service_df'],
                                        'all_rooms', 'new_rooms_service')
    count_bb_per_svc = count_element(babies['babies_potential_df'],
                                     'babies', 'babies_potential')
    count_bb_per_svc.sort_index(inplace=True)

    compare_tot = count_bb_per_svc - count_rooms_per_svc > 0
    compare = count_bb_per_svc - count_rooms_per_svc >= 1

    if tot_baby_need > tot_new_rooms_capa:
        logging.warning('Be careful, not enough rooms in '
                        f'{compare_tot[compare_tot].index.to_list()} service(s).')
        validation = False

    elif compare.any():
        logging.warning('Be careful, enough total nb of rooms, but not enough rooms'
                        f' in {compare[compare].index.to_list()} service(s).')
        validation = False

    return validation


class DataError(Exception):
    pass


class IncoherentDataError(Exception):
    pass
