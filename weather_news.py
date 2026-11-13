import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.ollama import OllamaChatCompletionClient
from ddgs import DDGS


def get_weather_news(city: str) -> str:
    """Search the web for TODAY'S weather news and current conditions in a city
    (temperature, rain, storms, alerts, forecast). Use this for any question about
    the weather or weather headlines right now; not for general trivia or history."""
    hits = DDGS().news(f"{city} weather forecast", max_results=3)
    return "\n".join(f"- [{h['date'][:10]}] {h['title']}: {h['body']}" for h in hits)


def make_agent():
    return AssistantAgent(
        "weather_news",
        # Local free model; swap for OpenAIChatCompletionClient(model="gpt-4o-mini") if you have a key.
        model_client=OllamaChatCompletionClient(model="qwen2.5:1.5b"),
        tools=[get_weather_news],
        # On: the model reads the tool result and writes the 3-line reply.
        # Off: the agent would print the raw tool output (the news list) instead.
        reflect_on_tool_use=True,
        system_message="Call get_weather_news for the city the user gives. Reply in exactly 3 short lines separated by newlines: 1) conditions, 2) temperature, 3) a tip.",
    )


async def main():
    city = input("City: ")
    await Console(make_agent().run_stream(task=city))


if __name__ == "__main__":
    asyncio.run(main())
