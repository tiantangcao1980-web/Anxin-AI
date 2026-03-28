from camel.configs import ChatGPTConfig
from camel.models import OpenAIModel, ModelFactory
from camel.types import ModelType, ModelPlatformType
import os

os.environ["OPENAI_API_KEY"] = "sk-dummy"

print("ChatGPTConfig default:", ChatGPTConfig().as_dict())

try:
    print("\nTesting OpenAIModel directly:")
    model = OpenAIModel(model_type=ModelType.GPT_4O, model_config_dict={'temperature': 0.7})
    print("Model initialized")
    config = model._prepare_request_config(None)
    print("Prepared config:", config)

    print("\nTesting ModelFactory:")
    model_factory = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={'temperature': 0.7},
        api_key="sk-dummy"
    )
    print("Factory model created")
    config_factory = model_factory._prepare_request_config(None)
    print("Factory prepared config:", config_factory)

except Exception as e:
    print("Error:", e)
