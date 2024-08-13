import pandas as pd


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
        print(f'Error in {xls_col} data.')
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
        print(f"The duos ('service', 'treatment') >>> {d1[~validation_svc_treat].to_list()} <<< do not exist in rooms data.")
        validation = False

    return validation


class DataError(Exception):
    pass
