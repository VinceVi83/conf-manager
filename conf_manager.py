import sys
import logging
import yaml
import shutil
from pathlib import Path
project_root = Path(__file__).parent.parent
if (project_root / 'config_example.yaml').exists():
    from .utils import Utils
else:
    from utils import Utils
from types import SimpleNamespace

logger = logging.getLogger(__name__)

class CfgConfig(SimpleNamespace):
    """
    Configuration container built on SimpleNamespace with dict-like access support.

    Provides dual access patterns for configuration values:
    - Attribute-style: cfg.section.key
    - Dict-style: cfg.section['key']

    All configuration data is recursively converted to SimpleNamespace,
    enabling nested access like cfg.dico2.dico_dico.key1.
    Lists are preserved as-is.

    Usage:
        cfg = CfgConfig()
        cfg.load_from_file('config.yml')

        # Attribute access
        token = cfg.discord.token

        # Dict access  
        token = cfg.discord['token']

        # Iteration
        for key, value in vars(cfg.section).items():
            print(f'{key}: {value}')

    Features:
        - Recursive SimpleNamespace conversion for all nested dicts
        - Lists preserved as native Python lists (not converted)
        - Dict elements inside lists are recursively converted to SimpleNamespace
        - Dual attribute/dict access patterns
        - Compatible with hasattr(), getattr(), vars()

    Note:
        While flexible, consider standardizing on one access pattern 
        (preferably attribute-style) for consistency in your codebase.
        Lists are intentionally kept as lists for natural iteration and indexing.
        WARNING: Read-only. Do not modify attributes after loading.
        Do not use as a setter or treat as global mutable state.
    """

    def __repr__(self):
        return self._format_object(self)

    def _format_object(self, obj, indent_level=0):
        spacing = '  ' * indent_level
        if isinstance(obj, (SimpleNamespace, CfgConfig)):
            items = vars(obj).items()
            if not items:
                return '{}'
            lines = ['{']
            for k, v in items:
                formatted_value = self._format_object(v, indent_level + 1)
                lines.append(spacing + '  ' + '"' + k + '": ' + formatted_value + ',')
            lines[-1] = lines[-1].rstrip(',')
            lines.append(spacing + '}')
            return '\n'.join(lines)
        if isinstance(obj, list):
            if not obj:
                return '[]'
            items = []
            for item in obj:
                items.append(self._format_object(item, indent_level + 1))
            return '[\n' + spacing + '  ' + (',\n' + spacing + '  ').join(items) + '\n' + spacing + ']'
        if isinstance(obj, str):
            return '"' + obj + '"'
        if obj is None:
            return 'null'
        if isinstance(obj, bool):
            return 'true' if obj else 'false'
        return str(obj)

    def to_dict(self):
        result = {}
        for k, v in vars(self).items():
            if isinstance(v, (CfgConfig, SimpleNamespace)):
                result[k] = self._to_dict_recursive(v)
            elif isinstance(v, list):
                result[k] = self._list_to_dict(v)
            else:
                result[k] = v
        return result

    def _to_dict_recursive(self, obj):
        if isinstance(obj, (CfgConfig, SimpleNamespace)):
            return {k: self._to_dict_recursive(v) for k, v in vars(obj).items()}
        elif isinstance(obj, list):
            return self._list_to_dict(obj)
        return obj

    def _list_to_dict(self, lst):
        result = []
        for item in lst:
            if isinstance(item, (CfgConfig, SimpleNamespace)):
                result.append({k: self._to_dict_recursive(v) for k, v in vars(item).items()})
            elif isinstance(item, list):
                result.append(self._list_to_dict(item))
            else:
                result.append(item)
        return result

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f'"{key}" not found in configuration')

    def __contains__(self, key):
        return hasattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


class ConfManager:
    """
    Configuration loader with automatic detection of local or user directory.

    Handles config file discovery, initialization, and loading with fallback:
        1. Look for config_example.yaml in project root → template reference
        2. Runtime config lives at ~/Documents/<project>/config.yaml
        3. If config.yaml is missing, auto-copy from config_example.yaml
        4. If config_example.yaml is also missing, create it with defaults in both:  
            - project root (template)
            - ~/Documents/<project>/ (runtime)
    Attributes:
        dir_name (str): Project name from parent directory
        CONFIG_FILE (Path): Target config file path

    Usage:
        from config import cfg # in your modules to access configuration values.
        # WARNING: self.cfg should be used as read-only, do not modify attributes after loading
    """

    def __init__(self, standalone=False):
        if standalone:
            self.cfg = self.dict_to_namespace(get_example_config())
            return

        self.project_root = Path(__file__).resolve().parent.parent
        self.dir_name = self.project_root.name
        self.BASE_DIR = Path.home() / 'Documents' / self.dir_name
        self.AGENTS_DIR = self.BASE_DIR / 'agents'
        self.CONFIG_FILE = self.BASE_DIR / 'config.yaml'
        self.template_config = self.project_root / 'config_example.yaml'
        self.template_agents = self.project_root / 'agents'

        self._setup_files()
        yaml_data = self._load_yaml()
        self.cfg = self.dict_to_namespace(yaml_data)
        self.cfg.agents = self._load_agents()
        self.cfg.project_dir = self.project_root
        self.cfg.config_dir = self.BASE_DIR
        self.cfg.lanip = Utils.get_local_ip()

    def _setup_files(self):
        if not self.BASE_DIR.exists():
            self.BASE_DIR.mkdir(parents=True, exist_ok=True)
            if self.template_config.exists():
                shutil.copy(self.template_config, self.CONFIG_FILE)
                logger.info(f'Config copied from template to {self.CONFIG_FILE}')
            else:
                self._create_default_config()
                logger.info(f'Default config created in {self.CONFIG_FILE}')
            if self.template_agents.exists():
                shutil.copytree(self.template_agents, self.AGENTS_DIR)
                logger.info(f'Agents copied from template to {self.AGENTS_DIR}')
            else:
                self.AGENTS_DIR.mkdir(parents=True, exist_ok=True)

        if not self.CONFIG_FILE.exists():
            if self.template_config.exists():
                shutil.copy(self.template_config, self.CONFIG_FILE)
                logger.info(f'Config copied from template to {self.CONFIG_FILE}')
            else:
                self._create_default_config()
                logger.info(f'Default config created in {self.CONFIG_FILE}')

    def _create_default_config(self):
        default_config_dict = {
            'key1': 'value',
            'dico': {'key1': None, 'key2': None},
            'dico2': {
                'key1': True,
                'key2': False,
                'dico_dico': {'key1': True, 'key2': None}
            },
            'key2': False,
            'my_list': ['item1', 'item2', 'item3'],
            'servers': [
                {'host': '192.168.1.1', 'port': 8080},
                {'host': '192.168.1.2', 'port': 9090}
            ],
            'mixed_config': {
                'names': ['alice', 'bob', 'charlie'],
                'active': True,
                'details': {'logs': ['error.log', 'access.log'], 'retention': 30}
            }
        }
        if not self.template_config.exists():
            with open(self.template_config, 'w', encoding='utf-8') as f:
                yaml.dump(default_config_dict, f, default_flow_style=False, allow_unicode=True)
            logger.info(f'Template config created: {self.template_config}')
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(default_config_dict, f, default_flow_style=False, allow_unicode=True)

    def _load_yaml(self):
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _load_agents(self):
        agents = CfgConfig()
        self._load_markdown_agents(self.AGENTS_DIR, agents)
        return agents

    def _load_markdown_agents(self, agents_dir, agents):
        for md_file in agents_dir.glob('*.md'):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                setattr(agents, md_file.stem, content)

    @staticmethod
    def dict_to_namespace(data):
        if isinstance(data, dict):
            return CfgConfig(**{k: ConfManager.dict_to_namespace(v) for k, v in data.items()})
        elif isinstance(data, list):
            return [ConfManager.dict_to_namespace(item) if isinstance(item, dict) else item for item in data]
        return data


_config_manager = ConfManager()
cfg = _config_manager.cfg

class LocalFilesFilter(logging.Filter):
    
    def __init__(self):
        super().__init__()
        self.local_files = set()
        root_dir = Path(__file__).resolve().parent.parent
        for path in root_dir.rglob('*.py'):
            if '__pycache__' in path.parts:
                continue
            if any(part.startswith('.') for part in path.parts):
                continue
            self.local_files.add(path.name)

    def filter(self, record):
        return record.filename in self.local_files


def setup_logging():
    log_dir = cfg.config_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    date_format = '%y%m%d:%H:%M:%S'
    if getattr(cfg, 'verbose', False):
        log_format = '[%(asctime)s][%(filename)s][%(funcName)s](%(levelname)s): %(message)s'
    else:
        log_format = '[%(asctime)s][%(funcName)s](%(levelname)s): %(message)s'
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    local_filter = LocalFilesFilter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(local_filter)

    file_handler = logging.FileHandler(log_dir / 'debug.log', mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.addFilter(local_filter)

    root_logger = logging.getLogger()
    if getattr(cfg, 'debug', False):
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    logging.getLogger('uvicorn').setLevel(logging.WARNING)


def get_example_config():
    return {
        'key1': 'value',
        'dico': {'key1': 'value1', 'key2': 'value2'},
        'dico2': {
            'key1': True,
            'key2': False,
            'dico_dico': {'key1': 'value1', 'key2': 'value2'}
        },
        'key2': False,
        'my_list': ['item1', 'item2', 'item3'],
        'servers': [
            {'host1': '192.168.1.1', 'port': 8080},
            {'host2': '192.168.1.2', 'port': 9090}
        ],
        'mixed_config': {
            'names': ['alice', 'bob', 'charlie'],
            'active': True,
            'details': {'logs': ['error.log', 'access.log'], 'retention': 30}
        }
    }
