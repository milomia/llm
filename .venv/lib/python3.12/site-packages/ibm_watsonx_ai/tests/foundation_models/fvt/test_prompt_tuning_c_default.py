#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from ibm_watsonx_ai.helpers.connections import DataConnection, ContainerLocation
from ibm_watsonx_ai.tests.foundation_models.abstract_tests_classes import AbstractTestPromptTuning

from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, PromptTuningInitMethods

from ibm_watsonx_ai.tests.utils import save_data_to_container, is_cp4d

@unittest.skipIf(is_cp4d(), "Container type is not supported on CP4D")
class TestPromptTuning(AbstractTestPromptTuning, unittest.TestCase):
    """
    The test can be run on Cloud only.
    This test runs Prompt Tuning with input and output data references as Container
    """

    data_location = './foundation_models/data/file_to_tune1.json'
    data_cos_path = 'file_to_tune1.json'
    SPACE_ONLY = True

    PROMPT_TUNING_NAME = "SDK test Classification Container"

    prompt_tuning_info = dict(
        name=PROMPT_TUNING_NAME,
        task_id="summarization",
        base_model=ModelTypes.LLAMA_2_13B_CHAT,
        init_method=PromptTuningInitMethods.TEXT,
        init_text='Summarize: ',
        num_epochs=5
    )

    deployment_id = None

    def test_00b_write_data_to_container(self):
        if self.SPACE_ONLY:
            self.wml_client.set.default_space(self.space_id)
        else:
            self.wml_client.set.default_project(self.project_id)

        save_data_to_container(self.data_location, self.data_cos_path, self.wml_client)

    def test_02_data_reference_setup(self):
        TestPromptTuning.train_data_connections = [DataConnection(
            location=ContainerLocation(path=self.data_cos_path
                                       ))]
        TestPromptTuning.results_connection = None

        self.assertEqual(len(TestPromptTuning.train_data_connections), 1)

    def test_02a_read_saved_remote_data_before_fit(self):
        self.train_data_connections[0].set_client(self.wml_client)
        data = self.train_data_connections[0].read(raw=True, binary=True)

        self.assertIsInstance(data, bytes)

    def test_30_deployment_creation_in_project(self):
        if not self.SPACE_ONLY:
            self.wml_client.set.default_project(self.project_id)
        meta_props = {
            self.wml_client.deployments.ConfigurationMetaNames.NAME: "PT deployment SDK tests",
            self.wml_client.deployments.ConfigurationMetaNames.ONLINE: {}
        }
        deployments_details = self.wml_client.deployments.create(self.stored_model_id,
                                                                 meta_props=meta_props)
        TestPromptTuning.deployment_id = self.wml_client.deployments.get_id(deployments_details)
        self.assertIsNotNone(TestPromptTuning.deployment_id)

        self.assertEqual(deployments_details['entity']['status']['state'], 'ready')
        print(deployments_details)

    def test_91_delete_deployments(self):
        if not self.SPACE_ONLY:
            self.wml_client.set.default_project(self.project_id)
        self.wml_client.deployments.delete(TestPromptTuning.deployment_id)


    def test_99_delete_container(self):
        if not self.SPACE_ONLY:
            self.wml_client.set.default_project(self.project_id)

        # TODO!

        # with self.assertRaises(WMLClientError):
        # self.wml_client.data_assets.get_details(self.asset_id)


if __name__ == '__main__':
    unittest.main()
