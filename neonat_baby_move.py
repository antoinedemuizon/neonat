# import sys
import os.path as osp
import pandas as pd
import argparse
import logging

from gamspy import (Container, Set, Parameter, Variable,
                    Equation, Model, Sum, Sense, Domain, Ord)

from utils import (DataError, IncoherentDataError, mapping_creation,
                   map_list_control, excel_control, coherence_control)


SCRIPT_DIR = osp.dirname(__file__)
pd.options.mode.copy_on_write = True


def set_logging(log_path):
    logging.basicConfig(filename=log_path, filemode='w', force=True)  # , format='%(levelname)s:%(message)s')


def new_bed_alloc_simple(babies_list, old_beds_list, new_beds_list):
    """
    From an old allocation of babies in the neonat service,
    Give the new relevant allocation while capacity reduction.
    Take into accounts a new and an old list of beds.
    """
    # Model
    alloc_model = Container()

    # Set
    babies = Set(container=alloc_model, name="babies", description="babies")
    babies.setRecords(babies_list)

    all_beds_list = list(set(old_beds_list + new_beds_list + ['out']))
    all_beds = Set(container=alloc_model,
                    name="all_beds",
                    description="all beds")
    all_beds.setRecords(all_beds_list)    
    # Subset
    old_beds = Set(container=alloc_model,
                    domain=all_beds,
                    name="old_beds",
                    description="old beds")
    old_beds.setRecords(old_beds_list)

    new_beds = Set(container=alloc_model,
                    name="new_beds",
                    domain=all_beds,
                    description="new beds")
    new_beds.setRecords(new_beds_list)

    old_beds_kept = Set(container=alloc_model,
                         name="old_beds_kept",
                         domain=old_beds,
                         description="old beds kept for new configuration")
    old_beds_kept_list = [bed for bed in old_beds_list
                                if bed in new_beds_list]
    old_beds_kept.setRecords(old_beds_kept_list)
    
    new_places = Set(container=alloc_model,
                     name="new_places",
                    domain=all_beds,
                    description="new places")
    new_places.setRecords(new_beds_list + ['out'])
    
    old_alloc_list = [('bb1', 'r1'),
                          ('bb2', 'r2'),
                          ('bb3', 'r3'),
                          ('bb4', 'r4')]
    
    old_alloc_df = pd.Series(
        index=pd.MultiIndex.from_tuples(old_alloc_list)
    )

    map_old_alloc = Set(
        container=alloc_model,
        name='map_old_alloc',
        domain=[babies, old_beds],
        description='map the old beds to the babies',
        uels_on_axes=True,
        records=old_alloc_df,
    )

    # VARIABLES

    bin_baby_bed = Variable(
        container=alloc_model,
        name="BIN_BABY_bed",
        domain=[babies, all_beds],
        type="binary",
        description="binary variable which equals 1 if baby is in bed",
    )

    # EQUATIONS
    # Equation each baby has a bed

    eq_baby_has_bed = Equation(
        container=alloc_model,
        name="eq_baby_has_bed",
        domain=[babies],
        description="each baby needs a new bed or goes out"
    )

    eq_baby_has_bed[babies] = (Sum(new_places,
                                bin_baby_bed[babies, new_places])
                                == 1)

    # Equation each bed cannot have more babies than 1
    eq_bed = Equation(        
        container=alloc_model,
        name="eq_bed",
        domain=[new_places],
        description="each bed can have a baby or not"
    )
    
    eq_bed[new_places] = (Sum(babies, bin_baby_bed[babies, new_places])
                           <= 1)

    obj = Sum(map_old_alloc[babies, old_beds_kept],
              bin_baby_bed[babies, old_beds_kept])

    alloc_mod = Model(
        alloc_model,
        name="alloc_model",
        equations=[eq_baby_has_bed, eq_bed],
        problem="MIP",
        sense=Sense.MAX,
        objective=obj,
    )

    alloc_mod.solve()

    obj = alloc_mod.objective_value
    result = bin_baby_bed.records[['babies', 'all_beds', 'level']]
    alloc_babies_beds = result[result['level'] == 1][['babies', 'all_beds']]
    
    return alloc_babies_beds, obj


def read_input(input_path):
    """
    Read input specific for calc_bed_allocation.

    Data description :
    - services_list : a list containing service names ;
    - babies_list : a list containing babies id ;
    - babies_service_df : a list of tuples with all possible service a baby
        can go ;
    - old_beds_list : list of all the previous occupied beds
    - new_beds_list : list of all new beds (for instance, withdraw the one
        of the historical floor of a service if summer cleaning)
    - new_beds_service_df : all the services a bed can deliver
    - old_alloc_df : previous bed for each baby
    """
    xls_read = pd.ExcelFile(input_path)
    with xls_read as xls:
        valid_control = excel_control(xls)
        if not valid_control:
            raise AssertionError('The input Excel file has not the good column names.')
        # Service sheet
        services = {}
        services_sheet = pd.read_excel(xls, 'services')
        services['services_list'] = list(services_sheet['services'].drop_duplicates())

        # Babies sheet
        babies = {}
        babies_sheet = pd.read_excel(xls, 'babies')
        babies['babies_list'] = babies_sheet['babies'].drop_duplicates()
        babies_service_df = babies_sheet[['babies', 'babies_service']]
        babies_service_df['babies_service'] = babies_service_df['babies_service'].str.split(",")
        babies_service_df = babies_service_df.explode('babies_service')
        babies['babies_service_df'] = mapping_creation(babies_service_df)
        babies['old_alloc_df'] = mapping_creation(babies_sheet[['babies', 'old_alloc_list']])

        nan_treatment = babies_sheet['treatment'].fillna('no_treatment')
        babies_sheet['treatment'] = nan_treatment
        babies['babies_treatment_df'] = mapping_creation(babies_sheet[['babies', 'treatment']])

        # beds sheet
        beds = {}
        beds_sheet = pd.read_excel(xls, 'beds')
        beds['all_beds'] = beds_sheet['all_beds'].drop_duplicates()
        beds['new_beds'] = beds_sheet[
                                beds_sheet['new_beds'] == 'yes']['all_beds']
        beds['old_beds'] = beds_sheet[
                                beds_sheet['old_beds'] == 'yes']['all_beds']
        beds['going_out'] = beds_sheet[
                                beds_sheet['going_out'] == 'yes']['all_beds']

        new_beds_service_df = beds_sheet[['all_beds', 'new_beds_service']]
        new_beds_service_df['new_beds_service'] = new_beds_service_df['new_beds_service'].str.split(",")
        new_beds_service_df = new_beds_service_df.explode('new_beds_service')
        beds['new_beds_service_df'] = mapping_creation(new_beds_service_df)

        beds['beds_capacities_df'] = beds_sheet[['all_beds', 'beds_capacities']].dropna()
        beds['priority'] = beds_sheet[['all_beds', 'priority']].dropna()

        nan_treatment = beds_sheet['treatment'].fillna('no_treatment')
        beds_sheet['treatment_list'] = nan_treatment
        beds['treatment'] = beds_sheet['treatment_list'].drop_duplicates().dropna()

        # A bed with specific treatment can be assign to a baby without treatment
        bed_treatment_list = nan_treatment + ',no_treatment'
        beds_sheet['treatment'] = bed_treatment_list
        map_bed_treatment_df = beds_sheet[['all_beds', 'treatment']]
        map_bed_treatment_df['treatment'] = map_bed_treatment_df['treatment'].str.split(",")
        map_bed_treatment_df = map_bed_treatment_df.explode('treatment')
        beds['beds_treatment_df'] = mapping_creation(map_bed_treatment_df.drop_duplicates())

    return services, babies, beds


def calc_bed_allocation(services,
                         babies,
                         beds,
                         force=False):
    """
    From an old allocation of babies in the neonat service,
    Gives the new relevant allocation while the context may have changed.

    Inputs :
    - services : a dict containing services data ;
    - babies : a dict containing babies data ;
    - beds : a dict containing beds data ;

    TODO : control errors :
         - modelstatus/solvestatus,
    """
    # Model
    alloc_model = Container()

    # Load inputs
    ## Mapping control
    data_control = map_list_control(services, babies, beds)
    if not data_control and not force:
        raise DataError('There is some errors in your dataset mappings, please reconsider it.')

    ## Coherence control  
    data_coherence_control = coherence_control(services, babies, beds)
    if not data_coherence_control and not force:
        raise IncoherentDataError('There is a risk of unfeasability in your dataset, please reconsider it.')

    services_list = services['services_list']
    treatment_list = beds['treatment']

    babies_list = babies['babies_list']
    babies_service_df = babies['babies_service_df']
    old_alloc_df = babies['old_alloc_df']
    babies_treatment_df = babies['babies_treatment_df']

    all_beds_list = beds['all_beds']
    old_beds_list = beds['old_beds']
    new_beds_list = beds['new_beds']
    new_beds_service_df = beds['new_beds_service_df']
    beds_capacities_df = beds['beds_capacities_df']
    beds_treatment_df = beds['beds_treatment_df']

    # Services sets, maps and parameters
    services = Set(container=alloc_model,
                   name='services',
                   description='service')
    services.setRecords(services_list)

    # Treatment sets, maps and parameters
    treatment = Set(container=alloc_model,
                   name='treatment',
                   description='treatment')
    treatment.setRecords(treatment_list)

    # beds sets, maps and parameters
    all_beds = Set(container=alloc_model,
                    name="all_beds",
                    description="all beds")
    all_beds.setRecords(all_beds_list)

    ## Subset
    old_beds = Set(container=alloc_model,
                    domain=all_beds,
                    name="old_beds",
                    description="old beds")
    old_beds.setRecords(old_beds_list)

    new_beds = Set(container=alloc_model,
                    name="new_beds",
                    domain=all_beds,
                    description="new beds")
    new_beds.setRecords(new_beds_list)

    old_beds_kept = Set(container=alloc_model,
                         name="old_beds_kept",
                         domain=all_beds,
                         description="old beds kept for new configuration")
    old_beds_kept_list = old_beds_list[old_beds_list.isin(new_beds_list)]
    old_beds_kept.setRecords(old_beds_kept_list)

    new_places = Set(container=alloc_model,
                     name="new_places",
                     domain=all_beds,
                     description="new places")
    new_places_df = new_beds_list.copy().reset_index(drop=True)
    new_places_df.loc[len(new_places_df)] = 'out'
    new_places.setRecords(new_places_df)

    map_new_beds_service = Set(
        container=alloc_model,
        name='map_new_beds_service',
        domain=[new_places, services],
        description='map the service a bed belongs to',
        uels_on_axes=True,
        records=new_beds_service_df
    )

    beds_capacities = Parameter(
        container=alloc_model,
        name='beds_capacities',
        domain=[all_beds],
        description='beds number in each bed',
        records=beds_capacities_df
    )

    priority = Parameter(
        container=alloc_model,        
        name='beds_priority',
        domain=[all_beds],
        description='If a bed is subject to priority',
        records=beds['priority']
    )

    map_beds_treatment = Set(
        container=alloc_model,        
        name='map_beds_treatment',
        domain=[all_beds, treatment],
        description='If a bed allows a certain treatment',
        uels_on_axes=True,
        records=beds_treatment_df
    )

    # Babies sets, maps and parameters
    babies = Set(container=alloc_model, name="babies", description="babies")
    babies.setRecords(babies_list)

    map_babies_service = Set(
        container=alloc_model,
        name='map_babies_service',
        domain=[babies, services],
        description='map the possible service a baby can move to',
        uels_on_axes=True,
        records=babies_service_df
    )


    map_old_alloc = Set(
        container=alloc_model,
        name='map_old_alloc',
        domain=[babies, all_beds],
        description='map the old beds to the babies',
        uels_on_axes=True,
        records=old_alloc_df,
    )

    map_babies_treatment = Set(
        container=alloc_model,        
        name='map_babies_treatment',
        domain=[babies, treatment],
        description='If a baby needs a certain treatment',
        uels_on_axes=True,
        records=babies_treatment_df
    )

    # VARIABLES

    bin_baby_bed = Variable(
        container=alloc_model,
        name="BIN_BABY_BED",
        domain=[babies, all_beds],
        type="binary",
        description="binary variable which equals 1 if baby is in bed",
    )

    # EQUATIONS
    # Equation each baby has a bed with the the relevant service

    eq_baby_relevant_service = Equation(
        container=alloc_model,
        name="eq_baby_relevant_service",
        domain=[babies],
        description="each baby needs a new place with the relevant service"
    )

    eq_baby_relevant_service[babies] = (Sum(services,
                                            Sum((map_babies_service[babies, services],
                                                 map_new_beds_service[new_places, services]),
                                                bin_baby_bed[babies, new_places]
                                            )
                                        )
                                        == 1)

    # Equation each baby has a bed with the relevant treatment

    eq_baby_relevant_treatment = Equation(
        container=alloc_model,
        name="eq_baby_relevant_treatment",
        domain=[babies],
        description="each baby needs a new place with the relevant treatment"
    )

    eq_baby_relevant_treatment[babies] = (Sum(treatment,
                                            Sum((map_babies_treatment[babies, treatment],
                                                 map_beds_treatment[new_places, treatment]),
                                                bin_baby_bed[babies, new_places]
                                            )
                                        )
                                        == 1)

    # Equation a baby has only one bed

    eq_baby_one_bed = Equation(
        container=alloc_model,
        name="eq_baby_one_bed",
        domain=[babies],
        description="a baby should have only one bed"
    )

    eq_baby_one_bed[babies] = (Sum(all_beds,
                                    bin_baby_bed[babies, all_beds])
                                == 1)

    # Equation each bed cannot have more babies than its capacity
    eq_bed_capacity = Equation(
        container=alloc_model,
        name="eq_bed_capacity",
        domain=[new_beds],
        description="each bed have limited bed number"
    )

    eq_bed_capacity[new_beds] = (Sum(babies, bin_baby_bed[babies, new_beds])
                                   <= beds_capacities[new_beds])

    # OBJ : minimize the number of changes
    obj = (
        Sum(Domain(babies, all_beds).where[~map_old_alloc[babies, all_beds]],
            Sum((map_babies_service[[babies, services]],
                 map_new_beds_service[new_places[all_beds], services]),
                Ord(services)**priority[all_beds] * bin_baby_bed[babies, all_beds]
            )
        )
    )

    alloc_mod = Model(
        alloc_model,
        name="alloc_model",
        equations=alloc_model.getEquations(),
        problem="MIP",
        sense=Sense.MIN,
        objective=obj,
    )

    alloc_mod.solve()
    if alloc_mod.status.value > 2.0:
        raise ValueError((f'Problem is {alloc_mod.status.name}. '
                         'There might be a problem of data.'))

    obj = alloc_mod.objective_value
    result = bin_baby_bed.records[['babies', 'all_beds', 'level']]
    alloc_babies_beds = result[result['level'] == 1][['babies', 'all_beds']]

    # Add old alloc to result to visualize which babies has moved
    summary = alloc_babies_beds.merge(old_alloc_df.reset_index(),
                                       how='left',
                                       on='babies')

    summary = summary.drop(columns=[0])
    summary['move'] = summary['all_beds'] != summary['old_alloc_list']
    summary.columns = ['babies', 'new_place', 'old_place', 'should_move']
    return summary, obj


def write_output(xls_path, alloc_babies_beds):
    """
    Write results of babies allocation in excel.
    """
    with pd.ExcelWriter(xls_path) as writer:  
        alloc_babies_beds.to_excel(writer, sheet_name='babies_allocation')


def run_neonat():
    """
    From a scenario_name, run a scenario of new bed allocation.
    Scenario_name is the name of the folder,
    which include an Excel file "input.xls" to be read by the script.
    TODO : creer une fonction run_neonat_with_xls(scenario),
     puis une autre fonction qui appelle le parser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario_name')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    scenario_name = args.scenario_name
    force = args.force
    xls_input_path = osp.join(SCRIPT_DIR, 'scenarios', scenario_name,
                              'input_' + scenario_name + '.xlsx')
    xls_output_path = osp.join(SCRIPT_DIR, 'scenarios', scenario_name,
                               'output_' + scenario_name + '.xlsx')
    log_path = osp.join(SCRIPT_DIR, 'scenarios', scenario_name,
                        'log_' + scenario_name + '.log')

    set_logging(log_path=log_path)

    services, babies, beds = read_input(xls_input_path)

    result, obj = calc_bed_allocation(services, babies, beds, force)

    baby_move_nb = result['should_move'].sum()
    print(f'{baby_move_nb} out of {len(result)} babies should change beds.')
    print(result)
    ###
    print(f'obj fun is equal to {obj}')
    ###
    write_output(xls_output_path, result)


if __name__ == '__main__':
    run_neonat()
