#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.utils.autoai.utils import check_dependencies_versions
from ibm_watsonx_ai.tests.utils import get_wml_credentials


class MyTestCase(unittest.TestCase):
    request_json = {'hybrid_pipeline_software_specs': [{'name': "autoai-kb_3.1-py3.7"}]}

    @classmethod
    def setUpClass(cls) -> None:
        """
        Load WML credentials from config.ini file based on ENV variable.
        """

        cls.credentials = get_wml_credentials()
        cls.api_client = APIClient(wml_credentials=cls.credentials.copy())

    def test_01__all_and_xgboost(self):
        check_dependencies_versions(self.request_json, self.api_client, estimator_pkg='xgboost')

    def test_02__all_and_lightgbm(self):
        check_dependencies_versions(self.request_json, self.api_client, estimator_pkg='lightgbm')


if __name__ == '__main__':
    unittest.main()
