#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

import pytest

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.tests.utils import get_wml_credentials, get_cos_credentials


def pytest_collection_modifyitems(items):
    """
    Because UnitTest do not like to cooperate with fixtures other than with param `autouse=True`
    there is a need to enumerate test BY MODEL and then ALPHANUMERICAL, which this function does.
    """
    for i, item in enumerate(items):
        if 'foundation_models' in item.nodeid:
            timeout = 35 * 60 if 'prompt_tuning' in item.name else 2 * 60  # 35 minutes for prompt tuning, 2 mins for other tests
            item.add_marker(pytest.mark.timeout(timeout))


@pytest.fixture(scope="session", name="credentials")
def fixture_credentials():
    """
    Fixture responsible for getting credentials from `config.ini` file
        return:
            dict: Credentials for WML
    """
    credentials = get_wml_credentials()
    return credentials


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
def fixture_api_client(credentials):
    """
    Fixture responsible for setup API Client with given credentials.
        Args:
            credentials:

        return:
            APIClient Object:
    """
    api_client = APIClient(credentials)
    return api_client


@pytest.fixture(scope="session", name="cos_credentials")
def fixture_cos_credentials():
    """
    Fixture responsible for getting COS credentials
        return:
            dict: COS Credentials
    """
    cos_credentials = get_cos_credentials()
    return cos_credentials


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
