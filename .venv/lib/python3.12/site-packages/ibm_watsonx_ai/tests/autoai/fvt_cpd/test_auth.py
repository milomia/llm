#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import os
import copy
import unittest

from ibm_watsonx_ai import APIClient
# change to `ibm_watsonx_ai` when `client` source code transformed
from ibm_watson_machine_learning import version as package_release_version
from ibm_watsonx_ai.tests.utils import (get_wml_credentials, is_cp4d)
from ibm_watsonx_ai.wml_client_error import WMLClientError, CannotAutogenerateBedrockUrl
from ibm_watsonx_ai.messages.messages import Messages


@unittest.skipIf(not is_cp4d(), "Not supported on cloud")
class TestAutoAIRemote(unittest.TestCase):
    """
    The test can be run on CLOUD, WMLS and CPD (not tested)
    The test covers:
    - COS set-up (if run on Cloud): checking if bucket exists for the cos instance, if not new bucket is create
    - Saving data `/bank.cdv` to COS/data assets
    - downloading training data from cos/data assets
    - downloading all generated pipelines to lale pipeline
    - deployment with lale pipeline
    - deployment deletion
    """
    incorrect_version_error_message = "The version was recognized incorrectly."
    version_not_recognized_error_message = "The version was not recognized."

    credentials = None
    token = None

    @classmethod
    def setUpClass(cls) -> None:
        """
        Load WML credentials from config.ini file based on ENV variable.
        """
        cls.credentials = get_wml_credentials()
        api_client = APIClient(wml_credentials=cls.credentials)
        cls.token = api_client.wml_token

    def test_01_missing_version(self):
        credentials = copy.copy(self.credentials)

        del credentials['version']
        client = APIClient(wml_credentials=credentials)

        self.assertTrue(client.CPD_version == float(client.CPD_version.supported_version_list[-1]))

    def test_02_missing_url(self):
        url_not_provided_error_message = '`url` is not provided.'
        credentials = copy.copy(self.credentials)
        del credentials['url']

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(url_not_provided_error_message in context.exception.error_msg)

    def test_03_missing_instance_id(self):
        url_is_not_valid_error_message = 'The specified url is not valid. To authenticate with your Cloud Pak for Data installed software, add `"instance_id": "openshift"` to your credentials. To authenticate with your Cloud Pak for Data as a Service account, see https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/ml-authentication.html .'
        credentials = copy.copy(self.credentials)
        del credentials['instance_id']

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(
            url_is_not_valid_error_message in context.exception.error_msg)

    def test_04_invalid_version(self):
        credentials = copy.copy(self.credentials)
        credentials['version'] = 'banana'
        message = WMLClientError(Messages.get_message(credentials['version'], package_release_version,
                                                      message_id="invalid_version_from_automated_check"))

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(str(message) in context.exception.error_msg)

    def test_05_invalid_url(self):
        url_syntax_error_message = '`url` must start with `https://`.'
        credentials = copy.copy(self.credentials)
        credentials['url'] = 'banana'

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(url_syntax_error_message in context.exception.error_msg)

    def test_06_invalid_instance_id(self):
        invalid_instance_id_error_message = 'Invalid instance_id for Cloud Pak for Data. Use `"instance_id": "openshift"` in your credentials. To authenticate with a different offering, refer to the product documentation for authentication details.'
        credentials = copy.copy(self.credentials)
        credentials['instance_id'] = 'banana'

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(
            invalid_instance_id_error_message in context.exception.error_msg)

    def test_username_password_auth_scenario_01_correct(self):
        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version'],
            'username': self.credentials['username'],
            'password': self.credentials['password']
        }
        APIClient(wml_credentials=credentials)

    def test_username_password_auth_scenario_02_missing_password(self):
        password_is_missing_error_message = '`password` missing in wml_credentials.'
        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version'],
            'username': self.credentials['username']
        }

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(password_is_missing_error_message in context.exception.error_msg)

    def test_username_password_auth_scenario_03_missing_username(self):
        username_is_missing_error_message = '`username` missing in wml_credentials.'
        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version'],
            'password': self.credentials['password']
        }

        with self.assertRaises(CannotAutogenerateBedrockUrl) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(username_is_missing_error_message in context.exception.args[0].error_msg)

    def test_username_apikey_auth_scenario_01_correct(self):
        if 'apikey' not in self.credentials:
            self.skipTest("No apikey in creds")

        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version'],
            'username': self.credentials['username'],
            'apikey': self.credentials['apikey']
        }
        APIClient(wml_credentials=credentials)

    def test_username_apikey_auth_scenario_02_invalid_apikey_key(self):
        if 'apikey' not in self.credentials:
            self.skipTest("No apikey in creds")

        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version'],
            'username': self.credentials['username'],
            'apikey': self.credentials['apikey']
        }
        APIClient(wml_credentials=credentials)

    def test_username_apikey_auth_scenario_03_url_in_env_variables(self):
        os.environ['RUNTIME_ENV_APSX_URL'] = self.credentials['url']

        credentials = {
            'instance_id': self.credentials['instance_id'],
            'version': self.credentials['version'],
            'username': self.credentials['username'],
            'apikey': self.credentials['apikey']
        }
        APIClient(wml_credentials=credentials)

    def test_token_auth_scenario_01_correct(self):
        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version'],
            'token': self.token
        }
        APIClient(wml_credentials=credentials)

    def test_token_auth_scenario_03_missing_token(self):
        username_is_missing_error_message = '`username` missing in wml_credentials.'
        credentials = {
            'instance_id': self.credentials['instance_id'],
            'url': self.credentials['url'],
            'version': self.credentials['version']
        }

        with self.assertRaises(WMLClientError) as context:
            APIClient(wml_credentials=credentials)

        self.assertTrue(username_is_missing_error_message in context.exception.error_msg)

    def test_project_id_auth_scenario_01_correct_char_key(self):
        project_id_syntax_error_message = '`project_id` parameter contains bad syntax!'
        project_id_special_characters_error_message = '`project_id` parameter can not contain special characters in blocks!'
        credentials = copy.copy(self.credentials)
        project_id = credentials['project_id']

        first_block = str(project_id[:7]).isalnum()
        second_block = str(project_id[9:12]).isalnum()
        third_block = str(project_id[14:17]).isalnum()
        fourth_block = str(project_id[19:22]).isalnum()
        fifth_block = str(project_id[24:]).isalnum()

        self.assertTrue(project_id[8] and project_id[13] and project_id[18] and project_id[23] == "-",
                        project_id_syntax_error_message)
        self.assertTrue(first_block and second_block and third_block and fourth_block and fifth_block,
                        project_id_special_characters_error_message)

        APIClient(wml_credentials=credentials)


if __name__ == '__main__':
    unittest.main()
