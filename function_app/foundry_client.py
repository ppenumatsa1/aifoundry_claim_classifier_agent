import os
import json

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

try:
    from .logging_config import setup_logger
except (ImportError, ModuleNotFoundError):
    from logging_config import setup_logger

# Load environment variables from .env file
load_dotenv()

logger = setup_logger(__name__)


class FoundryClient:
    """Wrapper for Azure AI Foundry Agent operations."""

    def __init__(self):
        self.endpoint = os.environ["PROJECT_ENDPOINT"]
        self.model_deployment = os.environ["MODEL_DEPLOYMENT_NAME"]
        logger.info(
            f"Initializing FoundryClient with endpoint: {self.endpoint}, model: {self.model_deployment}"
        )

        # Using DefaultAzureCredential for authentication
        try:
            self.client = AIProjectClient(
                endpoint=self.endpoint, credential=DefaultAzureCredential()
            )
            logger.info("Successfully created AIProjectClient")
        except Exception as e:
            logger.error(f"Failed to create AIProjectClient: {e}")
            raise

        # Create or get the claims classifier agent
        self.agent = self._setup_classifier_agent()

    def _setup_classifier_agent(self):
        """Create or get the claims classifier agent with system instructions."""
        logger.info("Setting up claims classifier agent")

        # Read the classification prompt
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "classification_prompt.txt"
        )
        logger.debug(f"Loading prompt from: {prompt_path}")

        try:
            with open(prompt_path, "r") as f:
                system_instructions = f.read()
            logger.info(
                f"Loaded system instructions ({len(system_instructions)} characters)"
            )
        except Exception as e:
            logger.error(
                f"Failed to read classification prompt from {prompt_path}: {e}"
            )
            raise

        # Create the agent with system instructions
        try:
            agent = self.client.agents.create_agent(
                model=self.model_deployment,
                name="Claims Fraud Classifier",
                instructions=system_instructions,
            )
            logger.info(f"Successfully created agent with ID: {agent.id}")
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise

    def classify_claims(self, claim_texts: list[str]) -> list[dict]:
        """Send claim texts to the Foundry agent and return structured outputs."""
        logger.info(f"Classifying {len(claim_texts)} claims")
        results = []

        for idx, claim in enumerate(claim_texts, 1):
            logger.debug(f"Processing claim {idx}/{len(claim_texts)}: {claim[:100]}...")

            try:
                # Create a new thread for conversation
                thread = self.client.agents.threads.create()
                logger.debug(f"Created thread ID: {thread.id}")

                # Add the claim as a message to the thread
                self.client.agents.messages.create(
                    thread_id=thread.id, role="user", content=claim
                )

                # Process the claim using the agent with the specified model deployment
                run = self.client.agents.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=self.agent.id,
                )

                response_text = self._get_assistant_response(thread.id, run.id)
                logger.debug(
                    "Claim %s: Retrieved assistant response (%d characters)",
                    idx,
                    len(response_text),
                )
                logger.info("Claim %s: Assistant response:\n%s", idx, response_text)

                parsed = self._parse_json_response(response_text)
                results.append(parsed)

            except Exception as e:
                logger.error(f"Claim {idx}: Failed to classify: {e}")
                results.append({"classification": "ERROR", "reasoning": str(e)[:250]})

        logger.info(f"Completed classification of {len(results)} claims")
        return results

    def _get_assistant_response(self, thread_id: str, run_id: str) -> str:
        """Return the assistant text for the given run or raise if unavailable."""
        messages = self.client.agents.messages.list(
            thread_id=thread_id,
            order=ListSortOrder.ASCENDING,
        )

        for message in messages:
            if message.run_id != run_id or not message.text_messages:
                continue
            text_value = message.text_messages[-1].text.value
            if text_value and text_value.strip():
                return text_value

        raise ValueError("Assistant did not return any text for the run")

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON response from assistant or return fallback for valid text."""
        if not text or not text.strip():
            raise ValueError("Assistant response was empty")

        try:
            parsed = json.loads(text.strip())

            if not isinstance(parsed, dict):
                return {
                    "classification": "Unable to classify",
                    "reasoning": text.strip()[:500],
                }

            classification = parsed.get("classification")
            reasoning = parsed.get("reasoning") or parsed.get("reason")

            if not classification or not reasoning:
                return {
                    "classification": "Unable to classify",
                    "reasoning": text.strip()[:500],
                }

            return {"classification": classification, "reasoning": reasoning}

        except json.JSONDecodeError:
            # Valid text response but not JSON - treat as business logic response
            return {
                "classification": "Unable to classify",
                "reasoning": text.strip()[:500],
            }
