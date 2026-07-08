#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.migration_v4ga_cloud import Migrationv4GACloud

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class Migrationv4GACloud(Migrationv4GACloud):
    """Migration APIs for v4 GA Cloud. This will be applicable only till the migration period.
    Refer to the documentation at 'https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/wml-ai.html'
    for details on migration.
    """
    pass