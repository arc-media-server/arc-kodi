"""Pre-roll policy and a hard list deadline, without Kodi dependencies."""
import queue
import threading

def enabled(item, resume_ms=0, together=False):
    return item.get("kind") == "movie" and resume_ms <= 0 and not together

def clips_before_deadline(fetch, seconds=3.0):
    """Late or failed network work cannot delay the film or mutate playback later."""
    answers = queue.Queue(maxsize=1)
    def load():
        try:
            answers.put(fetch())
        except Exception:
            answers.put(None)
    threading.Thread(target=load, name="arc-preroll-list", daemon=True).start()
    try:
        answer = answers.get(timeout=seconds)
    except queue.Empty:
        return [], "timeout"
    if not isinstance(answer, list):
        return [], "failed"
    return [c for c in answer if isinstance(c, dict) and isinstance(c.get("url"), str) and c["url"]], "ready"
