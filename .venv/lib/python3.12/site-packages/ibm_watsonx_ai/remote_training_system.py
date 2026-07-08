#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.remote_training_system import RemoteTrainingSystem

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class RemoteTrainingSystem(RemoteTrainingSystem):
    """The RemoteTrainingSystem class represents a Federated Learning party and provides a list of identities
    that are permitted to join training as the RemoteTrainingSystem.
    """
    pass