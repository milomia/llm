#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.hw_spec import HwSpec
from ibm_watsonx_ai.metanames import HwSpecMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class HwSpec(HwSpec):
    """Store and manage hardware specs."""
    ConfigurationMetaNames = HwSpecMetaNames()
    """MetaNames for Hardware Specification."""