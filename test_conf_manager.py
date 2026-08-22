from types import SimpleNamespace  
from pathlib import Path

project_root = Path(__file__).parent.parent
if (project_root / 'config_example.yaml').exists():
    from .conf_manager import cfg
    from .utils import Utils
else:
    from conf_manager import ConfManager
    from utils import Utils
    cfg = ConfManager(standalone=True).cfg

def test_conf_manager():
    token = cfg.key1
    flag = cfg.key2

    dico_key1 = cfg.dico.key1
    dico_key2 = cfg.dico.key2
    print(f'cfg.dico["key1"]: {cfg.dico["key1"]}')

    dico_dico_key1 = cfg.dico2.dico_dico.key1
    dico_dico_key2 = cfg.dico2.dico_dico.key2
    print(f'cfg.dico2.dico_dico["key1"]: {cfg.dico2.dico_dico["key1"]}')

    token = getattr(cfg, "key1", 'default_value')
    dico_key = getattr(cfg.dico, "key1", 'default')

    if hasattr(cfg, "key1"):
        print('key1 exist')

    if cfg.dico2.key1:
        print('dico2.key1 exist')

    if cfg.dico.key1 is None:
        print('dico.key1 est None')

    for key, value in vars(cfg.dico).items():
        print(f'{key}: {value}')

    for key, value in vars(cfg.dico2.dico_dico).items():
        print(f'{key}: {value}')

    dico_key = Utils.deep_getattr(cfg, 'dico.dico_dico.key1', 'default')
    dico_dico_key = Utils.deep_getattr(cfg, 'dico2.dico_dico.key3', 'fallback')
    server_port = Utils.deep_getattr(cfg, 'servers.0.port', None)

    print(f'deep dico.dico_dico.key1  => {dico_key}')
    print(f'deep dico2.dico_dico.key3 => {dico_dico_key}')
    print(f'deep servers[0].port       => {server_port}')

    iterate_config(cfg)

def iterate_config(obj, parent_key=''):
    for key, value in vars(obj).items():
        full_key = f'{parent_key}.{key}' if parent_key else key
        if isinstance(value, SimpleNamespace):
            iterate_config(value, full_key)
        else:
            print(f'{full_key}: {value}')


if __name__ == '__main__':
    print('Running test_conf_manager...')
    test_conf_manager()
