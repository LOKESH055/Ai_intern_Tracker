import os
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

credentials = Credentials(
    url=os.getenv("WATSONX_URL"),
    api_key=os.getenv("IBM_API_KEY"),
)

client = APIClient(credentials)

model = ModelInference(
    model_id="meta-llama/llama-3-3-70b-instruct",
    api_client=client,
    project_id=os.getenv("WATSONX_PROJECT_ID"),
    params={
        "max_new_tokens": 200,
        "temperature": 0.7,
    }
)

response = model.generate_text("List 3 skills important for a Data Science internship.")
print("✅ watsonx response:")
print(response)