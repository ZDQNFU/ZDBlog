from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

#加载env环境变量
load_dotenv()

# ── Monkey-patch langchain_openai 以支持 DeepSeek 的 reasoning_content ──
# DeepSeek 要求 reasoning_content 必须在多轮对话中回传，但 langchain_openai
# 不处理这个非 OpenAI 标准字段，需要手动补丁。

import langchain_openai.chat_models.base as _openai_base

_orig_convert_message_to_dict = _openai_base._convert_message_to_dict
_orig_convert_dict_to_message = _openai_base._convert_dict_to_message
_orig_convert_delta_to_message_chunk = _openai_base._convert_delta_to_message_chunk


def _patched_convert_message_to_dict(message, api="chat/completions"):
    """在转换消息为 API dict 时，回传 reasoning_content 给 DeepSeek。"""
    msg_dict = _orig_convert_message_to_dict(message, api)
    if isinstance(message, AIMessage):
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            msg_dict["reasoning_content"] = reasoning
    return msg_dict


def _patched_convert_dict_to_message(_dict):
    """从 API 响应中捕获 reasoning_content 到 AIMessage.additional_kwargs。"""
    message = _orig_convert_dict_to_message(_dict)
    if isinstance(message, AIMessage) and "reasoning_content" in _dict:
        message.additional_kwargs["reasoning_content"] = _dict["reasoning_content"]
    return message


def _patched_convert_delta_to_message_chunk(_dict, default_class):
    """从流式 delta 中捕获 reasoning_content 到 AIMessageChunk.additional_kwargs。"""
    message_chunk = _orig_convert_delta_to_message_chunk(_dict, default_class)
    if isinstance(message_chunk, AIMessageChunk) and "reasoning_content" in _dict:
        message_chunk.additional_kwargs["reasoning_content"] = _dict["reasoning_content"]
    return message_chunk


_openai_base._convert_message_to_dict = _patched_convert_message_to_dict
_openai_base._convert_dict_to_message = _patched_convert_dict_to_message
_openai_base._convert_delta_to_message_chunk = _patched_convert_delta_to_message_chunk

def get_llm_model():
    model_map = {
        'deepseek' : ChatOpenAI(
            model = os.getenv('DEEPSEEK_LLM_MODEL'),
            api_key = os.getenv('DEEPSEEK_API_KEY'),
            base_url = os.getenv('DEEPSEEK_BASE_URL'),
            temperature = os.getenv('TEMPERATURE'),
            max_tokens = int(os.getenv('MAX_TOKENS')),
        )
    }
    model_type = os.getenv('LLM_MODEL')
    return model_map.get(model_type)


def chat_with_agent(agent, user_input, thread_id="default-thread"):
    """简化的聊天接口"""
    # 统一处理输入格式
    if isinstance(user_input, str):
        messages = [HumanMessage(content=user_input)]
    else:
        messages = user_input

    config = {"configurable": {"thread_id": thread_id}}
    return agent.invoke({"messages": messages}, config=config)


def stream_chat_with_agent(agent, user_input, thread_id="default-thread"):
    """
    流式聊天

    只输出模型的最终文本回复，过滤掉：
    - ToolMessage（工具返回的原始数据）
    - 含有 tool_calls 的消息（模型请求调用工具时的中间消息）
    - SummarizationMiddleware 生成的总结文本
    """
    from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

    config = {"configurable": {"thread_id": thread_id}}

    # 总结文本都以这些字符串开头
    SUMMARY_PREFIXES = (
        "## SESSION INTENT",
        "## SUMMARY",
        "## ARTIFACTS",
        "## NEXT STEPS",
        "## USER MESSAGES",
    )

    current_msg_id = None
    # 检测状态：None=未决定, list=暂存chunk, True=确认为总结(丢弃), False=确认非总结(放行)
    detect_state = None
    detect_buf: list[str] = []

    def _prefix_match(accumulated: str) -> int:
        """返回 0=需要更多字符, 1=确认是总结, -1=确认不是总结"""
        t = accumulated.lstrip()
        if not t:
            return 0
        # 不以 # 或 ## 开头 → 绝对不是总结
        if not t.startswith("#"):
            return -1
        # 以 ## 开头但还没匹配完整前缀
        # 检查是否与任一前缀部分匹配
        partial = False
        for prefix in SUMMARY_PREFIXES:
            if t.startswith(prefix):
                return 1  # 完全匹配 → 是总结
            if prefix.startswith(t):
                partial = True
        if partial:
            return 0  # 部分匹配 → 需要更多字符
        # 以 ## 开头但不匹配任何前缀 → 不是总结
        return -1

    for chunk in agent.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="messages"
    ):
        if not (isinstance(chunk, tuple) and len(chunk) == 2):
            continue

        message, metadata = chunk

        if isinstance(message, ToolMessage):
            continue

        if hasattr(message, 'tool_calls') and message.tool_calls:
            continue
        if hasattr(message, 'additional_kwargs') and message.additional_kwargs.get('tool_calls'):
            continue

        if not isinstance(message, (AIMessage, AIMessageChunk)):
            continue

        content = getattr(message, 'content', None)
        if not content:
            continue

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = ''.join(
                item['text'] if isinstance(item, dict) and 'text' in item
                else item if isinstance(item, str)
                else ''
                for item in content
            )
        else:
            continue

        if not text:
            continue

        # 过滤纯空白 token（如 LLM 末尾的换行符），避免 C 端渲染空白行
        if not text.strip():
            continue

        msg_id = getattr(message, 'id', None)

        # 消息 ID 变化 → 重置检测状态
        if msg_id is not None and msg_id != current_msg_id:
            current_msg_id = msg_id
            detect_state = None
            detect_buf = []

        if detect_state is True:
            # 已确认为总结，静默丢弃
            continue

        if detect_state is False:
            # 已确认非总结，直接流式输出
            yield text
            continue

        # detect_state is None → 尚未判断，需要缓冲检测
        detect_buf.append(text)
        accumulated = ''.join(detect_buf)
        result = _prefix_match(accumulated)

        if result == -1:
            # 确认不是总结 → 立即输出所有缓冲
            for buf in detect_buf:
                yield buf
            detect_state = False
            detect_buf = []
        elif result == 1:
            # 确认是总结 → 丢弃
            detect_state = True
            detect_buf = []
        # result == 0 → 继续缓冲

def extract_ai_response(result):
    """从结果中提取 AI 的回复文本"""
    messages = result.get("messages", [])
    ai_messages = [msg.content for msg in messages if isinstance(msg, AIMessage)]
    return ai_messages[-1] if ai_messages else None