#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.script import Script
from ibm_watsonx_ai.metanames import ScriptMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class Script(Script):
    """Store and manage scripts assets."""

    ConfigurationMetaNames = ScriptMetaNames()
    """MetaNames for script assets creation."""