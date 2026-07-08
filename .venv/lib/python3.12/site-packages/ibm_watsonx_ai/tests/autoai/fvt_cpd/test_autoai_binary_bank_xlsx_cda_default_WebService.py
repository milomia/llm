#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

import ibm_boto3
from ibm_watsonx_ai.experiment import AutoAI
from ibm_watsonx_ai.helpers.connections import DataConnection, S3Location
from ibm_watsonx_ai.wml_client_error import WMLClientError
from ibm_watsonx_ai.tests.utils import bucket_exists, create_bucket, is_cp4d, create_connection_to_cos
from ibm_watsonx_ai.tests.autoai.abstract_tests_classes import AbstractTestAutoAISync,\
    AbstractTestWebservice

from ibm_watsonx_ai.utils.autoai.enums import PredictionType, Metrics


class TestAutoAIRemote(AbstractTestAutoAISync, AbstractTestWebservice, unittest.TestCase):
    """
    The test can be run on CPD
    """

    cos_resource = None
    data_location = './autoai/data/xlsx/CarPrice_bank__two_sheets.xlsx'
    sheet_name = 'bank'
    # sheet_number = 1 # not supported by FLight Service

    data_cos_path = 'data/CarPrice_bank__two_sheets.xlsx'

    # data_location = './autoai/data/bank.csv'
    # data_cos_path = "bank.csv"

    SPACE_ONLY = False

    OPTIMIZER_NAME = "Bank test sdk"
    HISTORICAL_RUNS_CHECK = False

    target_space_id = None

    experiment_info = dict(
        name=OPTIMIZER_NAME*5,
        desc='a long test description '*5,
        prediction_type=PredictionType.BINARY,
        prediction_column='y',
        positive_label='yes',
        scoring=Metrics.ACCURACY_SCORE,
        holdout_size=0.1,
        max_number_of_estimators=1,
        excel_sheet=sheet_name
    )

    def test_00b_prepare_COS_instance_and_connection(self):
        TestAutoAIRemote.connection_id, TestAutoAIRemote.bucket_name = create_connection_to_cos(
            wml_client=self.api_client,
            cos_credentials=self.cos_credentials,
            cos_endpoint=self.cos_endpoint,
            bucket_name=self.bucket_name,
            save_data=True,
            data_path=self.data_location,
            data_cos_path=self.data_cos_path)

        print("Connection id: ", self.connection_id)

        self.assertIsInstance(self.connection_id, str)

    def test_00c_prepare_connected_data_asset(self):
        asset_details = self.api_client.data_assets.store({
            self.api_client.data_assets.ConfigurationMetaNames.CONNECTION_ID: self.connection_id,
            self.api_client.data_assets.ConfigurationMetaNames.NAME: "Bank - training asset",
            self.api_client.data_assets.ConfigurationMetaNames.DATA_CONTENT_NAME: f"{self.bucket_name}/{self.data_cos_path}/{self.sheet_name}"
        })
        print(asset_details)

        TestAutoAIRemote.asset_id = self.api_client.data_assets.get_id(asset_details)
        self.assertIsInstance(self.asset_id, str)

    def test_02_data_reference_setup(self):
        TestAutoAIRemote.data_connection = DataConnection(data_asset_id=self.asset_id)
        TestAutoAIRemote.results_connection = None

        self.assertIsNotNone(obj=TestAutoAIRemote.data_connection)
        self.assertIsNone(obj=TestAutoAIRemote.results_connection)

    # def test_99_delete_connection_and_connected_data_asset(self):
    #     self.api_client.data_assets.delete(self.asset_id)
    #     self.api_client.connections.delete(self.connection_id)
    #
    #     with self.assertRaises(WMLClientError):
    #         self.api_client.data_assets.get_details(self.asset_id)
    #         self.api_client.connections.get_details(self.connection_id)


if __name__ == '__main__':
    unittest.main()
