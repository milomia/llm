#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.wml_client_error import *

__all__ = [
    "WMLClientError",
    "MissingValue",
    "MissingMetaProp",
    "NotUrlNorUID",
    "ApiRequestFailure",
    "UnexpectedType",
    "ForbiddenActionForPlan",
    "NoVirtualDeploymentSupportedForICP",
    "MissingArgument",
    "WrongEnvironmentVersion",
    "CannotAutogenerateBedrockUrl",
    "WrongMetaProps",
    "CannotSetProjectOrSpace",
    "ForbiddenActionForGitBasedProject",
    "CannotInstallLibrary",
    "DataStreamError",
    "WrongLocationProperty",
    "WrongFileLocation",
    "EmptyDataSource",
    "SpaceIDandProjectIDCannotBeNone",
    "ParamOutOfRange",
    "InvalidMultipleArguments",
    "ValidationError",
    "InvalidValue",
    "PromptVariablesError",
    "UnsupportedOperation",
]


class ParamOutOfRange(WMLClientError, ValueError):
    def __init__(self, param_name, value, min, max):
        WMLClientError.__init__(self,
                                f"Value of parameter `{param_name}`, {value}, is out of expected range - between {min} and {max}.")

class InvalidMultipleArguments(WMLClientError, ValueError):
    def __init__(self, params_names_list, reason=None):
        WMLClientError.__init__(self, f"One of {params_names_list} parameters should be set.", reason)       

class ValidationError(WMLClientError, KeyError):
    def __init__(self, key: str):
        WMLClientError.__init__(self, (f"Invalid prompt template; check for"
                                       f" mismatched or missing input variables." 
                                       f" Missing input variable: {key}"))
class PromptVariablesError(WMLClientError, KeyError):
    def __init__(self, key: str):
        WMLClientError.__init__(self, (f"Prompt template contains input variables." 
                                       f" Missing {key} in `prompt_variables`"))
        
class InvalidValue(WMLClientError, ValueError):
    def __init__(self, value_name, reason=None):
        WMLClientError.__init__(self, 'Inappropriate value of \"' + value_name + '\"', reason)

class UnsupportedOperation(WMLClientError):
    def __init__(self, reason):
        WMLClientError.__init__(self, f"Operation is unsupported for this release.", reason)