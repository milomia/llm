#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.models import Models
from ibm_watsonx_ai.metanames import ModelMetaNames, LibraryMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings


@change_docstrings
class Models(Models):
    """Store and manage models."""

    ConfigurationMetaNames = ModelMetaNames()
    """MetaNames for models creation."""

    LibraryMetaNames = LibraryMetaNames()
    """MetaNames for libraries creation."""
