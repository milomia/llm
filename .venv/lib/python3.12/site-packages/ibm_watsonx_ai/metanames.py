#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from ibm_watson_machine_learning.metanames import (MetaProp, MetaNamesBase,
                                                   TrainingConfigurationMetaNames, TrainingConfigurationMetaNamesCp4d30,
                                                   ExperimentMetaNames, PipelineMetanames,
                                                   LearningSystemMetaNames, MemberMetaNames,
                                                   ModelMetaNames, PayloadLoggingMetaNames,
                                                   FunctionMetaNames, FunctionNewMetaNames,
                                                   ScoringMetaNames, DecisionOptimizationMetaNames,
                                                   RuntimeMetaNames, LibraryMetaNames,
                                                   SpacesMetaNames, ExportMetaNames,
                                                   SpacesPlatformMetaNames, SpacesPlatformMemberMetaNames,
                                                   AssetsMetaNames, SwSpecMetaNames,
                                                   ScriptMetaNames, ShinyMetaNames,
                                                   PkgExtnMetaNames, HwSpecMetaNames,
                                                   ModelDefinitionMetaNames, ConnectionMetaNames,
                                                   DeploymentMetaNames, DeploymentNewMetaNames,
                                                   Migrationv4GACloudMetaNames, RemoteTrainingSystemMetaNames,
                                                   ExportMetaNames, VolumeMetaNames,
                                                   GenTextParamsMetaNames, GenTextReturnOptMetaNames,
                                                   FactsheetsMetaNames, GenTextModerationsMetaNames)

from ibm_watsonx_ai.utils.change_methods_docstring import change_docstrings

@change_docstrings
class MetaProp(MetaProp):
   __doc__ = MetaProp.__doc__
       
@change_docstrings
class MetaNamesBase(MetaNamesBase):
    __doc__ = MetaNamesBase.__doc__

class TrainingConfigurationMetaNames(TrainingConfigurationMetaNames):
    __doc__ = TrainingConfigurationMetaNames.__doc__

class TrainingConfigurationMetaNamesCp4d30(TrainingConfigurationMetaNamesCp4d30):
    __doc__ = TrainingConfigurationMetaNamesCp4d30.__doc__

class ExperimentMetaNames(ExperimentMetaNames):
    __doc__ = ExportMetaNames.__doc__

class PipelineMetanames(PipelineMetanames):
    __doc__ = PipelineMetanames.__doc__

class LearningSystemMetaNames(LearningSystemMetaNames):
    __doc__ = LearningSystemMetaNames.__doc__

class MemberMetaNames(MemberMetaNames):
    __doc__ = MemberMetaNames.__doc__

class ModelMetaNames(ModelMetaNames):
    __doc__ = ModelMetaNames.__doc__
    
class PayloadLoggingMetaNames(PayloadLoggingMetaNames):
    __doc__ = PayloadLoggingMetaNames.__doc__

class FunctionMetaNames(FunctionMetaNames):
    __doc__ = FunctionMetaNames.__doc__

class FunctionNewMetaNames(FunctionNewMetaNames):
    __doc__ = FunctionNewMetaNames.__doc__

class ScoringMetaNames(ScoringMetaNames):
    __doc__ = ScoringMetaNames.__doc__

class DecisionOptimizationMetaNames(DecisionOptimizationMetaNames):
    __doc__ = DecisionOptimizationMetaNames.__doc__

class RuntimeMetaNames(RuntimeMetaNames):
    __doc__ = RuntimeMetaNames.__doc__

class LibraryMetaNames(LibraryMetaNames):
    __doc__ = LibraryMetaNames.__doc__

class SpacesMetaNames(SpacesMetaNames):
    __doc__ = SpacesMetaNames.__doc__

class ExportMetaNames(ExportMetaNames):
    __doc__ = ExportMetaNames.__doc__

class SpacesPlatformMetaNames(SpacesPlatformMetaNames):
    __doc__ = SpacesPlatformMetaNames.__doc__

class SpacesPlatformMemberMetaNames(SpacesPlatformMemberMetaNames):
    __doc__ = SpacesPlatformMemberMetaNames.__doc__

class AssetsMetaNames(AssetsMetaNames):
   __doc__ = AssetsMetaNames.__doc__


## update this later #Todo
class SwSpecMetaNames(SwSpecMetaNames):
    __doc__ = SwSpecMetaNames.__doc__

class ScriptMetaNames(ScriptMetaNames):
    __doc__ = ScriptMetaNames.__doc__

class ShinyMetaNames(ShinyMetaNames):
    __doc__ = ShinyMetaNames.__doc__

class PkgExtnMetaNames(PkgExtnMetaNames):
    __doc__ = PkgExtnMetaNames.__doc__

## update this later #Todo
class HwSpecMetaNames(HwSpecMetaNames):
    __doc__ = HwSpecMetaNames.__doc__

class ModelDefinitionMetaNames(ModelDefinitionMetaNames):
    __doc__ = ModelDefinitionMetaNames.__doc__

class ConnectionMetaNames(ConnectionMetaNames):
    __doc__ = ConnectionMetaNames.__doc__

class DeploymentMetaNames(DeploymentMetaNames):
    __doc__ = DeploymentMetaNames.__doc__

class DeploymentNewMetaNames(DeploymentNewMetaNames):
    __doc__ = DeploymentNewMetaNames.__doc__

class Migrationv4GACloudMetaNames(Migrationv4GACloudMetaNames):
    __doc__ = Migrationv4GACloudMetaNames.__doc__

class RemoteTrainingSystemMetaNames(RemoteTrainingSystemMetaNames):
    __doc__ = RemoteTrainingSystemMetaNames.__doc__

class ExportMetaNames(ExportMetaNames):
    __doc__ = ExportMetaNames.__doc__

class VolumeMetaNames(VolumeMetaNames):
    __doc__ = VolumeMetaNames.__doc__

class FactsheetsMetaNames(FactsheetsMetaNames):
    __doc__ = FactsheetsMetaNames.__doc__

class FactsheetsMetaNames(MetaNamesBase):

    ASSET_ID = "model_entry_asset_id"
    NAME = "model_entry_name"
    DESCRIPTION = "model_entry_description"
    MODEL_ENTRY_CATALOG_ID = "model_entry_catalog_id"

    _meta_props_definitions = [
        MetaProp('ASSET_ID', ASSET_ID, str, False, '13a53931-a8c0-4c2f-8319-c793155e7517'),
        MetaProp('NAME', NAME, str, False,  example_value="New model entry"),
        MetaProp('DESCRIPTION', DESCRIPTION, str, False, example_value='New model entry'),
        MetaProp('MODEL_ENTRY_CATALOG_ID', MODEL_ENTRY_CATALOG_ID, str, True, example_value='13a53931-a8c0-4c2f-8319-c793155e7517')
    ]

    __doc__ = MetaNamesBase(_meta_props_definitions)._generate_doc('Factsheets metanames')

    def __init__(self):
        MetaNamesBase.__init__(self, self._meta_props_definitions)


class GenTextParamsMetaNames(MetaNamesBase):
    DECODING_METHOD = "decoding_method"
    LENGTH_PENALTY = "length_penalty"
    TEMPERATURE = "temperature"
    TOP_P = "top_p"
    TOP_K = "top_k"
    RANDOM_SEED = "random_seed"
    REPETITION_PENALTY = "repetition_penalty"
    MIN_NEW_TOKENS = "min_new_tokens"
    MAX_NEW_TOKENS = "max_new_tokens"
    STOP_SEQUENCES = "stop_sequences"
    TIME_LIMIT = " time_limit"
    TRUNCATE_INPUT_TOKENS = "truncate_input_tokens"
    RETURN_OPTIONS = "return_options"

    _meta_props_definitions = [
        MetaProp('DECODING_METHOD',       DECODING_METHOD,       str,      False, "sample"),
        MetaProp('LENGTH_PENALTY',        LENGTH_PENALTY,        dict,     False, {"decay_factor": 2.5, "start_index": 5}),
        MetaProp('TEMPERATURE',           TEMPERATURE,           float,    False, 0.5),
        MetaProp('TOP_P',                 TOP_P,                 float,    False, 0.2),
        MetaProp('TOP_K',                 TOP_K,                 int,      False, 1),
        MetaProp('RANDOM_SEED',           RANDOM_SEED,           int,      False, 33),
        MetaProp('REPETITION_PENALTY',    REPETITION_PENALTY,    float,    False, 2),
        MetaProp('MIN_NEW_TOKENS',        MIN_NEW_TOKENS,        int,      False, 50),
        MetaProp('MAX_NEW_TOKENS',        MAX_NEW_TOKENS,        int,      False, 200),
        MetaProp('STOP_SEQUENCES',        STOP_SEQUENCES,        list,     False, ["fail"]),
        MetaProp('TIME_LIMIT',            TIME_LIMIT,            int,      False, 600000),
        MetaProp('TRUNCATE_INPUT_TOKENS', TRUNCATE_INPUT_TOKENS, int,      False, 200),
        MetaProp('RETURN_OPTIONS',        RETURN_OPTIONS,        dict,     False, {"input_text": True,
                                                                                   "generated_tokens": True,
                                                                                   "input_tokens": True,
                                                                                   "token_logprobs": True,
                                                                                   "token_ranks": False,
                                                                                   "top_n_tokens": False
                                                                                   })
    ]

    __doc__ = MetaNamesBase(_meta_props_definitions)._generate_doc('Foundation Model Parameters')

    def __init__(self):
        MetaNamesBase.__init__(self, self._meta_props_definitions)

class GenTextModerationsMetaNames(MetaNamesBase):
    INPUT = "input"
    OUTPUT = "output"
    THRESHOLD = "threshold"
    MASK = "mask"

    _meta_props_definitions = [
        MetaProp('INPUT',                INPUT,                bool,      False, False),
        MetaProp('OUTPUT',               OUTPUT,               bool,      False, False),
        MetaProp('THRESHOLD',            THRESHOLD,            float,     False, 0.5),
        MetaProp('MASK',                 MASK,                 dict,      False, {'remove_entity_value': True}),
    ]

    __doc__ = MetaNamesBase(_meta_props_definitions)._generate_doc('Generation Text Moderations Parameters')

    def __init__(self):
        MetaNamesBase.__init__(self, self._meta_props_definitions)
        
class GenTextReturnOptMetaNames(MetaNamesBase):
    INPUT_TEXT = "input_text"
    GENERATED_TOKENS = "generated_tokens"
    INPUT_TOKENS = "input_tokens"
    TOKEN_LOGPROBS = "token_logprobs"
    TOKEN_RANKS = "token_ranks"
    TOP_N_TOKENS = "top_n_tokens"

    _meta_props_definitions = [
        MetaProp('INPUT_TEXT',             INPUT_TEXT,       bool, True,  True),
        MetaProp('GENERATED_TOKENS',       GENERATED_TOKENS, bool, False, True),
        MetaProp('INPUT_TOKENS',           INPUT_TOKENS,     bool, True,  True),
        MetaProp('TOKEN_LOGPROBS',         TOKEN_LOGPROBS,   bool, False, True),
        MetaProp('TOKEN_RANKS',            TOKEN_RANKS,      bool, False, True),
        MetaProp('TOP_N_TOKENS',           TOP_N_TOKENS,      int, False, True)
    ]

    __doc__ = MetaNamesBase(_meta_props_definitions)._generate_doc(
        'Foundation Model Parameters',
        note="One of these parameters is required: ['INPUT_TEXT', 'INPUT_TOKENS']")

    def __init__(self):
        MetaNamesBase.__init__(self, self._meta_props_definitions)


class ParameterSetsMetaNames(MetaNamesBase):
    NAME = "name"
    DESCRIPTION = "description"
    PARAMETERS = "parameters"
    VALUE_SETS = "value_sets"

    _meta_props_definitions = [
        MetaProp('NAME',        NAME,        str,  True,  "sample name"),
        MetaProp('DESCRIPTION', DESCRIPTION, str,  False, "sample description"),
        MetaProp('PARAMETERS',  PARAMETERS,  list, True,  [{"name": "string", "description": "string", "prompt": "string", "type": "string", "subtype": "string", "value": "string", "valid_values": ["string"]}]),
        MetaProp('VALUE_SETS',  VALUE_SETS,  list, False, [{"name": "string", "values": [{"name": "string", "value": "string"}]}])
    ]

    __doc__ = MetaNamesBase(_meta_props_definitions)._generate_doc('Parameter Sets metanames')

    def __init__(self):
        MetaNamesBase.__init__(self, self._meta_props_definitions)
