#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.utils.autoai.utils import NextRunDetailsGenerator
from ibm_watsonx_ai.tests.utils import get_wml_credentials


class TestNextRunDetailsGenerator(unittest.TestCase):
    credentials_cp4d = None
    client = None
    project_id = 'dd829201-9d59-4f5a-b0e0-6ea3a88ae66b'
    generator = None
    data = []

    @classmethod
    def setUp(cls) -> None:
        cls.credentials_cp4d = get_wml_credentials('CLOUD_DEV_AM')
        cls.client = APIClient(cls.credentials_cp4d, cls.project_id)
        cls.client.set.default_project(cls.project_id)

    def test_01__initialize_generator_class(self):
        details = self.client.training.get_details(limit=1)
        self.data.extend(details['resources'])
        TestNextRunDetailsGenerator.generator = NextRunDetailsGenerator(api_client=self.client,
                                                                        href=details['next']['href'])

        self.assertIsInstance(self.generator.api_client, APIClient, msg="wml client not set")
        self.assertEqual(self.generator.href, details['next']['href'], msg="href is incorrect")

    def test_02__generate_next_run_details(self):
        for entry in self.generator:
            self.data.extend(entry)
        self.assertGreater(1, len(self.data), msg="There is only one or 0 runs, or generator works in incorrect way.")


if __name__ == '__main__':
    unittest.main()
