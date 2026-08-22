import socket

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
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

