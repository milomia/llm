#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import abc
from os import environ
import json
import logging
from pandas import DataFrame

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.tests.utils import (get_wml_credentials, get_cos_credentials, get_space_id,
                                                     set_wml_client_default_space_wrapper)
from ibm_watsonx_ai.tests.utils.cleanup import space_cleanup
from ibm_watsonx_ai.wml_client_error import WMLClientError, ApiRequestFailure

from ibm_watsonx_ai.experiment import TuneExperiment
from ibm_watsonx_ai.foundation_models.prompt_tuner import PromptTuner
from ibm_watsonx_ai.foundation_models import ModelInference

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

class AbstractTestPromptTuning(abc.ABC):
    """

    """

    bucket_name = environ.get('BUCKET_NAME', "prompt-tuning-sdk-tests")
    space_name = environ.get('SPACE_NAME', 'regression_tests_sdk_space')

    SPACE_ONLY = True

    wml_credentials = None
    cos_credentials = None
    space_id = None
    project_id = None

    experiment = None
    prompt_tuner = None
    tuned_details = None

    prompt_tuning_info = dict()

    train_data_connections: list = None
    results_data_connection = None

    stored_model_id = None
    promoted_model_id = None

    project_models_to_delete = []
    space_models_to_delete = []

    @classmethod
    def setUpClass(cls) -> None:
        """
        Load WML credentials from config.ini file based on ENV variable.
        """
        cls.wml_credentials = get_wml_credentials()
        cls.wml_client = APIClient(wml_credentials=cls.wml_credentials.copy())

        cls.cos_credentials = get_cos_credentials()
        cls.cos_endpoint = cls.cos_credentials.get('endpoint_url')
        cls.cos_resource_instance_id = cls.cos_credentials.get('resource_instance_id')

        cls.project_id = cls.wml_credentials.get('project_id')

    def test_00a_space_cleanup(self):
        space_checked = False
        while not space_checked:
            space_cleanup(self.wml_client,
                          get_space_id(self.wml_client, self.space_name,
                                       cos_resource_instance_id=self.cos_resource_instance_id),
                          days_old=7)
            space_id = get_space_id(self.wml_client, self.space_name,
                                    cos_resource_instance_id=self.cos_resource_instance_id)
            try:
                self.assertIsNotNone(space_id, msg="space_id is None")
                self.wml_client.spaces.get_details(space_id)
                space_checked = True
            except AssertionError or ApiRequestFailure:
                space_checked = False

        AbstractTestPromptTuning.space_id = space_id

        if self.SPACE_ONLY:
            self.wml_client.set.default_space(self.space_id)
        else:
            self.wml_client.set.default_project(self.project_id)

    def test_01_initialize_tune_experiment(self):

        if self.SPACE_ONLY:
            AbstractTestPromptTuning.experiment = TuneExperiment(credentials=self.wml_credentials.copy(),
                                                                 space_id=self.space_id)
        else:
            AbstractTestPromptTuning.experiment = TuneExperiment(credentials=self.wml_credentials.copy(),
                                                                 project_id=self.project_id)

        self.assertIsInstance(self.experiment, TuneExperiment, msg="Experiment is not of type TuneExperiment.")

    @abc.abstractmethod
    def test_02_data_reference_setup(self):
        pass

    def test_03_initialize_prompt_tuner(self):
        AbstractTestPromptTuning.prompt_tuner = self.experiment.prompt_tuner(
            **self.prompt_tuning_info)

        self.assertIsInstance(self.prompt_tuner, PromptTuner,
                              msg="experiment.prompt_tuner did not return PromptTuner object")

    def test_04_get_configuration_parameters_of_prompt_tuner(self):
        parameters = self.prompt_tuner.get_params()
        print(parameters)

        self.assertIsInstance(parameters, dict, msg='Config parameters are not a dictionary instance.')

    def test_05_run_prompt_tuning(self):
        AbstractTestPromptTuning.tuned_details = self.prompt_tuner.run(
            training_data_references=self.train_data_connections,
            training_results_reference=self.results_data_connection,
            background_mode=False)

        AbstractTestPromptTuning.run_id = self.tuned_details['metadata']['id']

    def test_06a_get_train_data(self):
        binary_data = self.prompt_tuner.get_data_connections()[0].read(binary=True)
        try:
            AbstractTestPromptTuning.train_data = json.loads(binary_data.decode())
        except json.decoder.JSONDecodeError:
            AbstractTestPromptTuning.train_data = [
                json.loads(line) for line in binary_data.decode().splitlines() if line
            ]

        print("train data sample:")
        print(self.train_data)

        self.assertIsInstance(self.train_data, list)
        self.assertGreater(len(self.train_data), 0)

    def test_07_get_run_status(self):
        status = self.prompt_tuner.get_run_status()
        run_details = self.prompt_tuner.get_run_details()
        self.assertEqual(status, run_details['entity'].get('status', {}).get('state'),
                         msg="Different statuses returned. Status: {},\n\n Run details {}".format(status,
                                                                                                  run_details))

        self.assertEqual(status, "completed",
                         msg="Prompt Tuning run didn't finished successfully. Status: {},\n\n Run details {}".format(
                             status,
                             run_details))

    def test_08a_get_run_details(self):
        parameters = self.prompt_tuner.get_run_details()
        training_details = self.wml_client.training.get_details(training_uid=parameters['metadata']['id'])
        print(json.dumps(training_details, indent=4))
        print(parameters)
        self.assertIsNotNone(parameters)

    def test_08b_get_run_details_include_metrics(self):
        parameters = self.prompt_tuner.get_run_details(include_metrics=True)
        training_details = self.wml_client.training.get_details(training_uid=parameters['metadata']['id'])
        print(json.dumps(training_details, indent=4))
        print(parameters)

        self.assertIsNotNone(parameters)
        self.assertIn('metrics', parameters['entity']['status'],
                      msg="prompt_tuner.get_run_details did not return metrics")

    def test_09_get_tuner(self):
        parameters = self.prompt_tuner.get_run_details()
        AbstractTestPromptTuning.prompt_tuner = self.experiment.runs.get_tuner(run_id=parameters['metadata']['id'])
        print("Received tuner params:", self.prompt_tuner.get_params())

        self.assertIsInstance(self.prompt_tuner, PromptTuner,
                              msg="experiment.get_tuner did not return PromptTuner object")
        status = AbstractTestPromptTuning.prompt_tuner.get_run_status()
        self.assertIsNotNone(status)

    def test_10_list_all_runs(self):
        historical_tunings = self.experiment.runs.list()
        print("All historical prompt tunings:")
        print(historical_tunings)

        self.assertIsInstance(historical_tunings, DataFrame,
                              msg="experiment.runs did not return DataFrame object")

    def test_11_list_specific_runs(self):
        parameters = self.prompt_tuner.get_params()
        historical_tunings = self.experiment.runs(filter=parameters['name']).list()
        print(f"Prompt tunings with name {parameters['name']}:")
        print(historical_tunings)

        self.assertIsInstance(historical_tunings, DataFrame,
                              msg="experiment.runs did not return DataFrame object")

    def test_12_runs_get_last_run_details(self):
        run_details = self.experiment.runs.get_run_details()
        print("Last prompt tuning run details:")
        print(run_details)

        self.assertIsNotNone(run_details)
        self.assertIsInstance(run_details, dict,
                              msg="experiment.runs.get_run_details did not return dict object")

    def test_13_runs_get_specific_run_details(self):
        parameters = self.prompt_tuner.get_run_details()
        run_details = self.experiment.runs.get_run_details(run_id=parameters['metadata']['id'])
        print(f"Run {parameters['metadata']['id']} details:")
        print(run_details)

        self.assertIsNotNone(run_details)
        self.assertIsInstance(run_details, dict,
                              msg="experiment.runs.get_run_details did not return dict object")

    def test_14_runs_get_run_details_include_metrics(self):
        run_details = self.experiment.runs.get_run_details(include_metrics=True)
        print("Last prompt tuning run details:")
        print(run_details)

        self.assertIsNotNone(run_details)
        self.assertIn('metrics', run_details['entity']['status'],
                      msg="experiment.runs.get_run_details did not return metrics")

    def test_15_get_summary_details(self):
        run_summary_details = self.prompt_tuner.summary()
        run_details = self.experiment.runs.get_run_details()
        print(f"Run {self.prompt_tuner.id} summary details:")
        print(run_summary_details)

        self.assertIsNotNone(run_summary_details)
        self.assertIs(type(run_summary_details), DataFrame)

        self.assertEqual(run_summary_details.get('Enhancements')[0][0],
                         run_details['entity'].get('prompt_tuning', {}).get('tuning_type'),
                         msg=f"Invalid run details: {run_details}")
        self.assertEqual(run_summary_details.get('Base model')[0],
                         run_details['entity'].get('prompt_tuning', {}).get('base_model', {}).get('model_id'),
                         msg=f"Invalid run details: {run_details}")
        self.assertEqual(run_summary_details.get('Auto store')[0],
                         run_details['entity'].get('auto_update_model'),
                         msg=f"Invalid run details: {run_details}")
        self.assertEqual(run_summary_details.get('Epochs')[0],
                         run_details['entity'].get('prompt_tuning', {}).get('num_epochs'),
                         msg=f"Invalid run details: {run_details}")
        self.assertGreater(run_summary_details.get('loss')[0], 0)

    def test_20_store_prompt_tuned_model_default_params(self):
        stored_model_details = self.wml_client.repository.store_model(training_id=self.prompt_tuner.id)
        AbstractTestPromptTuning.stored_model_id = self.wml_client.repository.get_model_id(stored_model_details)

        self.assertIsNotNone(self.stored_model_id)

    def test_21_promote_model_to_deployment_space(self):
        if self.SPACE_ONLY:
            AbstractTestPromptTuning.promoted_model_id = self.stored_model_id  # no need to promote
        else:
            AbstractTestPromptTuning.promoted_model_id = self.wml_client.spaces.promote(self.stored_model_id,
                                                                                        source_project_id=self.project_id,
                                                                                        target_space_id=self.space_id)
            AbstractTestPromptTuning.project_models_to_delete.append(self.stored_model_id)

        AbstractTestPromptTuning.space_models_to_delete.append(self.promoted_model_id
                                                               )

    @set_wml_client_default_space_wrapper
    def test_22_get_model_details(self):
        if self.wml_client.default_space_id is None:
            self.wml_client.set.default_space(self.space_id)
        model_details = self.wml_client.repository.get_details(self.promoted_model_id)
        self.assertIsNotNone(model_details)
        self.assertIsNotNone(model_details['entity'].get('training_id'))
        self.assertEqual(model_details['entity'].get('type'), 'prompt_tune_1.0')

    @set_wml_client_default_space_wrapper
    def test_23_list_repository(self):
        repository_data_frame_list = self.wml_client.repository.list_models()
        logger.info(repository_data_frame_list)
        repository_list = repository_data_frame_list.get('ID').to_list()
        self.assertIn(self.promoted_model_id, repository_list)

    def test_31_response_from_deployment_inference(self):
        if hasattr(self, 'deployment_id'):
            deployment_id = self.deployment_id
            d_inference = ModelInference(
                deployment_id=deployment_id,
                api_client=self.wml_client
            )
            response = d_inference.generate_text(prompt="sentence1: Oil prices fall back as Yukos oil threat lifted sentence2: Oil prices rise.")
            print(response)

            self.assertIsNotNone(response)

    def test_93_delete_experiment(self):
        self.prompt_tuner.cancel_run(hard_delete=True)
        with self.assertRaises(WMLClientError):
            self.wml_client.training.get_details(self.run_id)

    @set_wml_client_default_space_wrapper
    def test_94_delete_models(self):
        logger.info(f"Attempting to delete models: {self.space_models_to_delete, self.project_models_to_delete}"
                    f" in space: {self.wml_client.default_space_id} and project: {self.wml_client.default_project_id}")

        while len(self.space_models_to_delete) > 0:
            self.wml_client.repository.delete(self.space_models_to_delete.pop())

        if not self.SPACE_ONLY:
            self.wml_client.set.default_project(self.project_id)
            while len(self.project_models_to_delete) > 0:
                self.wml_client.repository.delete(self.project_models_to_delete.pop())
