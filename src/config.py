"""
配置加载模块
负责加载、校验和提供全局配置，支持热更新。
"""
import os
import threading
import yaml
import copy


class ConfigManager:
    """配置管理器：单例模式，线程安全"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_path=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path=None):
        if self._initialized:
            return
        self._initialized = True
        self._config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.yaml"
        )
        self._config = {}
        self._raw_config = {}
        self.load()

    def load(self):
        """从 YAML 文件加载配置"""
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")
        with open(self._config_path, "r", encoding="utf-8") as f:
            self._raw_config = yaml.safe_load(f) or {}
        self._config = copy.deepcopy(self._raw_config)
        return self._config

    def reload(self):
        """热重载配置（运行中修改 config.yaml 后调用）"""
        with self._lock:
            self.load()
        return self._config

    def get(self, key_path, default=None):
        """
        按点分路径获取配置，如 get('camera.width')
        """
        keys = key_path.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key_path, value):
        """
        按点分路径设置配置（仅内存中，不写文件）
        """
        keys = key_path.split(".")
        cfg = self._config
        for k in keys[:-1]:
            if k not in cfg or not isinstance(cfg[k], dict):
                cfg[k] = {}
            cfg = cfg[k]
        cfg[keys[-1]] = value

    def save(self):
        """将当前内存配置写回 YAML 文件"""
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    @property
    def all(self):
        return self._config

    @property
    def config_path(self):
        return self._config_path


def get_config(config_path=None):
    """获取全局配置单例"""
    return ConfigManager(config_path)
