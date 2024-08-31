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
        'babies': ['babies', 'babies_service', 'old_alloc_list', 'treatment'],
        'beds': ['all_beds', 'new_beds', 'old_beds', 'going_out',
                  'new_beds_service','old_beds_service', 'beds_capacities',
                  'priority', 'treatment']
    }

    validation_tab_names = all(ele in xls_file.sheet_names for ele in dico_columns.keys())
    if not validation_tab_names:
        print('Error in Excel Worksheet names.')
        print('You should have 3 worksheets : "babies", "beds" and "services".')
        validation = False
    
    for key in dico_columns.keys():
        columns_ds = pd.Series(dico_columns[key])
        xls_file_df = pd.read_excel(xls_file, key)
        xls_file_col = xls_file_df.columns
        validation_col_names = all(columns_ds.isin(xls_file_col))
        if not validation_col_names:
            print(f'Error in the column names of the tab ***{key}*** (line 1 of the sheet).')
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
                        f'<<< data : are the element >>> {black_list} <<< present in other relevant datasets ?')
        validation = False
    return validation


def map_list_control(services, babies, beds):
    """
    Several inputs we check to ensure the proper use of the tool:
    Ensure the gams objects mapping have no more data than their corresponding sets.
    """
    validation = True

    # Check mapping
    ## Babies should not pretend to a service that is not declared in sheet "services"
    babypot = babies['babies_service_df']
    srvc = services['services_list']
    validation = assert_map_in_set(validation, babypot, 'babies_service', srvc)

    ## Babies should not have an old bed that is not declared in sheet "beds"
    bboldalloc = babies['old_alloc_df']
    allr = beds['all_beds']
    validation = assert_map_in_set(validation, bboldalloc, 'old_alloc_list', allr)

    ## Babies should not have an treatment that is not declared in sheet "beds"
    bbtreat = babies['babies_treatment_df']
    alltreat = beds['treatment']
    validation = assert_map_in_set(validation, bbtreat, 'treatment', alltreat)

    ## beds should not have an treatment that is not declared in sheet "beds"
    bedsrvc = beds['new_beds_service_df']
    srvc = services['services_list']
    validation = assert_map_in_set(validation, bedsrvc, 'new_beds_service', srvc)

    # Tuple ('svc', 'treatment') for babies should be in the one of beds
    map_svc_treat_bb = pd.concat([bbtreat.reset_index(),
                                    babypot.reset_index()],
                                    axis=1
                                )[['babies_service', 'treatment']].drop_duplicates()
    map_svc_treat_rm = pd.concat([bedsrvc.reset_index(),
                               beds['beds_treatment_df'].reset_index()],
                               axis=1)[['new_beds_service', 'treatment']].drop_duplicates()
    d1 = pd.MultiIndex.from_frame(map_svc_treat_bb.dropna())
    d2 = pd.MultiIndex.from_frame(map_svc_treat_rm.dropna())

    validation_svc_treat = d1.isin(d2)
    if not validation_svc_treat.all():
        logging.warning("Be careful, the pairs ('service', 'treatment') >>>"
                        f" {d1[~validation_svc_treat].to_list()} "
                        "<<< do not exist in beds data."
                        )
        validation = False

    return validation


def count_element(mapping, dim1, dim2):
    """
    Function calculating the effective number of place available per service,
    considering babies service or beds places.
    If a bed propose a place in 'rea' or in 'soins', there is 0.5 place for both.
    Return a pd.Series.
    """
    map_df = pd.DataFrame(mapping)
    dim1_index = map_df.index.get_level_values(dim1)
    tmp = 1/map_df.groupby([dim1_index]).size()
    count_dim1 = tmp.loc[dim1_index].values
    map_df[f'count_{dim1}'] = count_dim1
    count_dim1_per_dim2_df = map_df.groupby([map_df.index.get_level_values(dim2)]).sum()
    count_dim1_per_dim2 = count_dim1_per_dim2_df[f'count_{dim1}']
    if (dim2 in ['new_beds_service', 'babies_service']
        and 'leave_hospital' in count_dim1_per_dim2):
        count_dim1_per_dim2 = count_dim1_per_dim2.drop('leave_hospital')

    return count_dim1_per_dim2


def coherence_control(services, babies, beds):
    """
    Several inputs we check to ensure the proper use of the tool:
    check if there is risk of unfeasibility.
    """
    validation = True

    # Incoherence in total nb of beds
    bed_capacities = beds['beds_capacities_df']
    new_beds = beds['new_beds']
    new_beds_capa = bed_capacities[bed_capacities['all_beds'].isin(new_beds)]
    tot_new_beds_capa = new_beds_capa['beds_capacities'].sum()

    bb_rm_pot_index = babies['babies_service_df'].index
    mask_babies_bed_potential = ~bb_rm_pot_index.get_level_values('babies_service').isin(['leave_hospital'])
    tot_baby_need = len(bb_rm_pot_index[mask_babies_bed_potential])

    # More precisely :
    count_beds_per_svc = count_element(beds['new_beds_service_df'],
                                        'all_beds', 'new_beds_service')
    count_bb_per_svc = count_element(babies['babies_service_df'],
                                     'babies', 'babies_service')
    count_bb_per_svc.sort_index(inplace=True)

    compare_tot = count_bb_per_svc - count_beds_per_svc > 0
    compare = count_bb_per_svc - count_beds_per_svc >= 1

    if tot_baby_need > tot_new_beds_capa:
        logging.warning('Be careful, not enough beds in '
                        f'{compare_tot[compare_tot].index.to_list()} service(s).')
        validation = False

    elif compare.any():
        logging.warning('Be careful, enough total nb of beds, but not enough beds'
                        f' in {compare[compare].index.to_list()} service(s).')
        validation = False

    return validation
