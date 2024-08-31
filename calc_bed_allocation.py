import os.path as osp
import pandas as pd
import logging

from gamspy import (Container, Set, Parameter, Variable,
                    Equation, Model, Sum, Sense, Domain, Ord)

from read_input import ReadInput


SCRIPT_DIR = osp.dirname(__file__)
pd.options.mode.copy_on_write = True


class CalcBedAllocation():

    def __init__(self, inputs: ReadInput, output_path=None):
        self.inputs = inputs
        self.output_path = output_path
        self.result_summary = 0
        self.obj = 0
        self.alloc_model = Container()

    def declare_model(self):
        """
        From an old allocation of babies in the neonat service,
        Gives the new relevant allocation while the context may have changed.

        Inputs :
        - services : a dict containing services data ;
        - babies : a dict containing babies data ;
        - beds : a dict containing beds data ;
        """
        read_input = self.inputs

        services_list = read_input.services_data['services_list']

        babies_list = read_input.babies_data['babies_list']
        babies_service_df = read_input.babies_data['babies_service_df']
        old_alloc_df = read_input.babies_data['old_alloc_df']
        babies_treatment_df = read_input.babies_data['babies_treatment_df']

        all_beds_list = read_input.beds_data['all_beds']
        old_beds_list = read_input.beds_data['old_beds']
        new_beds_list = read_input.beds_data['new_beds']
        new_beds_service_df = read_input.beds_data['new_beds_service_df']
        beds_capacities_df = read_input.beds_data['beds_capacities_df']
        treatment_list = read_input.beds_data['treatment']
        beds_treatment_df = read_input.beds_data['beds_treatment_df']
        beds_priority = read_input.beds_data['priority']

        # Services sets, maps and parameters
        services = Set(container=self.alloc_model,
                       name='services',
                       description='service')
        services.setRecords(services_list)

        # Treatment sets, maps and parameters
        treatment = Set(container=self.alloc_model,
                    name='treatment',
                    description='treatment')
        treatment.setRecords(treatment_list)

        # beds sets, maps and parameters
        all_beds = Set(container=self.alloc_model,
                        name="all_beds",
                        description="all beds")
        all_beds.setRecords(all_beds_list)

        ## Subset
        old_beds = Set(container=self.alloc_model,
                        domain=all_beds,
                        name="old_beds",
                        description="old beds")
        old_beds.setRecords(old_beds_list)

        new_beds = Set(container=self.alloc_model,
                        name="new_beds",
                        domain=all_beds,
                        description="new beds")
        new_beds.setRecords(new_beds_list)

        old_beds_kept = Set(container=self.alloc_model,
                            name="old_beds_kept",
                            domain=all_beds,
                            description="old beds kept for new configuration")
        old_beds_kept_list = old_beds_list[old_beds_list.isin(new_beds_list)]
        old_beds_kept.setRecords(old_beds_kept_list)

        new_places = Set(container=self.alloc_model,
                        name="new_places",
                        domain=all_beds,
                        description="new places")
        new_places_df = new_beds_list.copy().reset_index(drop=True)
        new_places_df.loc[len(new_places_df)] = 'out'
        new_places.setRecords(new_places_df)

        map_new_beds_service = Set(
            container=self.alloc_model,
            name='map_new_beds_service',
            domain=[new_places, services],
            description='map the service a bed belongs to',
            uels_on_axes=True,
            records=new_beds_service_df
        )

        beds_capacities = Parameter(
            container=self.alloc_model,
            name='beds_capacities',
            domain=[all_beds],
            description='beds number in each bed',
            records=beds_capacities_df
        )

        priority = Parameter(
            container=self.alloc_model,        
            name='beds_priority',
            domain=[all_beds],
            description='If a bed is subject to priority',
            records=beds_priority
        )

        map_beds_treatment = Set(
            container=self.alloc_model,        
            name='map_beds_treatment',
            domain=[all_beds, treatment],
            description='If a bed allows a certain treatment',
            uels_on_axes=True,
            records=beds_treatment_df
        )

        # Babies sets, maps and parameters
        babies = Set(container=self.alloc_model, name="babies", description="babies")
        babies.setRecords(babies_list)

        map_babies_service = Set(
            container=self.alloc_model,
            name='map_babies_service',
            domain=[babies, services],
            description='map the possible service a baby can move to',
            uels_on_axes=True,
            records=babies_service_df
        )


        map_old_alloc = Set(
            container=self.alloc_model,
            name='map_old_alloc',
            domain=[babies, all_beds],
            description='map the old beds to the babies',
            uels_on_axes=True,
            records=old_alloc_df,
        )

        map_babies_treatment = Set(
            container=self.alloc_model,        
            name='map_babies_treatment',
            domain=[babies, treatment],
            description='If a baby needs a certain treatment',
            uels_on_axes=True,
            records=babies_treatment_df
        )

        # VARIABLES

        bin_baby_bed = Variable(
            container=self.alloc_model,
            name="BIN_BABY_BED",
            domain=[babies, all_beds],
            type="binary",
            description="binary variable which equals 1 if baby is in bed",
        )

        # EQUATIONS
        # Equation each baby has a bed with the relevant service

        eq_baby_relevant_service = Equation(
            container=self.alloc_model,
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
            container=self.alloc_model,
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
            container=self.alloc_model,
            name="eq_baby_one_bed",
            domain=[babies],
            description="a baby should have only one bed"
        )

        eq_baby_one_bed[babies] = (Sum(all_beds,
                                        bin_baby_bed[babies, all_beds])
                                    == 1)

        # Equation each bed cannot have more babies than its capacity
        eq_bed_capacity = Equation(
            container=self.alloc_model,
            name="eq_bed_capacity",
            domain=[new_beds],
            description="each bed have limited bed number"
        )

        eq_bed_capacity[new_beds] = (Sum(babies, bin_baby_bed[babies, new_beds])
                                    <= beds_capacities[new_beds])

        # OBJ : minimize the number of changes
        self.obj = (
            Sum(Domain(babies, all_beds).where[~map_old_alloc[babies, all_beds]],
                Sum((map_babies_service[[babies, services]],
                    map_new_beds_service[new_places[all_beds], services]),
                    Ord(services)**priority[all_beds] * bin_baby_bed[babies, all_beds]
                )
            )
        )

    def run_model(self):
        """
        
        """
        alloc_mod = Model(
            self.alloc_model,
            name="alloc_model",
            equations=self.alloc_model.getEquations(),
            problem="MIP",
            sense=Sense.MIN,
            objective=self.obj,
        )

        alloc_mod.solve()
        if alloc_mod.status.value > 2.0:
            raise ValueError((f'Problem is {alloc_mod.status.name}. '
                            'There might be a problem of data.'))

        self.obj = alloc_mod.objective_value
        result = self.alloc_model['BIN_BABY_BED'].records[['babies', 'all_beds', 'level']]
        alloc_babies_beds = result[result['level'] == 1][['babies', 'all_beds']]

        # Add old alloc to result to visualize which babies has moved
        old_alloc_df = self.inputs.babies_data['old_alloc_df']
        self.result_summary = alloc_babies_beds.merge(old_alloc_df.reset_index(),
                                               how='left',
                                               on='babies')

        self.result_summary = self.result_summary.drop(columns=[0])
        self.result_summary['move'] = self.result_summary['all_beds'] != self.result_summary['old_alloc_list']
        self.result_summary.columns = ['babies', 'new_place', 'old_place', 'should_move']

    def write_output(self):
        """
        Write results of babies allocation in excel.
        """
        with pd.ExcelWriter(self.output_path) as writer:  
            self.result_summary.to_excel(writer, sheet_name='babies_allocation')


if __name__ == "__main__":
    input_path = osp.join(SCRIPT_DIR, 'tests', 'nrt1',
                              'input_' + 'nrt1' + '.xlsx')
    outputpath = osp.join(SCRIPT_DIR, 'tests', 'nrt1',
                              'test_output_' + 'nrt1' + '.xlsx')
    bed_alloc_dataset = ReadInput(input_path)
    bed_alloc_dataset.read_input_from_excel()
    bed_alloc_scenario = CalcBedAllocation(
        inputs=bed_alloc_dataset,
        output_path=outputpath
    )
    bed_alloc_scenario.declare_model()
    bed_alloc_scenario.run_model()
    bed_alloc_scenario.write_output()
    print(bed_alloc_scenario.result_summary)
    print(bed_alloc_scenario.obj)
