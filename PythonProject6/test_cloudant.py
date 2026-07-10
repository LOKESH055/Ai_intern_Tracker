from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from dotenv import load_dotenv
import os

load_dotenv()

authenticator = IAMAuthenticator(os.getenv("CLOUDANT_APIKEY"))
client = CloudantV1(authenticator=authenticator)
client.set_service_url(os.getenv("CLOUDANT_URL"))

response = client.get_server_information().get_result()
print("Cloudant connected! Version:", response["version"])