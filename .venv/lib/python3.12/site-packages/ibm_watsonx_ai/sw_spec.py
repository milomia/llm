#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.sw_spec import SwSpec
from ibm_watsonx_ai.metanames import SwSpecMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class SwSpec(SwSpec):
    """Store and manage software specs."""

    ConfigurationMetaNames = SwSpecMetaNames()
    """MetaNames for Software Specification creation."""
