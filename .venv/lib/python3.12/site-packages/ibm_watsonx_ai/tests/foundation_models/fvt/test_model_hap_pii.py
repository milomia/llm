#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------
import warnings
import pytest

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.tests.utils import get_wml_credentials
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams, GenTextModerationsMetaNames
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods, ModelTypes
from ibm_watsonx_ai.foundation_models.utils.utils import get_model_specs

wml_credentials = get_wml_credentials()
model_types_list = [model.value for model in ModelTypes]
available_models = [model_spec['model_id'] for model_spec in get_model_specs(wml_credentials.get('url')).get('resources', []) 
                    if model_spec['model_id'] in model_types_list ]

class TestModelHapPii:
    """
    This tests covers:
    - Generate text with HAP on
    - generate text with PII on
    """
    @classmethod
    def setup_class(cls) -> None:
        """
        Load WML credentials from config.ini file based on ENV variable.
        """
        cls.wml_credentials = get_wml_credentials()
        cls.project_id = cls.wml_credentials.get('project_id')
        cls.client = APIClient(wml_credentials=cls.wml_credentials,
                               project_id=cls.project_id)

        cls.text_params = {
            GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
            GenParams.MIN_NEW_TOKENS: 30,
            GenParams.MAX_NEW_TOKENS: 50
            }

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_00_generate_hap_output(self, model):
        q = "Please repeat the words in [], do not trim space.\n[ I hate this damn world. ]"
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }
        # guardrails_pii_params = {
        #     GenTextModerationsMetaNames.INPUT: False,
        #     GenTextModerationsMetaNames.OUTPUT: False
        #     }
        
        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                #   guardrails_pii_params=guardrails_pii_params
                                  )
        
        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('hap'), "No HAP detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                        params=TestModelHapPii.text_params,
                                        guardrails=True,
                                        guardrails_hap_params=guardrails_hap_params,
                                        # guardrails_pii_params=guardrails_pii_params
                                        )
            
            assert len(['Potentially harmful text detected' in str(warning.message) for warning in w]), \
                "No worning with HAP detection"

    @pytest.mark.parametrize("model", available_models, ids=available_models)
    def test_00a_generate_hap_output_with_mask(self, model, project_id, api_client):
        q = "Please repeat the words in [], do not trim space.\n[ I hate this damn world. ]"
        model = ModelInference(
            model_id=model,
            project_id=project_id,
            api_client=api_client
        )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.THRESHOLD: 0.01,
            GenTextModerationsMetaNames.MASK: {"remove_entity_value": True}
        }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                  )

        print(response['results'][0].get('generated_text'))
        assert '****' in response['results'][0].get('generated_text', {}), "No mask used (HAP)"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_01_generate_pii_output(self, model):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com ] "
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: False
            }
        guardrails_pii_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: True,
            GenTextModerationsMetaNames.THRESHOLD: 0.0
            }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                  guardrails_pii_params=guardrails_pii_params
                                  )

        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('pii'), "No PII detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                        params=TestModelHapPii.text_params,
                                        guardrails=True,
                                        guardrails_hap_params=guardrails_hap_params,
                                        guardrails_pii_params=guardrails_pii_params
                                        )

            assert len(['Personally identifiable information detected' in str(warning.message) for warning in w]), \
                "No worning with HAP detection"

    @pytest.mark.parametrize("model", available_models, ids=available_models)
    def test_01a_generate_pii_output_with_mask(self, model, project_id, api_client):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com ] "
        model = ModelInference(
            model_id=model,
            project_id=project_id,
            api_client=api_client
        )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: False
        }
        guardrails_pii_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: True,
            GenTextModerationsMetaNames.THRESHOLD: 0.0,
            GenTextModerationsMetaNames.MASK: {"remove_entity_value": True}
        }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                  guardrails_pii_params=guardrails_pii_params
                                  )
        print(response['results'][0].get('generated_text'))
        assert '****' in response['results'][0].get('generated_text', {}), "No mask used (PII)"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_02_generate_hap_pii_output(self, model):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com  I hate this damn world. ] "
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }
        guardrails_pii_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: True,
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                  guardrails_pii_params=guardrails_pii_params)

        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('pii') or\
            response['results'][0].get('moderations', {}).get('hap'), "No HAP/PII detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                        params=TestModelHapPii.text_params,
                                        guardrails=True,
                                        guardrails_hap_params=guardrails_hap_params,
                                        guardrails_pii_params=guardrails_pii_params
                                        )

            assert len(['Potentially harmful text detected' in str(warning.message) for warning in w]) or\
                len(['Personally identifiable information detected' in str(warning.message) for warning in w]), \
                "No worning with HAP/PII detection"


    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_03_generate_hap_input(self, model):
        q = "Please repeat the words in [], do not trim space.\n[ I hate this damn world. ]"
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }
        # guardrails_pii_params = {
        #     GenTextModerationsMetaNames.INPUT: False,
        #     GenTextModerationsMetaNames.OUTPUT: False
        #     }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                #   guardrails_pii_params=guardrails_pii_params
                                  )

        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('hap'), "No HAP detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                        params=TestModelHapPii.text_params,
                                        guardrails=True,
                                        guardrails_hap_params=guardrails_hap_params,
                                        # guardrails_pii_params=guardrails_pii_params
                                        )

            assert len(['Unsuitable input detected.' in str(warning.message) for warning in w]), \
                "No worning with HAP detection"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_04_generate_pii_input(self, model):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com ] "
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: False
            }
        guardrails_pii_params = {
            GenTextModerationsMetaNames.INPUT: True,
            GenTextModerationsMetaNames.OUTPUT: True,
            GenTextModerationsMetaNames.THRESHOLD: 0.0
            }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                  guardrails_pii_params=guardrails_pii_params)

        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('pii'), "No PII detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                        params=TestModelHapPii.text_params,
                                        guardrails=True,
                                        guardrails_hap_params=guardrails_hap_params,
                                        guardrails_pii_params=guardrails_pii_params
                                        )

            assert len(['Unsuitable input detected.' in str(warning.message) for warning in w]), \
                "No worning with HAP detection"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_05_generate_hap_pii_input(self, model):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com  I hate this damn world. ] "
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }
        guardrails_pii_params = {
            GenTextModerationsMetaNames.INPUT: True,
            GenTextModerationsMetaNames.OUTPUT: True,
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }

        response = model.generate(prompt=q,
                                  params=TestModelHapPii.text_params,
                                  guardrails=True,
                                  guardrails_hap_params=guardrails_hap_params,
                                  guardrails_pii_params=guardrails_pii_params)

        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('pii') or\
            response['results'][0].get('moderations', {}).get('hap'), "No HAP/PII detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                        params=TestModelHapPii.text_params,
                                        guardrails=True,
                                        guardrails_hap_params=guardrails_hap_params,
                                        guardrails_pii_params=guardrails_pii_params
                                        )

            assert len(['Unsuitable input detected.' in str(warning.message) for warning in w]) or\
                "No worning with HAP/PII detection"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_06_generate_stream_hap_pii(self, model):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com  I hate this damn world. ] "
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client
            )
        guardrails_hap_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }
        guardrails_pii_params = {
            GenTextModerationsMetaNames.INPUT: False,
            GenTextModerationsMetaNames.OUTPUT: True,
            GenTextModerationsMetaNames.THRESHOLD: 0.01
            }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text_stream(prompt=q,
                                              params=TestModelHapPii.text_params,
                                              guardrails=True,
                                              guardrails_hap_params=guardrails_hap_params,
                                              guardrails_pii_params=guardrails_pii_params
                                            )
            text_stream = list(text)
            print(text_stream)
            
            assert len(['Potentially harmful text detected' in str(warning.message) for warning in w]) or\
                len(['Personally identifiable information detected' in str(warning.message) for warning in w]), \
                "No worning with HAP/PII detection"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_07_generate_enable_guardrails_only(self, model):
        q = "Please repeat the words in [], do not trim space.\n[ I hate this damn world. ]"
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client,
            params=TestModelHapPii.text_params,
        )


        response = model.generate(prompt=q,
                                  guardrails=True)

        print(response['results'][0].get('moderations'))
        assert response['results'][0].get('moderations', {}).get('hap'), "No HAP detected"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                       params=TestModelHapPii.text_params,
                                       guardrails=True,
                                       )

            assert len(['Potentially harmful text detected' in str(warning.message) for warning in w]), \
                "No worning with HAP detection"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_08_generate_stream_guardrails_only(self, model):
        q = "Please repeat the word in [], do not trim space.\n[ foo.bar@ibm.com  I hate this damn world. ] "
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client,
            params=TestModelHapPii.text_params
        )


        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text_stream(prompt=q,
                                              guardrails=True
                                              )
            text_stream = list(text)
            print(text_stream)

            assert len(['Potentially harmful text detected' in str(warning.message) for warning in w]) or \
                   len(['Personally identifiable information detected' in str(warning.message) for warning in w]), \
                "No worning with HAP/PII detection"

    @pytest.mark.parametrize('model', available_models, ids=available_models)
    def test_09_generate_disable_guardrails(self, model):
        q = "Please repeat the words in [], do not trim space.\n[ I hate this damn world. ]"
        model = ModelInference(
            model_id=model,
            project_id=TestModelHapPii.project_id,
            api_client=TestModelHapPii.client,
            params=TestModelHapPii.text_params,
        )

        response = model.generate(prompt=q,
                                  guardrails=False)

        print(response['results'][0].get('moderations'))
        assert 'hap' not in response['results'][0].get('moderations', {}), "HAP detected, should be disabled"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            text = model.generate_text(prompt=q,
                                       params=TestModelHapPii.text_params,
                                       guardrails=False,
                                       )

            assert len(['Potentially harmful text detected' in str(warning.message) for warning in w]) == 0, \
                "HAP detected, should be disabled"