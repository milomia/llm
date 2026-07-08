#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import re
import pytest
import pandas as pd
from datetime import datetime

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.tests.utils import get_wml_credentials
from ibm_watsonx_ai.parameter_sets import ParameterSetsMetaNames


class TestParameterSetsE2E:
    """
    These tests covers:
    - create parameter sets
    - update parameter sets
    - delete parameter sets
    """

    PARAMETER_SETS_NAME = "TestParameterSetsE2E"
    SPACE_ONLY = False

    wml_credentials = None
    project_id = None
    space_id = None

    @classmethod
    def setup_class(cls) -> None:
        """
        Load WML credentials from config.ini file based on ENV variable.
        """
        cls.wml_credentials = get_wml_credentials()
        cls.wml_client = APIClient(wml_credentials=cls.wml_credentials.copy())

        cls.project_id = cls.wml_credentials.get('project_id')

        # Create unique name for each test
        now = datetime.now()
        cls.PARAMETER_SETS_NAME += now.strftime(" %d/%m/%Y %H:%M:%S")

    def test_00_setup(self):

        if self.SPACE_ONLY:
            self.wml_client.set.default_space(self.space_id)
        else:
            self.wml_client.set.default_project(self.project_id)

    def test_01_create_parameter_sets(self):
        meta_props = {
            ParameterSetsMetaNames.NAME: self.PARAMETER_SETS_NAME,
            ParameterSetsMetaNames.DESCRIPTION: "example description",
            ParameterSetsMetaNames.PARAMETERS: [
                {
                    "name": "string",
                    "description": "string12",
                    "prompt": "string",
                    "type": "string",
                    "subtype": "string",
                    "value": "string",
                    "valid_values": [
                        "string"
                    ]
                }
            ],
            ParameterSetsMetaNames.VALUE_SETS: [
                {
                    "name": "string",
                    "values": [
                        {
                            "name": "string",
                            "value": "string"
                        }
                    ]
                }
            ]
        }
        create_details = self.wml_client.parameter_sets.create(meta_props)
        print(f"\ncreate_details:\n{create_details}")

        assert isinstance(create_details, dict), f"create_details type is {type(create_details)}, but should be dict"
        assert create_details["entity"]["parameter_set"] == meta_props, ("Created parameter set details is not the same"
                                                                         " with whom they were created")

    def test_02_get_id_by_name(self):

        pattern = re.compile(r'^[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}$')
        parameter_sets_id = self.wml_client.parameter_sets.get_id_by_name(self.PARAMETER_SETS_NAME)

        print(f"\nparameter_sets_id: {parameter_sets_id}")

        assert isinstance(parameter_sets_id, str), f"parameter_sets_id type is {type(parameter_sets_id)}, but should be str"
        assert pattern.match(parameter_sets_id), "Pattern of parameter_sets_id is not valid"

    def test_03_get_details(self):

        details = self.wml_client.parameter_sets.get_details()
        print(f"\ndetails:\n{details}")

        assert isinstance(details, dict), f"parameter_sets_id type is {type(details)}, but should be dict"

    def test_03a_get_details_with_parameter_set_id(self):

        parameter_sets_id = self.wml_client.parameter_sets.get_id_by_name(self.PARAMETER_SETS_NAME)
        details = self.wml_client.parameter_sets.get_details(parameter_sets_id)
        print(f"\ndetails:\n{details}")

        assert isinstance(details, dict), f"parameter_sets_id type is {type(details)}, but should be dict"

    def test_04_list(self):

        parameter_set_list = self.wml_client.parameter_sets.list()
        print(f"\nparameter_set_list:\n{parameter_set_list}")

        assert isinstance(parameter_set_list, pd.DataFrame), (f"parameter_set_list type is {type(parameter_set_list)}, "
                                                              f"but should be DataFrame")

    def test_10_update_parameters(self):
        new_parameters_data = [
            {
                "name": "string",
                "description": "new_string",
                "prompt": "new_string",
                "type": "new_string",
                "subtype": "new_string",
                "value": "new_string",
                "valid_values": [
                    "new_string"
                ]
            },
            {
                "name": "string1",
                "description": "new_string",
                "prompt": "new_string",
                "type": "new_string",
                "subtype": "new_string",
                "value": "new_string",
                "valid_values": [
                    "new_string"
                ]
            }
        ]
        parameter_sets_id = self.wml_client.parameter_sets.get_id_by_name(self.PARAMETER_SETS_NAME)
        updated_details = self.wml_client.parameter_sets.update(parameter_sets_id, new_parameters_data, "parameters")
        print(f"\nupdated_details:\n{updated_details}")

        assert isinstance(updated_details, dict), f"parameter_sets_id type is {type(updated_details)}, but should be dict"
        assert updated_details["entity"]["parameter_set"]["parameters"] == new_parameters_data, \
            "Updated parameters are not valid"

    def test_11_update_value_sets(self):
        new_value_sets_data = [
            {
                "name": "string",
                "values": [
                    {
                        "name": "string",
                        "value": "test_string"
                    }
                ]
            },
            {
                "name": "string_2",
                "values": [
                    {
                        "name": "string",
                        "value": "test_string_2"
                    }
                ]
            }
        ]
        parameter_sets_id = self.wml_client.parameter_sets.get_id_by_name(self.PARAMETER_SETS_NAME)
        updated_details = self.wml_client.parameter_sets.update(parameter_sets_id, new_value_sets_data, "value_sets")
        print(f"\nupdated_details:\n{updated_details}")

        assert isinstance(updated_details, dict), f"parameter_sets_id type is {type(updated_details)}, but should be dict"
        assert updated_details["entity"]["parameter_set"]["value_sets"] == new_value_sets_data, \
            "Updated value_sets are not valid"

    def test_90_delete_parameter_sets(self):

        parameter_sets_id = self.wml_client.parameter_sets.get_id_by_name(self.PARAMETER_SETS_NAME)
        result = self.wml_client.parameter_sets.delete(parameter_sets_id)
        print(f"\nresult:\n{result}")

        assert result == "SUCCESS", "result is not valid, should be SUCCESS"

    def test_91_check_if_deleted(self):
        expected_response = "Not Found"
        parameter_sets_id = self.wml_client.parameter_sets.get_id_by_name(self.PARAMETER_SETS_NAME)

        assert parameter_sets_id == expected_response, f"response is not valid, should be {expected_response}"
