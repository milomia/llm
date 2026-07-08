#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from ibm_watsonx_ai.helpers.connections import DataConnection, S3Location
from ibm_watsonx_ai.wml_client_error import WMLClientError
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes
from ibm_watsonx_ai.tests.foundation_models.abstract_tests_classes import AbstractTestPromptTuning
from ibm_watsonx_ai.tests.utils import create_connection_to_cos, is_cp4d


@unittest.skipIf(is_cp4d(), "Connected Asset for Prompt Tuning type is not supported on CP4D")
class TestPromptTuning(AbstractTestPromptTuning, unittest.TestCase):
    """
    The test can be run on Cloud and CPD
    """

    data_location = './foundation_models/data/file_to_tune1.json'
    SPACE_ONLY = True

    PROMPT_TUNING_NAME = "SDK test Classification with COS Connected Asset"

    connection_id = None
    data_cos_path = "data/file_to_tune1.json"
    results_cos_path = 'results_wml_prompt_tuning'

    prompt_tuning_info = dict(
        name="SDK test Classification with COS Connected Asset",
        task_id="generation",
        base_model=ModelTypes.GRANITE_13B_INSTRUCT_V2,
        num_epochs=3
    )

    def test_00b_prepare_COS_instance_and_connection(self):
        TestPromptTuning.connection_id, TestPromptTuning.bucket_name = create_connection_to_cos(
            wml_client=self.wml_client,
            cos_credentials=self.cos_credentials,
            cos_endpoint=self.cos_endpoint,
            bucket_name=self.bucket_name,
            save_data=True,
            data_path=self.data_location,
            data_cos_path=self.data_cos_path)

        self.assertIsInstance(self.connection_id, str)

    def test_02_data_reference_setup(self):
        TestPromptTuning.train_data_connections = [DataConnection(
            connection_asset_id=self.connection_id,
            location=S3Location(
                bucket=self.bucket_name,
                path=self.data_cos_path
            )
        )]
        TestPromptTuning.results_data_connection = DataConnection(
            connection_asset_id=self.connection_id,
            location=S3Location(
                bucket=self.bucket_name,
                path=self.results_cos_path
            )
        )

        self.assertEqual(len(TestPromptTuning.train_data_connections), 1)
        self.assertIsNotNone(obj=TestPromptTuning.results_data_connection)

    def test_02a_read_saved_remote_data_before_fit(self):
        self.train_data_connections[0].set_client(self.wml_client)
        data = self.train_data_connections[0].read(raw=True, binary=True)

        self.assertIsInstance(data, bytes)

    def test_25_read_results_reference_filename(self):
        parameters = self.prompt_tuner.get_run_details()
        print(parameters)

        self.assertIsNotNone(parameters)
        self.assertEqual(parameters['entity']['results_reference']['location']['file_name'], self.results_cos_path)

    def test_99_delete_connection_and_connected_data_asset(self):
        if not self.SPACE_ONLY:
            self.wml_client.set.default_project(self.project_id)
        self.wml_client.connections.delete(self.connection_id)

        with self.assertRaises(WMLClientError):
            self.wml_client.connections.get_details(self.connection_id)


if __name__ == '__main__':
    unittest.main()
