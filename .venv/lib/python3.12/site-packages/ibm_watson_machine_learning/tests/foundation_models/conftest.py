#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024 .
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------
import logging
from datetime import datetime, timedelta

import pytest

from ibm_watson_machine_learning.foundation_models.prompts import PromptTemplate
from ibm_watson_machine_learning.foundation_models.utils.enums import ModelTypes
from ibm_watson_machine_learning.foundation_models.prompts import PromptTemplateManager

"""
When adding some fixture here follow that pattern:
- first "little" fixtures, that  are returning something simple as `prompt_id`;
- second "more complex setups" like `fixture_setup_prompt_mgr`;
- last one "tear down methods"
"""


@pytest.fixture(scope='function', name="prompt_id")
def fixture_prompt_id(data_storage):
    """
    Fixture that is getting prompt ID
        Args:
            data_storage:

        return:
            prompt_id
    """
    prompt_id = data_storage.prompt_mgr.store_prompt(PromptTemplate(name="My test prompt",
                                                                    model_id=ModelTypes.FLAN_T5_XL,
                                                                    input_text="What is a {object} and how does it work?",
                                                                    input_variables=["object"])).prompt_id
    return prompt_id


@pytest.fixture(scope='class', name="model_id")
def fixture_model_id():
    """
    Fixture that is getting model ID
        return:
            model_id
    """
    model_id = ModelTypes.STARCODER.value

    return model_id


@pytest.fixture(scope='function', name="prompt_template")
def fixture_prompt_template(data_storage):
    """
    Fixture that is creating template before test, and deleting it after test.
        Args:
            data_storage:

        yield:
            Prompt object, after executing test runners goes back to fixture to delete cleanup prompts
    """
    data_storage.prompt_id = data_storage.prompt_mgr.store_prompt(PromptTemplate(name="My test prompt",
                                                                 model_id=ModelTypes.FLAN_T5_XL,
                                                                 input_text="What is a {object} and how does it work?",
                                                                 input_variables=["object"]))
    prompt = data_storage.prompt_id
    yield prompt
    data_storage.prompt_mgr.delete_prompt(prompt.prompt_id, force=True)


@pytest.fixture(scope='session', name="prompt_mgr")
def fixture_prompt_mgr(credentials, project_id):
    prompt_mgr = PromptTemplateManager(credentials, project_id=project_id)
    return prompt_mgr


@pytest.fixture(scope='session', name="delete_old_prompt_templates", autouse=True)
def fixture_prompt_template_teardown_method(prompt_mgr):
    """
    Fixture that it is called before testing class to proxy cleanup part
        Args:
            prompt_mgr:

        yield:
    """
    yield True
    logging.info("\n====DELETING OLD PROMPTS====")
    prompt_list = prompt_mgr.list()
    today = datetime.now().replace(microsecond=0)
    for index, row in prompt_list.iterrows():
        delta = today - datetime.fromisoformat(row['CREATED'].replace('Z', ''))

        if delta > timedelta(days=7):
            prompt_id = row['ID']
            prompt_mgr.delete_prompt(prompt_id, force=True)
            logging.info(f'Prompt: {prompt_id} has been deleted')


@pytest.fixture(scope='class', name="prompt_template_deployment_teardown_method")
def fixture_prompt_template_deployment_teardown_method(request, prompt_mgr):
    """
    Fixture that it is called before testing class to proxy cleanup part
        Args:
            request:
            prompt_mgr:

        yield:
            Prompt object, after executing test runners goes back to fixture to delete cleanup prompts
    """
    yield True
    if request.cls.stored_prompt_id is not None:
        prompt_mgr.delete_prompt(prompt_id=request.cls.prompt_id, force=True)
        print("Teardown")
    request.cls.stored_prompt_id = None
