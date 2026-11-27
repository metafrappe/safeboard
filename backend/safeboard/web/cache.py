"""In-memory stale-while-revalidate cache, as in the MVP."""
import threading
import time

_cache = {}
_lock = threading.Lock()
_refreshing = set()


def cached(key, ttl, fn):
    """Stale-while-revalidate: answer from memory at once, refresh in the background."""
    with _lock:
        hit = _cache.get(key)
        fresh = hit and time.time() - hit[0] < ttl
        start_bg = hit and not fresh and key not in _refreshing
        if start_bg:
            _refreshing.add(key)
    if fresh:
        return hit[1]
    if hit:
        if start_bg:
            def bg():
                try:
                    val = fn()
                    with _lock:
                        _cache[key] = (time.time(), val)
                except Exception:
                    pass
                finally:
                    with _lock:
                        _refreshing.discard(key)
            threading.Thread(target=bg, daemon=True).start()
        return hit[1]
    val = fn()
    with _lock:
        _cache[key] = (time.time(), val)
    return val


def drop(prefix):
    with _lock:
        for k in [k for k in _cache if k.startswith(prefix)]:
            del _cache[k]
