from __future__ import annotations

from typing import Protocol


class RegisteredAgent(Protocol):
    name: str
    description: str
    capabilities: list[str]


class AgentRegistry:
    """Runtime registry for discoverable specialist agents."""

    def __init__(self) -> None:
        self._agents: dict[str, RegisteredAgent] = {}

    def register(self, agent: RegisteredAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> RegisteredAgent | None:
        return self._agents.get(name)

    def all_agents(self) -> list[RegisteredAgent]:
        return list(self._agents.values())

    def summaries(self) -> list[dict[str, object]]:
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "capabilities": list(agent.capabilities),
            }
            for agent in self.all_agents()
        ]
