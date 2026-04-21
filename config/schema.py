"""Configuration schema using Pydantic."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings


class Base(BaseModel):
    """Base model that accepts both camelCase and snake_case keys."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class OpenAIConfig(Base):
    """OpenAI API configuration."""

    base_url: str = ""
    model: str = ""
    temperature: float = 0.5
    recursion_limit: int = 50
    max_tokens: int = 4000

class AppConfig(Base):
    """Application configuration."""

    post_url: str = ""
    user: str = ""
    rc4key: str = ""
    dtlab_key: str = ""
    maxResultSize: int = 20
    time_out:int=60
    max_connections:int=10
    max_keepalive_connections: int = 5


class RedisConfig(Base):
    """Redis configuration."""

    host: str = ""
    port: int = 6379
    password: str = ""
    db: int = 0

class OauthConfig(Base):
    """OAuth configuration."""

    client_id: str = ""
    client_secret: str = ""
    auth_url: str = ""
    redirect_url: str = ""
    access_token_url: str = ""
    profile_url: str = ""

class LLMKeyConfig(Base):
    """LLM configuration."""

    llm_key_url: str = ""

class VerticaDatabaseConfig(Base):
    """Vertica Database configuration."""
    
    database: str = "FGEDW"
    host: str = "192.168.40.111"
    port: str = "5433"
    tlsmode: str = "disable"
    credentials_file: str = ""


class PostgresDatabaseConfig(Base):
    """PostgreSQL Database configuration."""
    
    database: str = "idatamemorydb"
    host: str = "192.168.41.173"
    port: str = "5432"
    user: str = "fuguo"
    password: str = "fuguo"
    tlsmode: str = "disable"


class KafkaConfig(Base):
    """Kafka configuration."""
    
    bootstrap_servers: list[str] = [
        '192.168.40.228:9092',
        '192.168.40.229:9092',
        '192.168.40.230:9092'
    ]
    topic: str = 'tst_datas001'
    zookeeper_servers: list[str] = [
        '192.168.40.228:2181',
        '192.168.40.229:2181',
        '192.168.40.230:2181'
    ]


class WebConfig(Base):
    host: str = "0.0.0.0"
    port: int = 8023

class OfflineLoginDB(Base):
    db_username: str = "root"
    db_password: str = "fullgoal"
    db_ip: str = "192.168.40.123"
    db_port: int = 3306


class Config(BaseSettings):
    """Root configuration for SQLAgent."""

    openai: OpenAIConfig = OpenAIConfig()
    app: AppConfig = AppConfig()
    redis: RedisConfig = RedisConfig()
    oauth: OauthConfig = OauthConfig()
    llm_key: LLMKeyConfig = LLMKeyConfig()
    verticadb: VerticaDatabaseConfig = VerticaDatabaseConfig()
    postgresqldb: PostgresDatabaseConfig = PostgresDatabaseConfig()
    kafka: KafkaConfig = KafkaConfig()
    web: WebConfig = WebConfig()
    offline_login: OfflineLoginDB = OfflineLoginDB()

    model_config = ConfigDict(env_prefix="SQLAGENT_", env_nested_delimiter="__")