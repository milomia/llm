#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.federated_learning.data_handler import DataHandler

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class DataHandler(DataHandler):
    """
    Base class to load and pre-process data.
    """
    pass