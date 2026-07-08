#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.model_definition import ModelDefinition
from ibm_watsonx_ai.metanames import ModelDefinitionMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class ModelDefinition(ModelDefinition):
    """Store and manage model definitions."""

    ConfigurationMetaNames = ModelDefinitionMetaNames()

    """MetaNames for model definition creation."""