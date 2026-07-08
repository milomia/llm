#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.pipelines import Pipelines
from ibm_watsonx_ai.metanames import PipelineMetanames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class Pipelines(Pipelines):
    """Store and manage pipelines."""

    ConfigurationMetaNames = PipelineMetanames()
    """MetaNames for pipelines creation."""