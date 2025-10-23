from dataclasses import dataclass

import yaml

CONFIG_FILENAME = "config.yml"


@dataclass
class GlobalConfig:
    redis: str
    cookie: str
    mongo: str
    postgres: str


_config: GlobalConfig | None = None


def load_config() -> GlobalConfig:
    global _config
    if not _config:
        with open(CONFIG_FILENAME, "r") as f:
            _config = GlobalConfig(**yaml.safe_load(f))
        
    return _config
