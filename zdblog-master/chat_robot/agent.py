"""Build an isolated graph; durable conversation state is owned by Django."""
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

from .tools import get_weather, search_func, search_blog, analyze_sentiment, handle_tool_errors
from .article_tools import list_articles, count_articles, get_article, site_timezone
from .tool_config import default_tools, WEATHER_RULES, BLOG_RULES, ARTICLE_TOOLS
from django.utils import timezone
from .utils import get_llm_model


TOOL_REGISTRY = {'get_weather': get_weather, 'search_func': search_func,
                 'search_blog': search_blog, 'analyze_sentiment': analyze_sentiment,
                 'list_articles': list_articles, 'count_articles': count_articles, 'get_article': get_article}


def build_agent(system_prompt, tool_names=None):
    names = default_tools() if tool_names is None else tool_names
    unknown = set(names) - TOOL_REGISTRY.keys()
    if unknown:
        raise ValueError('Unknown tool configuration')
    if 'get_weather' in names:
        system_prompt += WEATHER_RULES
    if set(names).intersection(['search_blog', *ARTICLE_TOOLS]):
        system_prompt += BLOG_RULES
        system_prompt += f'\n本站当前日期：{timezone.localdate(timezone=site_timezone()).isoformat()}（{site_timezone()}）。'
    return create_agent(
        model=get_llm_model(),
        system_prompt=system_prompt,
        tools=[TOOL_REGISTRY[name] for name in dict.fromkeys(names)],
        middleware=[
            handle_tool_errors,
            SummarizationMiddleware(
                model=get_llm_model(), trigger=('tokens', 10000), keep=('messages', 20),
            ),
        ],
    )
