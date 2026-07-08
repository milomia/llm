#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.repository import Repository

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings


@change_docstrings
class Repository(Repository):
    """Store and manage models, functions, spaces, pipelines and experiments
    using watsonx.ai Repository.
    
    To view ModelMetaNames, use:

    .. code-block:: python

        client.repository.ModelMetaNames.show()

    To view ExperimentMetaNames, use:

    .. code-block:: python

        client.repository.ExperimentMetaNames.show()

    To view FunctionMetaNames, use:

    .. code-block:: python

        client.repository.FunctionMetaNames.show()

    To view PipelineMetaNames, use:

    .. code-block:: python

        client.repository.PipelineMetaNames.show()

    """
    pass