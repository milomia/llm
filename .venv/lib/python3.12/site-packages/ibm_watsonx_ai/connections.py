#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.connections import Connections
from ibm_watsonx_ai.metanames import ConnectionMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class Connections(Connections):
    """Store and manage Connections."""
    ConfigurationMetaNames = ConnectionMetaNames()
    """MetaNames for Connection creation."""