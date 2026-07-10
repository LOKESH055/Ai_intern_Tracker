# app/services/watsonx_client.py
import time
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from app.utils.config import Config


# System prompt that defines the assistant's personality and behavior
SYSTEM_PROMPT = """You are an expert AI career assistant specializing in internship discovery.

Your capabilities:
- Search and recommend internships based on user preferences
- Rank internships by skill match, company reputation, stipend, and growth potential
- Analyze resumes for ATS compatibility and skill gaps
- Help users prepare internship applications

Guidelines:
- Always be concise, helpful, and encouraging
- When listing internships, use clear structured formatting
- When ranking, always explain your reasoning
- Ask clarifying questions when the user's request is vague
- Remember context from earlier in the conversation

You are currently in a chat interface. Respond naturally and conversationally."""


# Models to try in order — primary first, then fallbacks if rate limited
FALLBACK_MODELS = [
    "meta-llama/llama-3-3-70b-instruct",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "meta-llama/llama-3-1-8b",
    "mistralai/mistral-medium-2505",
]


class WatsonxClient:
    def __init__(self):
        Config.validate()

        credentials = Credentials(
            url=Config.WATSONX_URL,
            api_key=Config.IBM_API_KEY,
        )

        self.api_client = APIClient(credentials)
        self.project_id = Config.WATSONX_PROJECT_ID

        # Build ordered model list — configured model first, then fallbacks
        # (avoiding duplicates while preserving order)
        self.models_to_try = [Config.WATSONX_MODEL_ID] + [
            m for m in FALLBACK_MODELS if m != Config.WATSONX_MODEL_ID
        ]

        # Create initial model instance using the primary model
        self.model = ModelInference(
            model_id=self.models_to_try[0],
            api_client=self.api_client,
            project_id=self.project_id,
            params={
                "max_new_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.9,
            }
        )

    def chat(self, messages: list[dict], status_callback=None) -> str:
        """
        Send a conversation to watsonx and get a response.
        Automatically retries with backup models if rate limited (429).

        messages format:
        [
            {"role": "user", "content": "Find me Data Science internships"},
            {"role": "assistant", "content": "Sure! Let me search for those..."},
            {"role": "user", "content": "Top 5 only please"}
        ]

        status_callback: optional function(str) to report progress,
                          e.g. a Streamlit spinner text updater
        """
        full_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + messages

        last_error = None

        for i, model_id in enumerate(self.models_to_try):
            # Swap model_id on the existing inference object
            try:
                self.model.model_id = model_id
            except Exception:
                # If swapping fails, recreate the ModelInference for this model
                self.model = ModelInference(
                    model_id=model_id,
                    api_client=self.api_client,
                    project_id=self.project_id,
                    params={
                        "max_new_tokens": 1024,
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                )

            for attempt in range(2):  # up to 2 attempts per model
                try:
                    if status_callback and i > 0:
                        status_callback(f"Primary model busy — trying backup model ({model_id.split('/')[-1]})...")

                    response = self.model.chat(messages=full_messages)
                    return response["choices"][0]["message"]["content"]

                except Exception as e:
                    last_error = e
                    err_str = str(e)

                    if "429" in err_str or "consumption_limit" in err_str:
                        # Rate limited — brief wait, then retry same model once,
                        # then move on to next model in the list
                        time.sleep(2)
                        continue
                    else:
                        # Non-rate-limit error — no point retrying this model
                        break

        return (
            "⚠️ All available models are currently rate limited by IBM's free tier. "
            "Please wait 1-2 minutes and try again.\n\n"
            f"(Last error: {str(last_error)})"
        )


# Singleton — created once and reused across the app session
_client_instance = None

def get_watsonx_client() -> WatsonxClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = WatsonxClient()
    return _client_instance