#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from typing import Literal, List, Union

from ibm_watsonx_ai._wrappers import requests
from ibm_watsonx_ai.wml_resource import WMLResource
from ibm_watsonx_ai.metanames import ParameterSetsMetaNames

_DEFAULT_LIST_LENGTH = 50


class ParameterSets(WMLResource):
    """Store and manage parameter sets."""

    ConfigurationMetaNames = ParameterSetsMetaNames()
    """MetaNames for Parameter Sets creation."""

    def __init__(self, client):
        WMLResource.__init__(self, __name__, client)
        self._ICP = client.ICP

    @staticmethod
    def _prepare_parameter_sets_payload(meta_data: dict) -> dict:
        payload = {
            "parameter_set": meta_data
        }

        return payload

    @staticmethod
    def _prepare_parameter_sets_payload_to_update(meta_data: Union[List, str], path: str, operation: str = "replace") -> list:
        payload = [
            {
                "op": operation,
                "path": f"/entity/parameter_set/{path}",
                "value": meta_data
            }
        ]
        return payload

    def get_details(self, parameter_set_id: str = None) -> dict:
        """Get parameter set details. If no parameter_sets_id is passed, details for all parameter sets
        will be returned.

        :param parameter_set_id: UID of software specification
        :type parameter_set_id: str, optional

        :return: metadata of the stored parameter set(s)
        :rtype:
          - **dict** - if `parameter_set_id` is not None
          - **{"parameter_sets": [dict]}** - if `parameter_set_id` is None

        **Examples**

        if `parameter_set_id` is None

        .. code-block:: python

            parameter_sets_details = client.parameter_sets.get_details()

        if `parameter_set_id` is given

        .. code-block:: python

            parameter_sets_details = client.parameter_sets.get_details(parameter_set_id)

        """
        ParameterSets._validate_type(parameter_set_id, u'sw_spec_uid', str, False)

        if parameter_set_id:
            try:  # TODO remove when get_parameter_sets_href() available
                href = self._client.service_instance._href_definitions.get_parameter_set_href(parameter_set_id)
            except AttributeError:
                href = f"{self._client.service_instance._href_definitions._get_platform_url_if_exists()}/v2/parameter_sets/{parameter_set_id}"

        else:
            try:  # TODO remove when get_parameter_sets_href() available
                href = self._client.service_instance._href_definitions.get_parameter_sets_href()
            except AttributeError:
                href = f"{self._client.service_instance._href_definitions._get_platform_url_if_exists()}/v2/parameter_sets"

        response = requests.get(url=href,
                                params=self._client._params(),
                                headers=self._client._get_headers())

        return self._handle_response(200, u'get parameter set(s) details', response)

    def create(self, meta_props: dict) -> dict:
        """Create a parameter set.

        :param meta_props: metadata of the space configuration. To see available meta names use:

            .. code-block:: python

                client.parameter_sets.ConfigurationMetaNames.get()

        :type meta_props: dict

        :return: metadata of the stored parameter set
        :rtype: dict

        **Example**

        .. code-block:: python

            meta_props = {
                client.parameter_sets.ConfigurationMetaNames.NAME: "Example name",
                client.parameter_sets.ConfigurationMetaNames.DESCRIPTION: "Example description",
                client.parameter_sets.ConfigurationMetaNames.PARAMETERS: [
                    {
                        "name": "string",
                        "description": "string",
                        "prompt": "string",
                        "type": "string",
                        "subtype": "string",
                        "value": "string",
                        "valid_values": [
                            "string"
                        ]
                    }
                ],
                client.parameter_sets.ConfigurationMetaNames.VALUE_SETS: [
                    {
                        "name": "string",
                        "values": [
                            {
                                "name": "string",
                                "value": "string"
                            }
                        ]
                    }
                ]
            }

            parameter_sets_details = client.parameter_sets.create(meta_props)
        """

        ParameterSets._validate_type(meta_props, u'meta_props', dict, True)

        parameter_sets_meta_data = self.ConfigurationMetaNames._generate_resource_metadata(
            meta_props,
            with_validation=True,
            client=self._client)

        payload = self._prepare_parameter_sets_payload(parameter_sets_meta_data)

        try:  # TODO remove when get_parameter_sets_href() available
            href = self._client.service_instance._href_definitions.get_parameter_sets_href()
        except AttributeError:
            href = f"{self._client.service_instance._href_definitions._get_platform_url_if_exists()}/v2/parameter_sets"

        creation_response = requests.post(url=href,
                                          json=payload,
                                          params=self._client._params(),
                                          headers=self._client._get_headers())

        parameter_sets_details = self._handle_response(201, u'creating parameter set', creation_response)

        return parameter_sets_details

    def list(self, limit: int = None, return_as_df: bool = True):
        """Print parameter sets in a table format.

        :param limit: limit number of fetched records
        :type limit: int, optional

        :param return_as_df: determinate if table should be returned as pandas.DataFrame object, default: True
        :type return_as_df: bool, optional

        :return: pandas.DataFrame with listed parameter sets or None if return_as_df is False
        :rtype: pandas.DataFrame or None

        **Example**

        .. code-block:: python

            client.parameter_sets.list()
        """

        try:  # TODO remove when get_parameter_sets_href() available
            href = self._client.service_instance._href_definitions.get_parameter_sets_href()
        except AttributeError:
            href = f"{self._client.service_instance._href_definitions._get_platform_url_if_exists()}/v2/parameter_sets"

        response = requests.get(url=href,
                                params=self._client._params(),
                                headers=self._client._get_headers())

        parameter_sets_details = self._handle_response(200, u'list assets', response)['parameter_sets']

        parameter_sets_values = [
            (m['metadata']['name'],
             m['metadata']['asset_id'],
             m['metadata']['create_time']) for m in parameter_sets_details]

        table = self._list(parameter_sets_values, ['NAME', 'ID', 'CREATED'], limit, _DEFAULT_LIST_LENGTH)

        if return_as_df:
            return table

    def delete(self, parameter_set_id: str):
        """Delete a parameter set.

        :param parameter_set_id: Unique id of parameter set
        :type parameter_set_id: str

        :return: status ("SUCCESS" or "FAILED")
        :rtype: str

        **Example**

        .. code-block:: python

            client.parameter_sets.delete(parameter_set_id)

        """
        ParameterSets._validate_type(parameter_set_id, u'sw_spec_uid', str, True)

        try:  # TODO remove when get_parameter_sets_href() available
            href = self._client.service_instance._href_definitions.get_parameter_set_href(parameter_set_id)
        except AttributeError:
            href = f"{self._client.service_instance._href_definitions._get_platform_url_if_exists()}/v2/parameter_sets/{parameter_set_id}"

        response = requests.delete(url=href,
                                   params=self._client._params(),
                                   headers=self._client._get_headers())

        if response.status_code == 200:
            return response.json()
        else:
            return self._handle_response(204, u'delete parameter set', response)

    def get_id_by_name(self, parameter_set_name: str) -> str:
        """Get Unique Id of parameter set.

        :param parameter_set_name: name of the parameter sets
        :type parameter_set_name: str

        :return: Unique Id of parameter set
        :rtype: str

        **Example**

        .. code-block:: python

            asset_uid = client.parameter_sets.get_id_by_name(parameter_set_name)

        """
        ParameterSets._validate_type(parameter_set_name, u'parameter_sets_id', str, True)

        details = self.get_details().get("parameter_sets") or []

        parameter_sets_id = [parameter["metadata"]['asset_id'] for parameter in details if
                             parameter["metadata"]["name"] == parameter_set_name]

        return parameter_sets_id[0] if parameter_sets_id else "Not Found"

    def update(self, parameter_set_id: str, new_data: Union[str, List],
               file_path: Literal["description", "parameters", "value_sets"]) -> dict:
        """Update parameter sets.

        :param parameter_set_id: Unique id of parameter sets
        :type parameter_set_id: str

        :param new_data: Parameters new data.
        :type new_data: str, list

        :param file_path: path to update
        :type file_path: str

        :return: metadata of updated parameter sets
        :rtype: dict

        **Example for description**

        .. code-block:: python

            new_description_data = "New description"
            parameter_set_details = client.parameter_sets.update(parameter_set_id, new_description_data, "description")

        **Example for parameters**

        .. code-block:: python

            new_parameters_data = [
                {
                    "name": "string",
                    "description": "new_description",
                    "prompt": "new_string",
                    "type": "new_string",
                    "subtype": "new_string",
                    "value": "new_string",
                    "valid_values": [
                        "new_string"
                    ]
                }
            ]
            parameter_set_details = client.parameter_sets.update(parameter_set_id, new_parameters_data, "parameters")

        **Example for value_sets**

        .. code-block:: python

            new_value_sets_data = [
                {
                    "name": "string",
                    "values": [
                        {
                            "name": "string",
                            "value": "new_string"
                        }
                    ]
                }
            ]
            parameter_set_details = client.parameter_sets.update_value_sets(parameter_set_id, new_value_sets_data, "value_sets")

        """
        ParameterSets._validate_type(parameter_set_id, u'sw_spec_uid', str, True)
        ParameterSets._validate_type(new_data, u'meta_props', [list, str], True)

        try:  # TODO remove when get_parameter_sets_href() available
            href = self._client.service_instance._href_definitions.get_parameter_set_href(parameter_set_id)
        except AttributeError:
            href = f"{self._client.service_instance._href_definitions._get_platform_url_if_exists()}/v2/parameter_sets/{parameter_set_id}"

        payload = self._prepare_parameter_sets_payload_to_update(meta_data=new_data, path=file_path)

        response = requests.patch(url=href,
                                  json=payload,
                                  params=self._client._params(),
                                  headers=self._client._get_headers())

        parameter_sets_details = self._handle_response(200, u'update parameter set', response)

        return parameter_sets_details
