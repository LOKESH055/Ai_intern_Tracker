# app/utils/config.py
# app/utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # IBM watsonx
    IBM_API_KEY = os.getenv("IBM_API_KEY")
    WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
    WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

    # RapidAPI
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

    # IBM Cloud Object Storage
    COS_API_KEY = os.getenv("COS_API_KEY", "")
    COS_INSTANCE_ID = os.getenv("COS_INSTANCE_ID", "")
    COS_ENDPOINT = os.getenv("COS_ENDPOINT", "")
    COS_BUCKET = os.getenv("COS_BUCKET", "internship-assistant-resumes")

    # IBM Cloudant
    CLOUDANT_APIKEY = os.getenv("CLOUDANT_APIKEY", "")
    CLOUDANT_URL = os.getenv("CLOUDANT_URL", "")

    # Email (Phase 7)
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.IBM_API_KEY:
            missing.append("IBM_API_KEY")
        if not cls.WATSONX_PROJECT_ID:
            missing.append("WATSONX_PROJECT_ID")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )