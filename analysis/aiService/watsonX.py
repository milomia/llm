# import os
#
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from dotenv import load_dotenv
# from langchain_ibm import WatsonxLLM
# from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
# from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
# from analysis.models import llmModel
#
# from analysis.models import llmModel
#
# load_dotenv()
#
#
# WATSONX_APIKEY = os.getenv('WATSONX_APIKEY')
# PROJECT_ID = os.getenv('PROJECT_ID')
# IBM_WATSONX_URL = os.getenv('IBM_WATSONX_URL')
# BASE_MODEL_ID = llmModel.objects.filter(active=True).first().ibm_name
# print('BASE_MODEL_ID initiation: '+ BASE_MODEL_ID)
# credentials = {
#     "url": IBM_WATSONX_URL,
#     "apikey": WATSONX_APIKEY
# }
# parameters = {
#     GenParams.DECODING_METHOD: DecodingMethods.GREEDY.value,
#     GenParams.MAX_NEW_TOKENS: 4000,
#     GenParams.MIN_NEW_TOKENS: 50,
#     GenParams.TEMPERATURE: 0.4,
# }
#
#
# # mixtralLLM = ""
# mixtralLLM = WatsonxLLM(
#     model_id=BASE_MODEL_ID,
#     url=credentials["url"],
#     apikey=credentials["apikey"],
#     project_id=PROJECT_ID,
#     params=parameters
#     )
#
#
# @receiver(post_save, sender=llmModel)
# def post_save_handler(sender, instance, created,  **kwargs):
#     global mixtralLLM  # Declare mixtralLLM as global
#     if instance.active:
#         llmModel.objects.all().exclude(pk=instance.pk).update(active=False)
#         mixtralLLM = WatsonxLLM(
#             model_id=instance.ibm_name,
#             url=credentials["url"],
#             apikey=credentials["apikey"],
#             project_id=PROJECT_ID,
#             params=parameters
#         )
#         print("new llm model to be used: " + str(mixtralLLM.model_id))
#
# print(mixtralLLM)
#
# def getLLM():
#     return mixtralLLM