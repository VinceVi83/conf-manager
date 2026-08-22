# Shared Configuration Manager

## Overview

This project provides unified/shared configuration management across multiple projects. It loads YAML configuration into a namespace that supports nested attribute access and dictionary-style access, while keeping project-specific runtime files outside the source tree.

The runtime configuration is stored at `~/Documents/<project_name>/config.yaml`. If that file does not exist, the manager uses `config_example.yaml` from the project root as a template and copies it to the runtime location. If no template exists, it creates a default configuration and writes both the template and runtime files.

## Features

- YAML loading with `yaml.safe_load`.
- Recursive conversion of mappings to `CfgConfig` objects.
- Attribute access, such as `cfg.database.host`.
- Dictionary-style access for configuration objects, such as `cfg.database["host"]`.
- `get()` and `__contains__()` support on configuration objects.
- Conversion back to ordinary dictionaries with `CfgConfig.to_dict()`.
- Lists remain lists; dictionaries inside lists are converted recursively.
- Automatic creation or copying of the runtime configuration.
- Optional project-root `agents/*.md` files loaded as `cfg.agents.<filename_stem>` strings.
- Runtime values added to the loaded configuration: `cfg.config_dir` and `cfg.lanip`.
- Optional console and file logging setup through `setup_logging()`.

## Configuration locations

For a project whose root directory name is `<project_name>`:

- Template: `<project_root>/config_example.yaml`
- Runtime directory: `~/Documents/<project_name>/`
- Runtime configuration: `~/Documents/<project_name>/config.yaml`
- Runtime agents: `~/Documents/<project_name>/agents/`
- Debug log: `~/Documents/<project_name>/debug.log`

On initialization, the manager creates the runtime directory when needed. A project-root `agents/` directory is copied to the runtime directory when the runtime directory is first created. Missing runtime configuration is copied from the template or generated with built-in defaults.

## Usage

Place `conf_manager.py` and `utils.py` in the project package or importable module path. A normal import initializes the module-level manager and exposes the loaded configuration as `cfg`:

```python
from conf_manager import cfg

host = cfg.servers[0].host
project_config_dir = cfg.config_dir
local_ip = cfg.lanip
```

The configuration object is intended to be read-only after loading. For safe traversal of nested attributes, use `Utils.deep_getattr()`:

```python
from conf_manager import cfg
from utils import Utils

value = Utils.deep_getattr(cfg, "database.host", default="localhost")
```

`deep_getattr()` traverses attributes separated by periods. It does not provide list-index parsing; use normal Python indexing for list values.

## Classes and functions

### `CfgConfig`

A `types.SimpleNamespace` subclass for recursively loaded configuration mappings. It provides:

- `cfg.key` and `cfg["key"]` access.
- `cfg.get("key", default)` lookup.
- `"key" in cfg` membership checks.
- `to_dict()` conversion to nested dictionaries and lists.
- A structured `repr()` for inspection.

### `ConfManager`

Discovers the project and runtime paths, creates or copies configuration files, loads YAML, loads Markdown agents, and exposes the resulting `CfgConfig` through `manager.cfg`. Its `standalone=True` mode uses `get_example_config()` without filesystem setup.

### `Utils`

Provides two static helpers:

- `deep_getattr(obj, path, default=None)`: safely resolves a dotted attribute path.
- `get_local_ip()`: determines the local IPv4 address, falling back to `127.0.0.1` if detection fails.

## Logging

The module defines a module logger with `logging.getLogger(__name__)`. Logging setup is explicit; call `setup_logging()` after configuration has loaded if the application wants the provided console and file handlers. The file handler appends to `debug.log` in the runtime configuration directory.

## File structure

```text
<project_root>/
├── conf_manager.py
├── utils.py
├── config_example.yaml        # optional YAML template
└── agents/                    # optional Markdown agent templates
    └── <agent_name>.md

~/Documents/<project_name>/
├── config.yaml                # runtime YAML configuration
├── debug.log                  # created by setup_logging()
└── agents/                    # copied runtime Markdown agents
    └── <agent_name>.md
```

`test_conf_manager.py` exercises namespace access, fallback lookups, iteration, and the utility helpers and using the standalone configuration path when no project template is present.

## Dependencies

- Python 3.8 or newer (the code uses `pathlib`, `types.SimpleNamespace`, and standard-library logging, filesystem, and socket modules).
- [PyYAML](https://pyyaml.org/) 6.0.3.

Install the external dependency with:

```bash
python -m pip install -r requirements.txt
```
