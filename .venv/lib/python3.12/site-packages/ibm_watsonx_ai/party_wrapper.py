#!/usr/bin/env python3

#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.party_wrapper import Party

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings


@change_docstrings
class Party(Party):
    """The Party class embodies a Federated Learning party, with methods to run, cancel, and query local training.
    Refer to the ``client.remote_training_system.create_party()`` API for more information about creating an
    instance of the Party class. 
    """
    pass