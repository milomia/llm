#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import unittest

from os.path import join
from ibm_watsonx_ai.experiment import AutoAI
from ibm_watsonx_ai.helpers.connections import DataConnection, S3Location
from ibm_watsonx_ai.wml_client_error import WMLClientError
from ibm_watsonx_ai.tests.utils import create_connection_to_cos
from ibm_watsonx_ai.tests.autoai.abstract_tests_classes import AbstractTestTSAsync, \
    AbstractTestWebservice

from ibm_watsonx_ai.utils.autoai.enums import PredictionType, ImputationStrategy


class TestAutoAIRemote(AbstractTestTSAsync, unittest.TestCase):
    """
    The test can be run on Cloud only
    """

    cos_resource = None
    data_location = './autoai/data/store_item_demand_dataset_nans.csv'

    data_cos_path = 'store_item_demand_dataset_nans.csv'

    batch_payload_location = data_location
    batch_payload_cos_location = data_cos_path

    SPACE_ONLY = False
    BATCH_DEPLOYMENT = False

    OPTIMIZER_NAME = "Store Item Demand Nans test sdk"
    DEPLOYMENT_NAME = OPTIMIZER_NAME + "Deployment"

    target_space_id = None

    experiment_info = dict(
        name=OPTIMIZER_NAME,
        prediction_type=PredictionType.FORECASTING,
        prediction_columns=['sales'],
        timestamp_column_name='date',
        numerical_imputation_strategy=ImputationStrategy.MEDIAN,
        max_number_of_estimators=10,
        notebooks=True
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

        self.assertIsInstance(self.connection_id, str)

    def test_00d_prepare_connected_data_asset(self):
        asset_details = self.api_client.data_assets.store({
            self.api_client.data_assets.ConfigurationMetaNames.CONNECTION_ID: self.connection_id,
            self.api_client.data_assets.ConfigurationMetaNames.NAME: f"{self.data_cos_path} - training asset",
            self.api_client.data_assets.ConfigurationMetaNames.DATA_CONTENT_NAME: join(self.bucket_name,
                                                                                       self.data_cos_path)
        })
        TestAutoAIRemote.asset_id = self.api_client.data_assets.get_id(asset_details)
        self.assertIsInstance(self.asset_id, str)

    def test_02_data_reference_setup(self):
        TestAutoAIRemote.data_connection = DataConnection(data_asset_id=self.asset_id)
        TestAutoAIRemote.results_connection = None

        self.assertIsNotNone(obj=TestAutoAIRemote.data_connection)
        self.assertIsNone(obj=TestAutoAIRemote.results_connection)

    def test_09a_predict_using_all_fitted_pipeline_as_sklearn(self):
        pipelines_summary = self.remote_auto_pipelines.summary()

        AbstractTestTSAsync.winning_pipelines_summary = pipelines_summary[pipelines_summary['Winner']]
        AbstractTestTSAsync.discarded_pipelines_summary = pipelines_summary[pipelines_summary['Winner'] == False]

        failed_pipelines = []
        for pipeline_name in pipelines_summary.index:
            print(pipeline_name)
            try:
                pipeline_model = self.remote_auto_pipelines.get_pipeline(pipeline_name, astype='sklearn')
                predictions = pipeline_model.predict(X=self.train_X)
                print(predictions)
                self.assertGreater(len(predictions), 0)
            except Exception as e:
                failed_pipelines.append(pipeline_name)
                print(e)

        self.assertEqual(len(failed_pipelines), 0, msg=f"Some Pipelines failed: {failed_pipelines}")

    def test_09b_predict_using_all_fitted_pipeline_as_lale(self):
        pipelines_summary = self.remote_auto_pipelines.summary()

        AbstractTestTSAsync.winning_pipelines_summary = pipelines_summary[pipelines_summary['Winner']]
        AbstractTestTSAsync.discarded_pipelines_summary = pipelines_summary[pipelines_summary['Winner'] == False]

        failed_pipelines = []
        for pipeline_name in pipelines_summary.index:
            print(pipeline_name)
            try:
                pipeline_model = self.remote_auto_pipelines.get_pipeline(pipeline_name)
                predictions = pipeline_model.predict(X=self.train_X)
                print(predictions)
                self.assertGreater(len(predictions), 0)
            except Exception as e:
                failed_pipelines.append(pipeline_name)
                print(e)

        self.assertEqual(len(failed_pipelines), 0, msg=f"Some Pipelines failed: {failed_pipelines}")

    def test_99_delete_connection(self):
        if not self.SPACE_ONLY:
            self.api_client.set.default_project(self.project_id)

        self.api_client.connections.delete(self.connection_id)

        with self.assertRaises(WMLClientError):
            self.api_client.connections.get_details(self.connection_id)

    def test_99z_uninstall_xgboost_090(self):
        pass


if __name__ == '__main__':
    unittest.main()
