import socket
try:
    from common.conf_manager import cfg, setup_logging # type: ignore
except ImportError:
    from conf_manager import cfg, setup_logging # type: ignore

import threading
import requests
import logging

logger = logging.getLogger(__name__)

class Utils:
    """
    Collection of static utility methods for configuration traversal and network info.

    Provides helper functions commonly used across projects:
    - Deep attribute access for nested configuration objects
    - Local IP address detection

    All methods are static and can be called without instantiation.

    Usage:
        value = Utils.deep_getattr(cfg, 'section.sub.key', 'default')
        ip = Utils.get_local_ip()
    """
    @staticmethod
    def deep_getattr(obj, path, default=None):
        if not path:
            return obj
        parts = path.split('.')
        current = obj
        for part in parts:
            if current is None:
                return default
            try:
                current = getattr(current, part)
            except AttributeError:
                return default
        return current

    @staticmethod
    def format_result(result):
        if isinstance(result, dict):
            try:
                formatted_items = []
                for k, v in result.items():
                    formatted_items.append(f"{k}:{v}")
                return ",".join(formatted_items)
            except Exception:
                return str(result)
        return str(result)

    @staticmethod
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    @staticmethod
    def send_discord_notification(message, channel=None, files=None):
        if getattr(cfg, 'discord', None) is None:
            logger.info("Discord not configured")
            return
        def post_request():
            try:
                if channel is not None:
                    channel_name = channel
                else:
                    channel_name = cfg.discord.channel
                payload = {
                    "channel_name": channel_name,
                    "msg": message,
                    "attachments": files if files else []
                }
                requests.post(f"http://{cfg.discord.host}:{cfg.discord.port}/send",
                              json=payload,
                              timeout=5)
            except Exception as e:
                pass
        threading.Thread(target=post_request, daemon=False).start()
