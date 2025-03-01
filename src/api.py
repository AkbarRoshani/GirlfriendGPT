"""Scaffolding to host your LangChain Chatbot on Steamship and connect it to Telegram."""
from typing import List, Optional, Type

import langchain
from langchain.agents import Tool, initialize_agent, AgentType, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from pydantic import Field
from steamship.experimental.package_starters.telegram_bot import (
    TelegramBot,
    TelegramBotConfig,
)
from steamship.invocable import Config
from steamship_langchain.llms import OpenAIChat
from steamship_langchain.memory import ChatMessageHistory

from agent.base import LangChainAgentBot
from agent.tools.search import SearchTool
from agent.tools.selfie import SelfieTool
from agent.tools.speech import GenerateSpeechTool
from personalities import get_personality, Personality
from prompts import SUFFIX, FORMAT_INSTRUCTIONS, PERSONALITY_PROMPT

MODEL_NAME = "gpt-4"  # or "gpt-4"
TEMPERATURE = 0.7
VERBOSE = False
MEMORY_WINDOW_SIZE = 10

langchain.cache = None


class GirlFriendAIConfig(TelegramBotConfig):
    bot_token: str = Field(
        description="Your telegram bot token.\nLearn how to create one here: "
        "https://github.com/EniasCailliau/GirlfriendGPT/blob/main/docs/register-telegram-bot.md"
    )
    elevenlabs_api_key: str = Field(
        default="", description="Optional API KEY for ElevenLabs Voice Bot"
    )
    elevenlabs_voice_id: str = Field(
        default="", description="Optional voice_id for ElevenLabs Voice Bot"
    )
    chat_ids: str = Field(
        default="", description="Comma separated list of whitelisted chat_id's"
    )
    personality: Personality = Field(
        description="The personality you want to deploy. Pick one of the personalities listed here: "
        "https://github.com/EniasCailliau/GirlfriendGPT/tree/main/src/personalities"
    )
    use_gpt4: bool = Field(
        True,
        description="If True, use GPT-4. Use GPT-3.5 if False. "
        "GPT-4 generates better responses at higher cost and latency.",
    )


class GirlfriendGPT(LangChainAgentBot, TelegramBot):
    """Deploy LangChain chatbots and connect them to Telegram."""

    config: GirlFriendAIConfig

    @classmethod
    def config_cls(cls) -> Type[Config]:
        """Return the Configuration class."""
        return GirlFriendAIConfig

    def get_agent(self, chat_id: str) -> AgentExecutor:
        llm = OpenAIChat(
            client=self.client,
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
            verbose=VERBOSE,
        )

        tools = self.get_tools(chat_id=chat_id)

        memory = self.get_memory(chat_id)

        return initialize_agent(
            tools,
            llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            agent_kwargs={
                # "output_parser": MultiModalOutputParser(ConvoOutputParser()),
                "prefix": PERSONALITY_PROMPT.format(
                    personality=get_personality(
                        self.config.personality or Personality.SACHA.value
                    )
                ),
                "suffix": SUFFIX,
                "format_instructions": FORMAT_INSTRUCTIONS,
            },
            verbose=VERBOSE,
            memory=memory,
        )

    def voice_tool(self) -> Optional[Tool]:
        """Return tool to generate spoken version of output text."""
        return GenerateSpeechTool(
            client=self.client,
            voice_id=self.config.elevenlabs_voice_id,
            elevenlabs_api_key=self.config.elevenlabs_api_key,
        )

    def get_memory(self, chat_id):
        if self.context and self.context.invocable_instance_handle:
            my_instance_handle = self.context.invocable_instance_handle
        else:
            my_instance_handle = "local-instance-handle"

        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            chat_memory=ChatMessageHistory(
                client=self.client, key=f"history-{chat_id}-{my_instance_handle}"
            ),
            return_messages=True,
            k=MEMORY_WINDOW_SIZE,
        )
        return memory

    def get_tools(self, chat_id: str) -> List[Tool]:
        return [
            SearchTool(self.client),
            # MyTool(self.client),
            # GenerateImageTool(self.client),
            # GenerateAlbumArtTool(self.client)
            # RemindMe(invoke_later=self.invoke_later, chat_id=chat_id),
            # VideoMessageTool(self.client),
            SelfieTool(self.client),
        ]
