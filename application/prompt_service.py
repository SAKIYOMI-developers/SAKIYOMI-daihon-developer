from infrastructure.prompt_repository import PromptRepository
from domain.prompt import Prompt
from typing import Dict, Any, Optional


class PromptService:
    def __init__(self):
        self.prompt_repo = PromptRepository()

    def create_prompt(self, user_id: str, type: str, text: str, example_plot: Optional[str] = None) -> Dict[str, Any]:
        prompt_id = f"{user_id}_{type}"
        prompt = Prompt(
            prompt_id=prompt_id,
            user_id=user_id,
            type=type,
            text=text,
            example_plot=example_plot
        )
        prompt.embed_example_plot()
        return self.prompt_repo.create_prompt(prompt)

    def read_prompt(self, user_id: str, type: str) -> Dict[str, Any]:
        prompt = self.prompt_repo.read_prompt(user_id, type)
        if prompt.get("status") == "error" or "data" not in prompt:
            return prompt
        prompt["data"]["text"] = self.format_prompt(prompt["data"]["text"], prompt["data"]["example_plot"])
        return prompt

    def update_prompt(self, prompt_id: str, user_id: str, type: str, text: str, example_plot: Optional[str] = None) -> Dict[str, Any]:
        prompt = Prompt(
            prompt_id=prompt_id,
            user_id=user_id,
            type=type,
            text=text,
            example_plot=example_plot
        )
        prompt.embed_example_plot()
        return self.prompt_repo.update_prompt(prompt)

    def delete_prompt(self, user_id: str, type: str) -> Dict[str, Any]:
        return self.prompt_repo.delete_prompt(user_id, type)

    def list_prompts(self, user_id: str) -> Dict[str, Any]:
        return self.prompt_repo.list_prompts(user_id)["data"]

    def format_prompt(self, text: str, example_plot: str) -> str:
        if '{example_plot}' in text:
            text = text.replace("{example_plot}", example_plot or "")
        return text
