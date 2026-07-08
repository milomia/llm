#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from ibm_watsonx_ai.foundation_models.prompts import PromptTemplate, PromptTemplateManager
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes
from ibm_watsonx_ai.wml_client_error import WMLClientError
from ibm_watsonx_ai.tests.utils import get_wml_credentials, is_cp4d
from ibm_watsonx_ai import APIClient

@unittest.skipIf(is_cp4d(), "Prompt Template Deployment is not supported on CPD 4.8")
class TestPromptTemplateDeployment(unittest.TestCase):
    """
    The test can be run on Cloud only.
    This test runs e2e Prompt Template deployments 
    """

    @classmethod
    def setUpClass(cls):
        cls.wml_credentials = get_wml_credentials()
        cls.project_id = cls.wml_credentials.get('project_id')
        cls.prompt_mgr = PromptTemplateManager(cls.wml_credentials.copy(), project_id=cls.project_id)
        # cannot deploy prompt which is not tmeplate
        cls.model_id = ModelTypes.MIXTRAL_8X7B_INSTRUCT_V01_Q.value
        cls.prompt_id = cls.prompt_mgr.store_prompt(PromptTemplate(name="My test prompt",
                                                                   model_id=cls.model_id,
                                                                   input_text="What is a {object} and how does it work?",
                                                                   input_variables=["object"])).prompt_id
        cls.deployment_id = None

        cls.client = APIClient(cls.wml_credentials)
        cls.client.set.default_project(cls.project_id)
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        TestPromptTemplateDeployment.prompt_mgr.delete_prompt(TestPromptTemplateDeployment.prompt_id, force=True)
        return super().tearDownClass()

    def test_00a_create_deployment(self):
        client = TestPromptTemplateDeployment.client
        TestPromptTemplateDeployment.base_model_id = ModelTypes.FLAN_T5_XL.value
        meta_props = {
            client.deployments.ConfigurationMetaNames.NAME: "SAMPLE DEPLOYMENT PROMPT TEMPLATE",
            client.deployments.ConfigurationMetaNames.ONLINE: {},
            client.deployments.ConfigurationMetaNames.BASE_MODEL_ID: TestPromptTemplateDeployment.base_model_id}

        deployment_details = client.deployments.create(TestPromptTemplateDeployment.prompt_id, meta_props)
        TestPromptTemplateDeployment.deployment_id = client.deployments.get_uid(deployment_details)
        self.assertIsInstance(TestPromptTemplateDeployment.deployment_id, str)

    def test_00b_create_deployment_without_base_model_id(self):
        client = TestPromptTemplateDeployment.client
        meta_props = {
            client.deployments.ConfigurationMetaNames.NAME: "SAMPLE DEPLOYMENT PROMPT TEMPLATE",
            client.deployments.ConfigurationMetaNames.ONLINE: {}
            }

        deployment_details = client.deployments.create(TestPromptTemplateDeployment.prompt_id, meta_props)
        TestPromptTemplateDeployment.deployment_id_without_model = client.deployments.get_uid(deployment_details)
        self.assertEqual(client.deployments.get_details(TestPromptTemplateDeployment.deployment_id_without_model).get('entity', {}).get('base_model_id'),
                         TestPromptTemplateDeployment.model_id)
        
    def test_00c_create_deployment_without_project_space(self):
        wml_credentials = TestPromptTemplateDeployment.wml_credentials.copy()
        if wml_credentials.get('project_id'):
            wml_credentials.pop('project_id')
        if wml_credentials.get('space_id'):
            wml_credentials.pop('space_id')
        client = APIClient(wml_credentials)
        meta_props = {
            client.deployments.ConfigurationMetaNames.NAME: "SAMPLE DEPLOYMENT PROMPT TEMPLATE",
            client.deployments.ConfigurationMetaNames.ONLINE: {}
            }

        self.assertRaises(WMLClientError, client.deployments.create, TestPromptTemplateDeployment.project_id, meta_props)
        
    def test_01_get_details(self):
        client = TestPromptTemplateDeployment.client

        details = client.deployments.get_details(TestPromptTemplateDeployment.deployment_id)
        self.assertEqual(details.get('entity', {}).get('prompt_template', {}).get('id', ""),
                         TestPromptTemplateDeployment.prompt_id)
        self.assertEqual(details.get('entity', {}).get('base_model_id', ""), TestPromptTemplateDeployment.base_model_id)

    def test_02_deployment_list(self):
        client = TestPromptTemplateDeployment.client

        df = client.deployments.list()
        df_prompt = df[(df['GUID'] == TestPromptTemplateDeployment.deployment_id)]
        self.assertIn(df_prompt.iloc[0]['ARTIFACT_TYPE'], ['prompt_template', 'foundation_model'])

    def test_03_generate(self):
        client = TestPromptTemplateDeployment.client
        self.assertRaises(WMLClientError, client.deployments.generate, TestPromptTemplateDeployment.deployment_id)
        generate_repsonse = client.deployments.generate(TestPromptTemplateDeployment.deployment_id,
                                                        params={"prompt_variables": {"object": "loan"}})
        self.assertIsInstance(generate_repsonse, dict)
        self.assertEqual(generate_repsonse.get('model_id', ""), TestPromptTemplateDeployment.base_model_id)
        self.assertIsInstance(generate_repsonse.get('results', [{}])[0].get('generated_text'), str)

    def test_04_generate_text(self):
        client = TestPromptTemplateDeployment.client
        self.assertIsInstance(client.deployments.generate_text(TestPromptTemplateDeployment.deployment_id,
                                                               params={"prompt_variables": {"object": "loan"}}), str)

    def test_05_generate_stream_text(self):
        client = TestPromptTemplateDeployment.client
        self.assertIsInstance(list(client.deployments.generate_text_stream(TestPromptTemplateDeployment.deployment_id,
                                                                           params={"prompt_variables": {
                                                                               "object": "loan"}}))[0], str)

    def test_06_model_generate(self):
        client = TestPromptTemplateDeployment.client
        model = ModelInference(deployment_id=TestPromptTemplateDeployment.deployment_id,
                               api_client=client)
        self.assertRaises(WMLClientError, model.generate, TestPromptTemplateDeployment.deployment_id)
        generate_repsonse = model.generate(params={"prompt_variables": {"object": "loan"}})
        self.assertIsInstance(generate_repsonse, dict)
        self.assertEqual(generate_repsonse.get('model_id', ""), TestPromptTemplateDeployment.base_model_id)
        self.assertIsInstance(generate_repsonse.get('results', [{}])[0].get('generated_text'), str)

    def test_07_model_generate_text(self):
        client = TestPromptTemplateDeployment.client
        model = ModelInference(deployment_id=TestPromptTemplateDeployment.deployment_id,
                               api_client=client)
        self.assertIsInstance(model.generate_text(params={"prompt_variables": {"object": "loan"}}), str)

    def test_08_model_generate_stream_text(self):
        client = TestPromptTemplateDeployment.client
        model = ModelInference(deployment_id=TestPromptTemplateDeployment.deployment_id,
                               api_client=client)
        self.assertIsInstance(list(model.generate_text_stream(params={"prompt_variables": {"object": "loan"}}))[0], str)

    def test_09_model_credentials_generate(self):
        model = ModelInference(deployment_id=TestPromptTemplateDeployment.deployment_id,
                               credentials=self.wml_credentials, project_id=self.project_id)
        self.assertIsInstance(list(model.generate_text_stream(params={"prompt_variables": {"object": "loan"}}))[0], str)

    def test_10_update(self):
        client = TestPromptTemplateDeployment.client
        new_name = "change name"
        metadata = client.deployments.update(TestPromptTemplateDeployment.deployment_id,
                                             changes={client.deployments.ConfigurationMetaNames.NAME: new_name})
        self.assertEqual(metadata.get('entity', {}).get('name', ""), new_name)

    def test_11_delete_deployment(self):
        client = TestPromptTemplateDeployment.client

        self.assertEqual(client.deployments.delete(TestPromptTemplateDeployment.deployment_id), "SUCCESS")
        self.assertEqual(client.deployments.delete(TestPromptTemplateDeployment.deployment_id_without_model), "SUCCESS")
