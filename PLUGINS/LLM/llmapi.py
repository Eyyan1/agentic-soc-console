import re
import os
import json

import httpx
import urllib3
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from Lib.log import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from PLUGINS.LLM.CONFIG import LLM_CONFIGS

FAKE_LLM_ENABLED = os.getenv("ASF_FAKE_LLM", "0") == "1"


def _is_placeholder_api_key(value: str | None) -> bool:
    api_key = str(value or "").strip().lower()
    if not api_key:
        return True
    return api_key.startswith("sk-local") or "placeholder" in api_key or api_key in {"changeme", "dummy", "none"}


def _should_use_fake_llm(selected_config: dict | None = None) -> bool:
    if os.getenv("ASF_FAKE_LLM", "0") == "1":
        return True
    if os.getenv("ASF_LOCAL_SIRP", "0") == "1" and selected_config:
        if selected_config.get("type") == "openai" and _is_placeholder_api_key(selected_config.get("api_key")):
            return True
    return FAKE_LLM_ENABLED


def _messages_to_text(messages) -> str:
    parts = []
    for message in messages:
        content = getattr(message, "content", message)
        if isinstance(content, list):
            parts.append(json.dumps(content, ensure_ascii=False))
        else:
            parts.append(str(content))
    return "\n".join(parts)


def _detect_email_phishing(text: str) -> bool:
    suspicious_tokens = [
        "spf=fail",
        "dkim=fail",
        "dmarc=fail",
        "urgent",
        "verify your identity",
        "account suspended",
        "reset-password",
        "phish",
        "mailbox-upgrade-secure",
        "delivery-fee-update",
    ]
    text_lower = text.lower()
    return any(token in text_lower for token in suspicious_tokens)


class _FakeStructuredModel:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, messages):
        text = _messages_to_text(messages)
        schema_name = self.schema.__name__
        if schema_name == "AnalyzeResult":
            fields = getattr(self.schema, "model_fields", {})
            if "is_phishing" in fields:
                is_phishing = _detect_email_phishing(text)
                confidence = "High" if is_phishing else "Medium"
                reasoning = (
                    "Detected phishing indicators in sender domain, authentication failures, urgency wording, and suspicious links."
                    if is_phishing else
                    "No strong phishing indicators were found in the sample. Treating as benign for local testing."
                )
                return self.schema(is_phishing=is_phishing, confidence=confidence, reasoning=reasoning)

            if "new_severity" in fields:
                text_lower = text.lower()
                if "cobalt strike" in text_lower or "command and control" in text_lower or "privilege escalation" in text_lower:
                    return self.schema(
                        original_severity="high",
                        new_severity="Critical",
                        confidence="High",
                        analysis_rationale="Local fake LLM classified the alert as high-risk based on attack-pattern keywords present in the payload.",
                        attack_stage="Command and Control" if "command and control" in text_lower else "Privilege Escalation",
                        recommended_actions="Isolate the affected asset and investigate surrounding activity."
                    )
                return self.schema(
                    original_severity="Medium",
                    new_severity="Medium",
                    confidence="Medium",
                    analysis_rationale="Local fake LLM returned a conservative result for development testing.",
                    attack_stage="Discovery",
                    recommended_actions="Review the alert and confirm supporting evidence."
                )
        return self.schema()


class _FakeToolModel:
    def __init__(self, tools):
        self.tools = tools

    def invoke(self, messages):
        text = _messages_to_text(messages)
        args = {
            "original_severity": "High" if "severity" in text.lower() else "Medium",
            "new_severity": "High",
            "confidence": "Medium",
            "analysis_rationale": "Local fake LLM finalized the case analysis without external tool calls.",
            "attack_stage": "Command and Control" if "command and control" in text.lower() else "Privilege Escalation",
            "recommended_actions": "Review linked alerts, isolate affected assets if needed, and confirm follow-up actions."
        }
        return AIMessage(content="", tool_calls=[{"name": "AnalyzeResult", "args": args, "id": "fake-tool-call-1", "type": "tool_call"}])


class _FakeChatModel:
    def with_structured_output(self, schema):
        return _FakeStructuredModel(schema)

    def bind_tools(self, tools):
        return _FakeToolModel(tools)


class LLMAPI(object):
    """
    A general-purpose LLM API client.
    It automatically reads the configuration from CONFIG.py and initializes the corresponding backend.
    Supports dynamic selection of model configurations through tags.
    It throws exceptions directly when it encounters an error.
    """

    def __init__(self, temperature: float = 0.0):
        """
        Initializes the LLM API client.
        Loads the configuration list from LLM_CONFIGS in CONFIG.py.
        """
        if not LLM_CONFIGS or not isinstance(LLM_CONFIGS, list):
            raise ValueError("LLM_CONFIGS in CONFIG.py is missing, empty, or not a list.")

        self.configs = LLM_CONFIGS
        self.default_config = self.configs[0]
        self.temperature = temperature
        self.alive = False

    def get_model(self, tag: str | list[str] | None = None, **kwargs) -> ChatOpenAI | ChatOllama:
        """
        Gets and returns the corresponding LangChain ChatModel instance based on the tag.

        Args:
            tag (str | list[str], optional):
                - str: Find the first configuration that contains this tag.
                - list[str]: Find the first configuration that contains all of these tags.
                - None: Use the first default configuration in the list.
            **kwargs: Allows overriding model parameters at call time (e.g., temperature, model).

        Raises:
            ValueError: If no configuration matching the specified tag (or list of tags) is found.
            ValueError: If the client_type in the configuration is not supported.

        Returns:
            ChatOpenAI | ChatOllama: LangChain's chat model instance.
        """
        selected_config = None

        if tag is None:
            selected_config = self.default_config
        else:
            for config in self.configs:
                config_tags = set(config.get("tags", []))

                # If tag is a list, check if all required tags exist
                if isinstance(tag, list):
                    required_tags = set(tag)
                    if required_tags.issubset(config_tags):
                        selected_config = config
                        break
                # If tag is a string, check if the tag exists
                elif isinstance(tag, str):
                    if tag in config_tags:
                        selected_config = config
                        break

        if selected_config is None:
            raise ValueError(f"No LLM configuration found matching tag(s): '{tag}'")

        if _should_use_fake_llm(selected_config):
            logger.info(
                "Using fake local LLM backend for tags %s.",
                tag if tag is not None else "[default]",
            )
            return _FakeChatModel()

        logger.debug(
            f"Using LLM configuration, base_url: {selected_config.get('base_url')} "
            f"model: {selected_config.get('model')}"
        )
        # Prepare model parameters
        params = {
            "temperature": self.temperature,
            "model": selected_config.get("model"),
        }
        # Update kwargs to allow overriding default values at runtime
        params.update(kwargs)

        client_type = selected_config.get("type")

        if client_type == 'openai':
            params.update({
                "base_url": selected_config.get("base_url"),
                "api_key": selected_config.get("api_key"),
                "http_client": httpx.Client(proxy=selected_config.get("proxy")) if selected_config.get("proxy") else None,
            })
            return ChatOpenAI(**params)

        elif client_type == 'ollama':
            params.update({
                "base_url": selected_config.get("base_url"),
            })
            # Ollama doesn't use api_key or http_client in the same way
            return ChatOllama(**params)
        else:
            raise ValueError(f"Unsupported client_type: {client_type}")

    def alive_check(self):
        for config in self.configs:
            if _should_use_fake_llm(config):
                print(f"{config} is using fake local LLM backend.")
                continue
            params = {
                "temperature": self.temperature,
                "model": config.get("model"),
            }
            client_type = config.get("type")
            if client_type == 'openai':
                params.update({
                    "base_url": config.get("base_url"),
                    "api_key": config.get("api_key"),
                    "http_client": httpx.Client(proxy=config.get("proxy")) if config.get("proxy") else None,
                })
                model = ChatOpenAI(**params)
                if self.is_alive(model):
                    print(f"{config} is alive.")
                else:
                    print(f"{config} is not alive.")

            elif client_type == 'ollama':
                params.update({
                    "base_url": config.get("base_url"),
                })
                model = ChatOllama(**params)
                if self.is_alive(model):
                    print(f"{config} is alive.")
                else:
                    print(f"{config} is not alive.")
            else:
                print(f"{config} error")

    def is_alive(self, model: ChatOpenAI | ChatOllama) -> bool:
        """
        Tests basic connectivity with the default model.
        Returns True on success, otherwise throws an exception directly (e.g., ConnectionError, ValueError).
        """
        parser = StrOutputParser()
        chain = model | parser
        messages = [
            ("system", "When you receive 'ping', you must reply with 'pong'."),
            ("human", "ping"),
        ]

        # Any network or API errors will be thrown here naturally as exceptions
        ai_msg = chain.invoke(messages)

        if "pong" not in ai_msg.lower():
            # Even if the connection is successful, but the response does not meet expectations, it is considered a failure
            self.alive = False
            raise ValueError(f"Model liveness check failed. Expected 'pong', got: {ai_msg}")

        self.alive = True
        return True

    def is_support_function_calling(self, tag: str = None) -> bool:
        """
        Tests whether the specified (or default) model supports function calling (Tool Calling) capabilities.
        Returns True on success, otherwise throws an exception directly.
        """

        def test_func(x: str) -> str:
            """A test function that returns the input string."""
            return x

        model = self.get_model(tag=tag)
        model_with_tools = model.bind_tools([test_func])
        test_messages = [
            ("system", "When user says test, call test_func with 'hello' as argument."),
            ("human", "test"),
        ]

        response = model_with_tools.invoke(test_messages)

        if not response.tool_calls:
            raise ValueError("Model responded but did not use the requested tool.")

        return True

    @staticmethod
    def extract_think(message: AIMessage) -> AIMessage:
        """
        Checks if a <think>...</think> tag exists at the beginning of the AIMessage content.
        Temporary solution for a Langchain Bug
        If it exists, it will:
        1. Extract the content within the <think> tag.
        2. Store the extracted content in message.additional_kwargs['reasoning_content'].
        3. Remove the <think>...</think> tag block from message.content.
        4. Return a new, modified AIMessage object.

        If it does not exist, the original message object is returned as is.

        Args:
            message: The LangChain AIMessage object to be processed.

        Returns:
            A processed AIMessage object, or the original object if there is no match.
        """
        # Ensure content is a string type
        if not isinstance(message.content, str):
            return message

        # Regular expression to match the <think> tag at the beginning and capture its content.
        # The re.DOTALL flag allows '.' to match any character, including newlines.
        # `^`      - matches the beginning of the string
        # `<think>`- matches the literal <think>
        # `(.*?)`  - non-greedily captures all characters until the next pattern
        # `</think>`- matches the literal </think>
        # `\s*`    - matches any whitespace characters (including newlines) after the think tag
        pattern = r"^<think>(.*?)</think>\s*"

        match = re.match(pattern, message.content, re.DOTALL)

        if match:
            # Extract the content of capture group 1, which is the text inside the <think> tag
            reasoning_content = match.group(1).strip()

            # Remove the entire matched <think>...</think> part from the original content
            new_content = message.content[match.end():]

            # Create a copy of additional_kwargs for modification
            # This is to avoid directly modifying the original dictionary that may be referenced elsewhere
            updated_kwargs = message.additional_kwargs.copy()
            updated_kwargs['reasoning_content'] = reasoning_content

            # Return a new AIMessage instance because LangChain message objects are immutable
            message.additional_kwargs = updated_kwargs
            message.content = new_content
            return message
        else:
            # If there is no match, return the original message
            return message


if __name__ == "__main__":
    LLMAPI().alive_check()
