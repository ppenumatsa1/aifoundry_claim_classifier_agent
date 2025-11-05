import os
import json
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment variables from .env file
load_dotenv()


class FoundryClient:
    """Wrapper for Azure AI Foundry Agent operations."""

    def __init__(self):
        self.endpoint = os.environ["PROJECT_ENDPOINT"]
        self.model_deployment = os.environ["MODEL_DEPLOYMENT_NAME"]
        # Using DefaultAzureCredential for authentication
        self.client = AIProjectClient(
            endpoint=self.endpoint, credential=DefaultAzureCredential()
        )

        # Create or get the claims classifier agent
        self.agent = self._setup_classifier_agent()

    def _setup_classifier_agent(self):
        """Create or get the claims classifier agent with system instructions."""
        # Read the classification prompt
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "classification_prompt.txt"
        )
        with open(prompt_path, "r") as f:
            system_instructions = f.read()

        # Create the agent with system instructions
        agent = self.client.agents.create(
            display_name="Claims Fraud Classifier",
            description="AI agent for classifying insurance claims as Fraud, Likely Fraud, or Not Fraud",
            system_instructions=system_instructions,
        )
        return agent

    def classify_claims(self, claim_texts: list[str]) -> list[dict]:
        """Send claim texts to the Foundry agent and return JSON outputs."""
        results = []
        for claim in claim_texts:
            # Create a new thread for conversation
            thread = self.client.agents.create_thread()
            # Add the claim as a message to the thread
            self.client.agents.create_message(
                thread_id=thread.id, role="user", content=claim
            )
            # Process the claim using the agent with the specified model deployment
            run = self.client.agents.create_and_process_run(
                thread_id=thread.id,
                deployment_name=self.model_deployment,
                agent_id=self.agent.id,
            )  # Use the created agent for classification
            output = run.output_text or ""
            try:
                parsed = json.loads(output)
            except Exception:
                parsed = {"classification": None, "reasoning": output[:250]}
            results.append(parsed)
        return results
