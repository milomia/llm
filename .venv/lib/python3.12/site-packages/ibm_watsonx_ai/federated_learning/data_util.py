#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

"""
Module providing utility functions helpful for preproccessing data
"""

from ibm_watson_machine_learning.federated_learning import data_util

# TODO get dp stats

from inspect import getmembers, isfunction

from ibm_watsonx_ai.utils.change_methods_docstring import copy_func
import sys

for function in getmembers(data_util, isfunction):
    if "ibm_watson_machine_learning" in function[1].__module__:
        sys.modules[__name__].__dict__[function[0]] = copy_func(function[1])