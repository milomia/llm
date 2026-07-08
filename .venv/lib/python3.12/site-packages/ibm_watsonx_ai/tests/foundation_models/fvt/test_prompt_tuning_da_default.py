#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from ibm_watsonx_ai.helpers.connections import DataConnection
from ibm_watsonx_ai.wml_client_error import WMLClientError
from ibm_watsonx_ai.foundation_models.utils.enums import PromptTuningTypes
from ibm_watsonx_ai.tests.foundation_models.abstract_tests_classes import AbstractTestPromptTuning
from ibm_watsonx_ai.tests.utils.utils import set_wml_client_default_space_wrapper


class TestPromptTuning(AbstractTestPromptTuning, unittest.TestCase):
    """
    The test can be run on Cloud and CPD
    """

    data_location = './foundation_models/data/file_to_tune1.json'
    SPACE_ONLY = False

    PROMPT_TUNING_NAME = "SDK test Classification"
    deployment_id = None

    prompt_tuning_info = dict(
        name="SDK test Classification",
        task_id="classification",
        base_model='google/flan-t5-xl',
        num_epochs=2,
        max_input_tokens=128,
        max_output_tokens=4,
        accumulate_steps=2,
        learning_rate=0.1,
        tuning_type=PromptTuningTypes.PT,
        verbalizer='Input: {{input}} Output:',
        auto_update_model=False
    )

    def test_00d_prepare_data_asset(self):
        asset_details = self.wml_client.data_assets.create(
            name=self.data_location.split('/')[-1],
            file_path=self.data_location)

        TestPromptTuning.asset_id = self.wml_client.data_assets.get_id(asset_details)
        self.assertIsInstance(self.asset_id, str)

    def test_02_data_reference_setup(self):
        TestPromptTuning.train_data_connections = [DataConnection(data_asset_id=self.asset_id)]
        TestPromptTuning.results_connection = None

        self.assertEqual(len(TestPromptTuning.train_data_connections), 1)
        self.assertIsNone(obj=TestPromptTuning.results_connection)

    def test_02a_read_saved_remote_data_before_fit(self):
        self.train_data_connections[0].set_client(self.wml_client)
        data = self.train_data_connections[0].read(raw=True, binary=True)

        self.assertIsInstance(data, bytes)

    @set_wml_client_default_space_wrapper
    def test_30_deployment_creation_with_prompted_asset(self):
        meta_props = {
            self.wml_client.deployments.ConfigurationMetaNames.NAME: "PT deployment SDK tests",
            self.wml_client.deployments.ConfigurationMetaNames.ONLINE: {}
        }
        deployments_details = self.wml_client.deployments.create(self.promoted_model_id,
                                                                 meta_props=meta_props)
        TestPromptTuning.deployment_id = self.wml_client.deployments.get_id(deployments_details)

        self.assertIsNotNone(TestPromptTuning.deployment_id)
        self.assertEqual(deployments_details['entity']['status']['state'], 'ready')

    @set_wml_client_default_space_wrapper
    def test_92_delete_deployments(self):
        self.wml_client.deployments.delete(TestPromptTuning.deployment_id)

    def test_99_delete_data_asset(self):
        if not self.SPACE_ONLY:
            self.wml_client.set.default_project(self.project_id)

        self.wml_client.data_assets.delete(self.asset_id)

        with self.assertRaises(WMLClientError):
            self.wml_client.data_assets.get_details(self.asset_id)


if __name__ == '__main__':
    unittest.main()
