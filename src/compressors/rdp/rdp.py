from typing import List, Tuple
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics


class RDPCompressor:
    def __init__(self, epsilon: float):
        self.epsilon = epsilon

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None
        self.metrics = None

    def _dist(self, p, a, b):
        x, y = p
        x1, y1 = a
        x2, y2 = b

        if x1 == x2 and y1 == y2:
            return abs(y - y1)

        num = abs((y2 - y1)*x - (x2 - x1)*y + x2*y1 - y2*x1)
        den = ((y2 - y1)**2 + (x2 - x1)**2) ** 0.5
        return num / den

    def _rdp(self, pts):
        if len(pts) < 3:
            return pts

        a, b = pts[0], pts[-1]

        max_d = -1
        idx = -1

        for i in range(1, len(pts)-1):
            d = self._dist(pts[i], a, b)
            if d > max_d:
                max_d = d
                idx = i

        if max_d > self.epsilon:
            left = self._rdp(pts[:idx+1])
            right = self._rdp(pts[idx:])
            return left[:-1] + right

        return [a, b]

    def compress(self, serie: List[Tuple[float, float]]):

        def _compress():
            return self._rdp(serie)

        # 🔥 apenas a compressão é monitorada
        pontos, t, mem = medir_pico_memoria(_compress)

        self.execution_time = t
        self.memory_usage_mb = mem
        self.compression_ratio = 100 * (1 - len(pontos) / len(serie))

        # reconstrução fora do monitor
        reconstruido = []
        idx = 0

        for i in range(len(pontos) - 1):
            t0, v0 = pontos[i]
            t1, v1 = pontos[i + 1]

            while idx < len(serie) and serie[idx][0] <= t1:
                t_ = serie[idx][0]
                if t1 == t0:
                    v = v0
                else:
                    a = (t_ - t0) / (t1 - t0)
                    v = v0 + a * (v1 - v0)
                reconstruido.append((t_, v))
                idx += 1

        reconstruido = reconstruido[:len(serie)]

        original = [v for _, v in serie]
        reconstruido_vals = [v for _, v in reconstruido]
        self.metrics = Metrics(original, reconstruido_vals).compute_metrics()

        return reconstruido