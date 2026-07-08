#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.pkg_extn import PkgExtn
from ibm_watsonx_ai.metanames import PkgExtnMetaNames

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class PkgExtn(PkgExtn):
    """Store and manage software Packages Extension specs."""

    ConfigurationMetaNames = PkgExtnMetaNames()
    """MetaNames for Package Extensions creation."""