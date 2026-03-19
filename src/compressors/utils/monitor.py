import psutil
import threading
import time
import os


def medir_pico_memoria(func, *args, **kwargs):
    process = psutil.Process(os.getpid())

    mem_base = process.memory_info().rss
    peak = mem_base
    running = True

    def monitor():
        nonlocal peak
        while running:
            mem = process.memory_info().rss
            peak = max(peak, mem)
            time.sleep(0.001)

    t = threading.Thread(target=monitor)
    t.start()

    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()

    running = False
    t.join()

    # 🔥 diferença real
    peak_delta = peak - mem_base
    peak_mb = peak_delta / (1024 * 1024)

    return result, (end - start), peak_mb