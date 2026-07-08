#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.experiments import Experiments
from ibm_watsonx_ai.metanames import ExperimentMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class Experiments(Experiments):
    """Run new experiment."""

    ConfigurationMetaNames = ExperimentMetaNames()
    """MetaNames for experiments creation."""
