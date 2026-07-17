import os

from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import AIMessage, ToolMessage

from chat_robot.tools import get_weather, search_func
from chat_robot.utils import get_llm_model, stream_chat_with_agent
from chat_robot.prompts import SYSTEM_PROMPT
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver


# 使用 InMemorySaver，避免 SQLite 在多 worker Gunicorn 下的并发锁问题。
# 对话持久化由 MySQL ChatMessage 负责，checkpointer 仅维护 Agent 内部状态。
checkpointer = InMemorySaver()

agent = create_agent(
    model=get_llm_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=[get_weather, search_func],
    middleware=[
        SummarizationMiddleware(
            model=get_llm_model(),
            trigger=("tokens", 10000),
            keep=("messages", 50),
        )
    ],
    checkpointer=checkpointer,
)
