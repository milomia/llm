#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------
import logging
from datetime import datetime, timedelta

import allure
import pytest

from ibm_watson_machine_learning import APIClient
from ibm_watson_machine_learning.tests.foundation_models.tests_steps.data_storage import DataStorage
from ibm_watson_machine_learning.tests.foundation_models.tests_steps.prompt_template_steps import PromptTemplateSteps
from ibm_watson_machine_learning.tests.foundation_models.tests_steps.prompt_tuning_steps import PromptTuningSteps
from ibm_watson_machine_learning.tests.foundation_models.tests_steps.universal_steps import UniversalSteps
from ibm_watson_machine_learning.tests.utils import get_wml_credentials, get_cos_credentials
from ibm_watson_machine_learning.wml_client_error import WMLClientError


def pytest_collection_modifyitems(items):
    """
    Because UnitTest do not like to cooperate with fixtures other than with param `autouse=False`
    there is a need to enumerate test BY MODEL and then ALPHANUMERICAL, which this function does.
    """
    for i, item in enumerate(items):
        if 'foundation_models' in item.nodeid:
            timeout = 35 * 60 if 'prompt_tuning' in item.name else 2 * 60  # 35 minutes for prompt tuning, 2 mins for other tests
            item.add_marker(pytest.mark.timeout(timeout))


class Credentials(dict):
    """
    Wrapper to search thought the credentials `keys` and search for `secret values`
    then replace them with `****` so they will not be shown in console log
    """

    def __repr__(self):
        secret_dict = {'apikey': '****'}
        tmp = dict(self)
        for el in secret_dict:
            if el in self:
                tmp[el] = secret_dict[el]
        return tmp.__repr__()


@pytest.fixture(scope="session", name="credentials")
def fixture_credentials():
    """
    Fixture responsible for getting credentials from `config.ini` file
        return:
            dict: Credentials for WML
    """
    credentials = get_wml_credentials()
    return Credentials(credentials)


@pytest.fixture(scope="session", name="project_id")
def fixture_project_id(credentials):
    """
    Fixture responsible for returning project ID
        Args:
            credentials:

        return:
            str: Project ID
    """
    project_id = credentials.get('project_id')
    return project_id


@pytest.fixture(scope="session", name="space_id")
def fixture_space_id(credentials):
    """
    Fixture responsible for returning space ID
        Args:
            credentials:

        return:
            str: Space ID
    """
    space_id = credentials.get('space_id')
    return space_id


@pytest.fixture(scope="session", name="api_client")
def fixture_api_client(credentials, project_id):
    """
    Fixture responsible for setup API Client with given credentials.
        Args:
            credentials:
            project_id:
        return:
            APIClient Object:
    """
    api_client = APIClient(credentials, project_id=project_id)
    api_client.set.default_project(project_id)
    return api_client


@pytest.fixture(scope="session", name="cos_credentials")
def fixture_cos_credentials():
    """
    Fixture responsible for getting COS credentials
        return:
            dict: COS Credentials
    """
    cos_credentials = get_cos_credentials()
    return Credentials(cos_credentials)


@pytest.fixture(scope="session", name="cos_endpoint")
def fixture_cos_endpoint(cos_credentials):
    """
    Fixture responsible for getting COS endpoint.
        Args:
            cos_credentials:

        return:
            str: COS Endpoint
    """
    cos_endpoint = cos_credentials['endpoint_url']
    return cos_endpoint


@pytest.fixture(scope="session", name="cos_resource_instance_id")
def fixture_cos_resource_instance_id(cos_credentials):
    """
    Fixture responsible for getting COS Instance ID from cos_credentials part of config.ini file
        Args:
            cos_credentials:

        return:
            str: COS resource instance ID
    """
    cos_resource_instance_id = cos_credentials['resource_instance_id']
    return cos_resource_instance_id


@pytest.fixture(scope="session", name="delete_old_data_assets", autouse=True)
def fixture_delete_old_data_assets(api_client):
    """
    Fixture responsible for getting deleting assets older than 7 days
        Args:
            api_client
    """
    yield
    logging.info("\n====DELETING OLD DATA ASSETS====")
    asset_list = api_client.data_assets.get_details()
    today = datetime.now().replace(microsecond=0)

    for element in asset_list["resources"]:
        delta = today - datetime.fromisoformat(element["metadata"]["created_at"].replace('Z', ''))

        if delta > timedelta(days=7):
            asset_id = element["metadata"]["asset_id"]
            api_client.data_assets.delete(asset_id)
            logging.info(f'Asset: {asset_id} has been deleted')


@pytest.fixture(scope="session", name="delete_old_experiments", autouse=True)
def fixture_delete_old_experiments(api_client):
    """
    Fixture responsible for getting deleting trainings older than 7 days
        Args:
            api_client
    """
    yield
    logging.info("\n====DELETING OLD TRAININGS====")
    experiment_list = api_client.training.get_details()
    today = datetime.now().replace(microsecond=0)

    for element in experiment_list["resources"]:
        delta = today - datetime.fromisoformat(element["metadata"]["created_at"].replace('Z', ''))

        if delta > timedelta(days=7):
            training_id = element['metadata']['id']
            pipeline_id = element['entity'].get('pipeline', {}).get('id')
            if pipeline_id:
                try:
                    api_client.pipelines.delete(pipeline_id)
                except:
                    logging.debug("Pipeline not deleted/detected")
            api_client.training.cancel(training_id, hard_delete=True)
            logging.info(f'Pipeline ID: {pipeline_id} has been deleted')
            logging.info(f'Experiment: {training_id} has been deleted')


@pytest.fixture(scope="session", name="delete_old_models_and_deployments", autouse=True)
def fixture_delete_old_models_and_deployments(api_client):
    """
    Fixture responsible for getting deleting models and deployments older than 7 days. To delete model you need
    to delete deployment first.
        Args:
            api_client
    """
    yield
    logging.info("\n====DELETING OLD DEPLOYMENTS AND MODELS====")
    deployment_list = api_client.deployments.get_details()
    model_list = api_client._models.get_details(get_all=True)
    today = datetime.now().replace(microsecond=0)

    for element in deployment_list["resources"]:
        delta = today - datetime.fromisoformat(element["metadata"]["created_at"].replace('Z', ''))
        try:
            if delta > timedelta(days=7):
                deployment_id = element['metadata']['id']
                api_client.deployments.delete(deployment_id)
                logging.info(f'Deployment: {deployment_id} has been deleted')
        except WMLClientError as e:
            logging.error(f'Error:{e} on {element}')

    for element in model_list["resources"]:
        delta = today - datetime.fromisoformat(element["metadata"]["created_at"].replace('Z', ''))
        try:
            if delta > timedelta(days=7):
                model_id = element['metadata']['id']
                api_client.repository.delete(model_id)
                logging.info(f'Model: {model_id} has been deleted')
        except WMLClientError as e:
            logging.error(f'Error:{e} on {element}')


@pytest.fixture(scope="session", name="delete_old_connections", autouse=True)
def fixture_delete_old_connections(api_client):
    """
    Fixture responsible for getting deleting connections older than 7 days
        Args:
            api_client
    """
    yield
    logging.info("\n====DELETING OLD CONNECTIONS====")
    connection_list = api_client.connections.get_details()
    today = datetime.now().replace(microsecond=0)
    for element in connection_list["resources"]:
        delta = today - datetime.fromisoformat(element["metadata"]["create_time"].replace('Z', ''))

        if delta > timedelta(days=7):
            connection_id = element['metadata']['id']
            api_client.repository.delete(connection_id)
            logging.info(f'Connection: {connection_id} has been deleted')


# @pytest.fixture(name="space_cleanup")
# def fixture_space_clean_up(api_client, cos_resource_instance_id, project_id, request):
#     print('cleanUP')
#     space_checked = False
#     while not space_checked:
#         space_cleanup(api_client,
#                       get_space_id(api_client, space_name,
#                                    cos_resource_instance_id=cos_resource_instance_id),
#                       days_old=7)
#         space_id = get_space_id(api_client, space_name,
#                                 cos_resource_instance_id=cos_resource_instance_id)
#         try:
#             assert space_id is not None, "space_id is None"
#             api_client.spaces.get_details(space_id)
#             space_checked = True
#         except AssertionError or ApiRequestFailure:
#             space_checked = False
#
#     request.cls.space_id = space_id
#
#     print('cleanUP x 2')
#
#     if request.cls.SPACE_ONLY:
#         api_client.set.default_space(space_id)
#     else:
#         api_client.set.default_project(project_id)

@allure.title("Data Storage Class - initialization")
@pytest.fixture(scope="function", name="data_storage")
def fixture_data_storage_init(api_client, prompt_mgr):
    """
    Every step will be using the same object of DataStorage
    """
    data_storage = DataStorage()
    data_storage.api_client = api_client
    data_storage.prompt_mgr = prompt_mgr
    return data_storage


@allure.title("Universal Steps - initialization")
@pytest.fixture(scope="function", name="universal_step")
def fixture_universal_step_init(data_storage):
    return UniversalSteps(data_storage)


@allure.title("Prompt Tuning Steps - initialization")
@pytest.fixture(scope="function", name="prompt_tuning_step")
def fixture_prompt_tuning_step_init(data_storage):
    return PromptTuningSteps(data_storage)


@allure.title("Prompt Template Steps - initialization")
@pytest.fixture(scope="function", name="prompt_template_step")
def fixture_prompt_template_step_init(data_storage):
    return PromptTemplateSteps(data_storage)
