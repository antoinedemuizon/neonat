# import sys
import os.path as osp
import pandas as pd
import argparse

from gamspy import (Container, Set, Parameter, Variable,
                    Alias, Equation, Model, Sum, Sense,
                    Domain, ModelStatus, Ord, Card)


SCRIPT_DIR = osp.dirname(__file__)


def new_room_alloc_simple(babies_list, old_rooms_list, new_rooms_list):
    """
    From an old allocation of babies in the neonat service,
    Give the new relevant allocation while capacity reduction.
    """
    # Model
    alloc_model = Container()

    # Set
    babies = Set(container=alloc_model, name="babies", description="babies")
    babies.setRecords(babies_list)

    all_rooms_list = list(set(old_rooms_list + new_rooms_list + ['out']))
    all_rooms = Set(container=alloc_model,
                    name="all_rooms",
                    description="all rooms")
    all_rooms.setRecords(all_rooms_list)    
    # Subset
    old_rooms = Set(container=alloc_model,
                    domain=all_rooms,
                    name="old_rooms",
                    description="old rooms")
    old_rooms.setRecords(old_rooms_list)

    new_rooms = Set(container=alloc_model,
                    name="new_rooms",
                    domain=all_rooms,
                    description="new rooms")
    new_rooms.setRecords(new_rooms_list)

    old_rooms_kept = Set(container=alloc_model,
                         name="old_rooms_kept",
                         domain=old_rooms,
                         description="old rooms kept for new configuration")
    old_rooms_kept_list = [room for room in old_rooms_list
                                if room in new_rooms_list]
    old_rooms_kept.setRecords(old_rooms_kept_list)
    
    new_places = Set(container=alloc_model,
                     name="new_places",
                    domain=all_rooms,
                    description="new places")
    new_places.setRecords(new_rooms_list + ['out'])
    
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
        domain=[babies, old_rooms],
        description='map the old rooms to the babies',
        uels_on_axes=True,
        records=old_alloc_df,
    )

    # VARIABLES

    bin_baby_room = Variable(
        container=alloc_model,
        name="BIN_BABY_ROOM",
        domain=[babies, all_rooms],
        type="binary",
        description="binary variable which equals 1 if baby is in room",
    )

    # EQUATIONS
    # Equation each baby has a room

    eq_baby_has_room = Equation(
        container=alloc_model,
        name="eq_baby_has_room",
        domain=[babies],
        description="each baby needs a new room or goes out"
    )

    eq_baby_has_room[babies] = (Sum(new_places,
                                bin_baby_room[babies, new_places])
                                == 1)

    # Equation each room cannot have more babies than 1
    eq_room = Equation(        
        container=alloc_model,
        name="eq_room",
        domain=[new_places],
        description="each room can have a baby or not"
    )
    
    eq_room[new_places] = (Sum(babies, bin_baby_room[babies, new_places])
                           <= 1)

    obj = Sum(map_old_alloc[babies, old_rooms_kept],
              bin_baby_room[babies, old_rooms_kept])

    alloc_mod = Model(
        alloc_model,
        name="alloc_model",
        equations=[eq_baby_has_room, eq_room],
        problem="MIP",
        sense=Sense.MAX,
        objective=obj,
    )

    alloc_mod.solve()

    obj = alloc_mod.objective_value
    result = bin_baby_room.records[['babies', 'all_rooms', 'level']]
    alloc_babies_rooms = result[result['level'] == 1][['babies', 'all_rooms']]
    
    return alloc_babies_rooms, obj


def read_input(input_path):
    """
    Read input specific for new_room_alloc_cplx.
    TODO : refactorer creation df mapping : pd.series(index=pd.MultiIndex.from_frame)
    """
    xls_read = pd.ExcelFile(input_path)
    with xls_read as xls:
        # Service sheet
        services = {}
        services_sheet = pd.read_excel(xls, 'services')
        services['services_list'] = list(services_sheet['services'].drop_duplicates())

        # Babies sheet
        babies = {}
        babies_sheet = pd.read_excel(xls, 'babies')
        babies['babies_list'] = list(babies_sheet['babies'].drop_duplicates())
        babies_potential_df = babies_sheet[['babies', 'babies_potential']]
        babies_potential_df['babies_potential'] = babies_potential_df['babies_potential'].str.split(",")
        babies_potential_df = babies_potential_df.explode('babies_potential')
        babies['babies_potential_df'] = pd.Series(
            index=pd.MultiIndex.from_frame(babies_potential_df)
        )
        babies['old_alloc_df'] = pd.Series(
            index=pd.MultiIndex.from_frame(babies_sheet[['babies', 'old_alloc_list']]).drop_duplicates()
        )

        # Rooms sheet
        rooms = {}
        rooms_sheet = pd.read_excel(xls, 'rooms')
        rooms['all_rooms'] = list(rooms_sheet['all_rooms'].drop_duplicates())
        rooms['new_rooms'] = list(rooms_sheet[
                                rooms_sheet['new_rooms'] == 'yes']['all_rooms'])
        rooms['old_rooms'] = list(rooms_sheet[
                                rooms_sheet['old_rooms'] == 'yes']['all_rooms'])
        rooms['going_out'] = list(rooms_sheet[
                                rooms_sheet['going_out'] == 'yes']['all_rooms'])

        new_rooms_service_df = rooms_sheet[['all_rooms', 'new_rooms_service']]
        new_rooms_service_df['new_rooms_service'] = new_rooms_service_df['new_rooms_service'].str.split(",")
        new_rooms_service_df = new_rooms_service_df.explode('new_rooms_service')

        new_rooms_service_df = pd.MultiIndex.from_frame(new_rooms_service_df.dropna())
        rooms['new_rooms_service_df'] = pd.Series(index=new_rooms_service_df)
        rooms['rooms_capacities_df'] = rooms_sheet[['all_rooms', 'rooms_capacities']].dropna()

    return services, babies, rooms


def new_room_alloc_cplx(services,
                        babies,
                        rooms):
    """
    From an old allocation of babies in the neonat service,
    Give the new relevant allocation while room number reduces services includes
    new rooms list.

    Inputs :
    - services_list : a list containing service names ;
    - babies_list : a list containing babies id ;
    - babies_potential_df : a list of tuples with all possible service a baby
        can go ;
    - old_rooms_list : list of all the previous occupied rooms
    - new_rooms_list : list of all new rooms (for instance, withdraw the one
        of the historical floor of a service if summer cleaning)
    - new_rooms_service_df : all the services a room can deliver
    - old_alloc_df : previous room for each baby

    TODO : input uniquement l'output de read_input() -> donne directement acces
        all_rooms par ex
    TODO : adapt the test to excel input
    TODO : set can be fed with pd.Series -> retirer "list()"
    TODO : add soin dimension : map(bb, required_soin) +
    map(room, possible_soin)
    TODO (pas obligé) : control equivalent solutions (or find a way to show them all) ;
    TODO : control errors :
         - inputs : induire des erreurs (mismatch orthographe set/map,
            mismatch taille des parametres, ...)
            Par exemple : si nb_bed < nb bebe not going out
         - modelstatus/solvestatus,
    """
    # Model
    alloc_model = Container()

    # Load inputs
    services_list=services['services_list']
    babies_list=babies['babies_list']
    babies_potential_df=babies['babies_potential_df']
    old_rooms_list=rooms['old_rooms']
    new_rooms_list=rooms['new_rooms']
    new_rooms_service_df=rooms['new_rooms_service_df']
    rooms_capacities_df=rooms['rooms_capacities_df']
    old_alloc_df=babies['old_alloc_df']

    # Set
    # Services
    services = Set(container=alloc_model,
                   name='services',
                   description='service')
    services.setRecords(services_list)

    # Rooms sets and maps
    all_rooms_list = dict.fromkeys(old_rooms_list + new_rooms_list + ['out'])
    all_rooms = Set(container=alloc_model,
                    name="all_rooms",
                    description="all rooms")
    all_rooms.setRecords(list(all_rooms_list.keys()))    

    # Subset
    old_rooms = Set(container=alloc_model,
                    domain=all_rooms,
                    name="old_rooms",
                    description="old rooms")
    old_rooms.setRecords(old_rooms_list)

    new_rooms = Set(container=alloc_model,
                    name="new_rooms",
                    domain=all_rooms,
                    description="new rooms")
    new_rooms.setRecords(new_rooms_list)

    old_rooms_kept = Set(container=alloc_model,
                         name="old_rooms_kept",
                         domain=old_rooms,
                         description="old rooms kept for new configuration")
    old_rooms_kept_list = [room for room in old_rooms_list
                                if room in new_rooms_list]
    old_rooms_kept.setRecords(old_rooms_kept_list)
    
    new_places = Set(container=alloc_model,
                     name="new_places",
                     domain=all_rooms,
                     description="new places")
    new_places.setRecords(new_rooms_list + ['out'])

    map_new_rooms_service = Set(
        container=alloc_model,
        name='map_new_rooms_service',
        domain=[new_places, services],
        description='map the service a room belongs to',
        uels_on_axes=True,
        records=new_rooms_service_df
    )

    rooms_capacities = Parameter(
        container=alloc_model,
        name='rooms_capacities',
        domain=[all_rooms],
        description='beds number in each room',
        records=rooms_capacities_df
    )

    # Babies sets and maps
    babies = Set(container=alloc_model, name="babies", description="babies")
    babies.setRecords(babies_list)

    map_babies_potential = Set(
        container=alloc_model,
        name='map_babies_potential',
        domain=[babies, services],
        description='map the possible service a baby can move to',
        uels_on_axes=True,
        records=babies_potential_df
    )


    map_old_alloc = Set(
        container=alloc_model,
        name='map_old_alloc',
        domain=[babies, old_rooms],
        description='map the old rooms to the babies',
        uels_on_axes=True,
        records=old_alloc_df,
    )

    # VARIABLES

    bin_baby_room = Variable(
        container=alloc_model,
        name="BIN_BABY_ROOM",
        domain=[babies, all_rooms],
        type="binary",
        description="binary variable which equals 1 if baby is in room",
    )
    
    distance_btw_rooms = Variable(
        container=alloc_model,
        name="DISTANCE_BTW_ROOMS",
        domain=[babies],
        type='integer',
        description='distance between the old and the new room of a baby'
    )

    # EQUATIONS
    # Equation each baby has a room

    eq_baby_has_room = Equation(
        container=alloc_model,
        name="eq_baby_has_room",
        domain=[babies],
        description="each baby needs a new room or goes out"
    )

    # Baby can only be in a room with the relevant service : 
    eq_baby_has_room[babies] = (Sum(services,
                                    Sum((map_babies_potential[babies, services],
                                     map_new_rooms_service[new_places, services]),
                                bin_baby_room[babies, new_places]))
                                == 1)


    # Equation each room cannot have more babies than 1
    eq_room_capacity = Equation(
        container=alloc_model,
        name="eq_room_capacity",
        domain=[new_rooms],
        description="each room have limited bed number"
    )

    eq_room_capacity[new_rooms] = (Sum(babies, bin_baby_room[babies, new_rooms])
                                   <= rooms_capacities[new_rooms])

    # Defines baby move distance with distance_btw_rooms
    eq_baby_move_distance = Equation(        
        container=alloc_model,
        name="eq_baby_move_distance",
        domain=[babies],
        description="defines the distance between old and new baby room"
    )

    ################# TEST : add penalty distance ###########################
    eq_baby_move_distance[babies] = (distance_btw_rooms[babies]
                                     == Sum(
                                         map_old_alloc[babies, old_rooms],
                                         Ord(old_rooms)/len(all_rooms))
                                        #  - Sum(new_places,
                                        #         # bin_baby_room[babies, new_places]
                                        #         Ord(new_places))
                                        )

    # import pdb ; pdb.set_trace()
                                        #  Sum(map_old_alloc[babies, old_rooms],
                                        #          Ord(old_rooms)))

    ###################### End Test #####################################
    # OBJ : add a penalty if room ord is too far from previous one
    # TODO : add an option for this penalty ?
    obj = (
        Sum(map_old_alloc[babies, old_rooms_kept],
               bin_baby_room[babies, old_rooms_kept])
        # -
        # Sum(babies, distance_btw_rooms[babies])
        )
    
    list_of_eq = [eq_baby_has_room, eq_room_capacity]
    # if True:
    #     list_of_eq.append(eq_baby_move_distance)

    alloc_mod = Model(
        alloc_model,
        name="alloc_model",
        equations=list_of_eq,
        # equations=[eq_baby_has_room, eq_room_capacity, eq_baby_move_distance],
        problem="MIP",
        sense=Sense.MAX,
        objective=obj,
    )

    alloc_mod.solve()  # output=sys.stdout)
    if alloc_mod.status.value > 2.0:
        # TODO : realize more control on model coherence.
        # Exemple : controler le nb de chambres rea + nb d'eft rea ; vérifier chambres hybrides
        raise ValueError((f'Problem is {alloc_mod.status.name}. '
                         'There might be a problem of data.'))

    obj = alloc_mod.objective_value
    result = bin_baby_room.records[['babies', 'all_rooms', 'level']]
    alloc_babies_rooms = result[result['level'] == 1][['babies', 'all_rooms']]

    # Add old alloc to result to visualize which babies has moved
    summary = alloc_babies_rooms.merge(old_alloc_df.reset_index(),
                                       how='left',
                                       on='babies')
    summary = summary.drop(columns=[0])
    summary['move'] = summary['all_rooms'] != summary['old_alloc_list']
    summary.columns = ['babies', 'new_place', 'old_place', 'should_move']
    return summary, obj


def write_output(xls_path, alloc_babies_rooms):
    """
    Write results of babies allocation in excel.
    """
    with pd.ExcelWriter(xls_path) as writer:  
        alloc_babies_rooms.to_excel(writer, sheet_name='babies_allocation')


def run_neonat():
    """
    From a scenario_name, run a scenario of new room allocation.
    Scenario_name is the name of the folder,
    which include an Excel file "input.xls" to be read by the script.
    TODO : creer une fonction run_neonat_with_xls(scenario),
     puis une autre fonction qui appelle le parser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario_name')
    args = parser.parse_args()

    scenario_name = args.scenario_name
    xls_input_path = osp.join(SCRIPT_DIR, 'scenarios', scenario_name,
                              'input_' + scenario_name + '.xlsx')
    xls_output_path = osp.join(SCRIPT_DIR, 'scenarios', scenario_name,
                               'output_' + scenario_name + '.xlsx')

    services, babies, rooms = read_input(xls_input_path)

    result, obj = new_room_alloc_cplx(services, babies, rooms)

    print(obj)
    print(result)
    write_output(xls_output_path, result)


if __name__ == '__main__':
    run_neonat()