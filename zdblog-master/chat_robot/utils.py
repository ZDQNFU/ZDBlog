"""DeepSeek model adapter and streaming projection for the conversation agent."""
import os
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from langchain_openai import ChatOpenAI
import langchain_openai.chat_models.base as _openai_base

# Production environment is loaded by config.settings; test settings stay isolated.

# DeepSeek requires reasoning_content to be returned on tool continuations.
# Install once, including when Django's autoreloader reloads this module.
if not getattr(_openai_base, '_zdblog_reasoning_patch', False):
    _original_to_dict = _openai_base._convert_message_to_dict
    _original_from_dict = _openai_base._convert_dict_to_message
    _original_delta = _openai_base._convert_delta_to_message_chunk

    def _to_dict(message, *args, **kwargs):
        result = _original_to_dict(message, *args, **kwargs)
        if isinstance(message, AIMessage) and 'reasoning_content' in message.additional_kwargs:
            result['reasoning_content'] = message.additional_kwargs['reasoning_content']
        return result

    def _from_dict(data, *args, **kwargs):
        message = _original_from_dict(data, *args, **kwargs)
        if isinstance(message, AIMessage) and 'reasoning_content' in data:
            message.additional_kwargs['reasoning_content'] = data['reasoning_content']
        return message

    def _from_delta(data, *args, **kwargs):
        message = _original_delta(data, *args, **kwargs)
        if isinstance(message, AIMessageChunk) and 'reasoning_content' in data:
            message.additional_kwargs['reasoning_content'] = data['reasoning_content']
        return message

    _openai_base._convert_message_to_dict = _to_dict
    _openai_base._convert_dict_to_message = _from_dict
    _openai_base._convert_delta_to_message_chunk = _from_delta
    _openai_base._zdblog_reasoning_patch = True


def get_llm_model():
    if os.getenv('LLM_MODEL', 'deepseek') != 'deepseek':
        raise ValueError('LLM_MODEL must be deepseek')
    if not os.getenv('DEEPSEEK_API_KEY'):
        raise ValueError('DEEPSEEK_API_KEY is required')
    return ChatOpenAI(
        model=os.getenv('DEEPSEEK_LLM_MODEL', 'deepseek-chat'),
        api_key=os.environ['DEEPSEEK_API_KEY'],
        base_url=os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        temperature=float(os.getenv('TEMPERATURE', '0.7')),
        max_tokens=int(os.getenv('MAX_TOKENS', '4096')),
        timeout=120, max_retries=2,
    )


def stream_chat_with_agent(agent, user_input, thread_id='default-thread', *, history=None, on_state=None):
    """Emit only model-node text; retain the complete state including tool/reasoning messages."""
    inputs = {'messages': [*(history or []), HumanMessage(content=user_input)]}
    config = {'configurable': {'thread_id': thread_id}, 'recursion_limit': 30}
    for mode, payload in agent.stream(inputs, config=config, stream_mode=['messages', 'values']):
        if mode == 'values':
            if on_state:
                on_state(payload.get('messages', []))
            continue
        message, metadata = payload
        # Summarization and tool nodes are never sent to the client.
        if metadata.get('langgraph_node') != 'model' or metadata.get('lc_source') == 'summarization':
            continue
        if not isinstance(message, (AIMessage, AIMessageChunk)):
            continue
        if message.tool_calls or message.additional_kwargs.get('tool_calls'):
            continue
        content = message.content
        if isinstance(content, list):
            content = ''.join(item if isinstance(item, str) else item.get('text', '')
                              for item in content if isinstance(item, (str, dict)))
        if isinstance(content, str) and content:
            # Whitespace is meaningful in Markdown and must survive token boundaries.
            yield content


def chat_with_agent(agent, user_input, thread_id='default-thread'):
    messages = [HumanMessage(content=user_input)] if isinstance(user_input, str) else user_input
    return agent.invoke({'messages': messages}, config={'configurable': {'thread_id': thread_id}})


def extract_ai_response(result):
    messages = [m.content for m in result.get('messages', []) if isinstance(m, AIMessage)]
    return messages[-1] if messages else None
