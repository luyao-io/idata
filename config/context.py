from contextvars import ContextVar

request_user: ContextVar[str] = ContextVar("request_user")
request_llm_key: ContextVar[str] = ContextVar("request_llm_key")