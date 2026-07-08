#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.assets import Assets
from ibm_watsonx_ai.metanames import AssetsMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings


@change_docstrings
class Assets(Assets):
    """Store and manage data assets."""
    ConfigurationMetaNames = AssetsMetaNames()
    """MetaNames for Data Assets creation."""
