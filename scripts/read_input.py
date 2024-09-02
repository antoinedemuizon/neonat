import os.path as osp
import pandas as pd
import logging

from scripts.utils import mapping_creation, assert_map_in_set, count_element
from scripts.exc import DataError, IncoherentDataError


SCRIPT_DIR = osp.dirname(__file__)
pd.options.mode.copy_on_write = True


class ReadInput():

    def __init__(self, input_path=None, force=False):
        self.input_path = input_path
        self.is_valid = True
        self.xls_pd_df = 0
        self.dico_columns = {
            'services': ['services'],
            'babies': ['babies', 'babies_service', 'old_alloc_list', 'treatment'],
            'beds': ['all_beds', 'new_beds', 'old_beds', 'going_out',
                    'new_beds_service','old_beds_service', 'beds_capacities',
                    'priority', 'treatment']
        }
        self.services_data = {}
        self.babies_data = {}
        self.beds_data = {}
        self.force = force

    def read_input_from_excel(self):
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
        self.xls_pd_df = pd.ExcelFile(self.input_path)
        with self.xls_pd_df as xls:
            self.excel_format_control()
            if not self.is_valid:
                raise AssertionError('The input Excel file has not the good column names.')
            # Service sheet
            services_sheet = pd.read_excel(xls, 'services')
            self.services_data['services_list'] = list(services_sheet['services'].drop_duplicates())

            # Babies sheet
            babies_sheet = pd.read_excel(xls, 'babies')
            self.babies_data['babies_list'] = babies_sheet['babies'].drop_duplicates()
            babies_service_df = babies_sheet[['babies', 'babies_service']]
            babies_service_df['babies_service'] = babies_service_df['babies_service'].str.split(",")
            babies_service_df = babies_service_df.explode('babies_service')
            self.babies_data['babies_service_df'] = mapping_creation(babies_service_df)
            self.babies_data['old_alloc_df'] = mapping_creation(babies_sheet[['babies', 'old_alloc_list']])

            nan_treatment = babies_sheet['treatment'].fillna('no_treatment')
            babies_sheet['treatment'] = nan_treatment
            self.babies_data['babies_treatment_df'] = mapping_creation(babies_sheet[['babies', 'treatment']])

            # beds sheet
            beds_sheet = pd.read_excel(xls, 'beds')
            self.beds_data['all_beds'] = beds_sheet['all_beds'].drop_duplicates()
            self.beds_data['new_beds'] = beds_sheet[
                                    beds_sheet['new_beds'] == 'yes']['all_beds']
            self.beds_data['old_beds'] = beds_sheet[
                                    beds_sheet['old_beds'] == 'yes']['all_beds']
            self.beds_data['going_out'] = beds_sheet[
                                    beds_sheet['going_out'] == 'yes']['all_beds']

            new_beds_service_df = beds_sheet[['all_beds', 'new_beds_service']]
            new_beds_service_df['new_beds_service'] = new_beds_service_df['new_beds_service'].str.split(",")
            new_beds_service_df = new_beds_service_df.explode('new_beds_service')
            self.beds_data['new_beds_service_df'] = mapping_creation(new_beds_service_df)

            self.beds_data['beds_capacities_df'] = beds_sheet[['all_beds', 'beds_capacities']].dropna()
            self.beds_data['priority'] = beds_sheet[['all_beds', 'priority']].dropna()

            nan_treatment = beds_sheet['treatment'].fillna('no_treatment')
            beds_sheet['treatment_list'] = nan_treatment
            self.beds_data['treatment'] = beds_sheet['treatment_list'].drop_duplicates().dropna()

            # A bed with specific treatment can be assign to a baby without treatment
            bed_treatment_list = nan_treatment + ',no_treatment'
            beds_sheet['treatment'] = bed_treatment_list
            map_bed_treatment_df = beds_sheet[['all_beds', 'treatment']]
            map_bed_treatment_df['treatment'] = map_bed_treatment_df['treatment'].str.split(",")
            map_bed_treatment_df = map_bed_treatment_df.explode('treatment')
            self.beds_data['beds_treatment_df'] = mapping_creation(map_bed_treatment_df.drop_duplicates())
        self.map_list_control()
        self.coherence_control()

    def excel_format_control(self): 
        """
        Control xls_file tabs and columns names.
        """
        xls_file = self.input_path
        # With a parse_header function which read structure in a "general sheet", no need of this

        validation_tab_names = all(ele in self.xls_pd_df.sheet_names
                                   for ele in self.dico_columns.keys())
        if not validation_tab_names:
            logging.error('Error in Excel Worksheet names.'
                          ' You should have 3 worksheets : "babies", "beds" and "services".')
            self.is_valid = False

        for key in self.dico_columns.keys():
            columns_ds = pd.Series(self.dico_columns[key])
            xls_file_df = pd.read_excel(xls_file, key)
            xls_file_col = xls_file_df.columns
            validation_col_names = all(columns_ds.isin(xls_file_col))
            if not validation_col_names:
                logging.error(f'Error in the column names of the tab ***{key}*** (line 1 of the sheet).')
                self.is_valid = False

        if not self.is_valid and not self.force:
            raise DataError('There is some errors in your dataset mappings, please reconsider it.')

    def map_list_control(self):
        """
        Several inputs we check to ensure the proper use of the tool:
        Ensure the gams objects mapping have no more data than their corresponding sets.
        """

        # Check mapping
        ## Babies should not pretend to a service that is not declared in sheet "services"
        babypot = self.babies_data['babies_service_df']
        srvc = self.services_data['services_list']
        self.is_valid = assert_map_in_set(self.is_valid, babypot, 'babies_service', srvc)

        ## Babies should not have an old bed that is not declared in sheet "beds"
        bboldalloc = self.babies_data['old_alloc_df']
        allr = self.beds_data['all_beds']
        self.is_valid = assert_map_in_set(self.is_valid, bboldalloc, 'old_alloc_list', allr)

        ## Babies should not have an treatment that is not declared in sheet "beds"
        bbtreat = self.babies_data['babies_treatment_df']
        alltreat = self.beds_data['treatment']
        self.is_valid = assert_map_in_set(self.is_valid, bbtreat, 'treatment', alltreat)

        ## beds should not have an treatment that is not declared in sheet "beds"
        bedsrvc = self.beds_data['new_beds_service_df']
        srvc = self.services_data['services_list']
        self.is_valid = assert_map_in_set(self.is_valid, bedsrvc, 'new_beds_service', srvc)

        # Tuple ('svc', 'treatment') for babies should be in the one of beds
        map_svc_treat_bb = pd.concat([bbtreat.reset_index(),
                                        babypot.reset_index()],
                                        axis=1
                                    )[['babies_service', 'treatment']].drop_duplicates()
        map_svc_treat_rm = pd.concat([bedsrvc.reset_index(),
                                self.beds_data['beds_treatment_df'].reset_index()],
                                axis=1)[['new_beds_service', 'treatment']].drop_duplicates()
        d1 = pd.MultiIndex.from_frame(map_svc_treat_bb.dropna())
        d2 = pd.MultiIndex.from_frame(map_svc_treat_rm.dropna())

        validation_svc_treat = d1.isin(d2)
        if not validation_svc_treat.all():
            logging.warning("Be careful, the pairs ('service', 'treatment') >>>"
                            f" {d1[~validation_svc_treat].to_list()} "
                            "<<< do not exist in beds data."
                            )
            self.is_valid = False

        if not self.is_valid and not self.force:
            raise DataError('There is some errors in your dataset mappings, please reconsider it.')

    def coherence_control(self):
        """
        Several inputs we check to ensure the proper use of the tool:
        check if there is risk of unfeasibility.
        """

        # Incoherence in total nb of beds
        bed_capacities = self.beds_data['beds_capacities_df']
        new_beds = self.beds_data['new_beds']
        new_beds_capa = bed_capacities[bed_capacities['all_beds'].isin(new_beds)]
        tot_new_beds_capa = new_beds_capa['beds_capacities'].sum()

        bb_rm_pot_index = self.babies_data['babies_service_df'].index
        mask_babies_bed_potential = ~bb_rm_pot_index.get_level_values('babies_service').isin(['leave_hospital'])
        tot_baby_need = len(bb_rm_pot_index[mask_babies_bed_potential])

        # More precisely :
        count_beds_per_svc = count_element(self.beds_data['new_beds_service_df'],
                                            'all_beds', 'new_beds_service')
        count_bb_per_svc = count_element(self.babies_data['babies_service_df'],
                                        'babies', 'babies_service')
        count_bb_per_svc.sort_index(inplace=True)

        compare_tot = count_bb_per_svc - count_beds_per_svc > 0
        compare = count_bb_per_svc - count_beds_per_svc >= 1

        if tot_baby_need > tot_new_beds_capa:
            logging.warning('Be careful, not enough beds in '
                            f'{compare_tot[compare_tot].index.to_list()} service(s).')
            self.is_valid = False

        elif compare.any():
            logging.warning('Be careful, enough total nb of beds, but not enough beds'
                            f' in {compare[compare].index.to_list()} service(s).')
            self.is_valid = False

        if not self.is_valid and not self.force:
            raise IncoherentDataError('There is a risk of unfeasability in your dataset,'
                                      ' please reconsider it.')


if __name__ == "__main__":
    input_path = osp.join(SCRIPT_DIR, 'tests', 'nrt1',
                              'input_' + 'nrt1' + '.xlsx')
    bed_alloc_dataset = ReadInput(input_path)
    bed_alloc_dataset.read_input_from_excel()
    print(bed_alloc_dataset.services_data)
    print(bed_alloc_dataset.babies_data)
    print(bed_alloc_dataset.beds_data)

