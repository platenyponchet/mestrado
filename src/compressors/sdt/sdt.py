from typing import List, Tuple
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics


class SDTCompressor:
    def __init__(self, error: float):
        self.error = error

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None
        self.metrics = None

    class _SDT:
        def __init__(self, error, first_point):
            self.error = error
            self.corridor_point = first_point
            self.last_inbound_point = first_point

            self.upper_door_pivot = (first_point[0], first_point[1] + error)
            self.lower_door_pivot = (first_point[0], first_point[1] - error)

            self.max_upper_slope = float('-inf')
            self.min_lower_slope = float('inf')

        def process(self, p):
            dx_u = p[0] - self.upper_door_pivot[0]
            dx_l = p[0] - self.lower_door_pivot[0]

            if dx_u == 0 or dx_l == 0:
                return True, None

            upper = (p[1] - self.upper_door_pivot[1]) / dx_u
            lower = (p[1] - self.lower_door_pivot[1]) / dx_l

            self.max_upper_slope = max(self.max_upper_slope, upper)
            self.min_lower_slope = min(self.min_lower_slope, lower)

            if self.max_upper_slope > self.min_lower_slope:
                self.corridor_point = self.last_inbound_point

                self.upper_door_pivot = (self.corridor_point[0], self.corridor_point[1] + self.error)
                self.lower_door_pivot = (self.corridor_point[0], self.corridor_point[1] - self.error)

                self.max_upper_slope = float('-inf')
                self.min_lower_slope = float('inf')

                self.process(p)
                return False, self.corridor_point

            self.last_inbound_point = p
            return True, None

    def compress(self, serie: List[Tuple[int, float]]):

        def _compress():
            sdt = self._SDT(self.error, serie[0])
            pts = [serie[0]]

            for p in serie[1:]:
                ok, out = sdt.process(p)
                if not ok:
                    pts.append(out)

            if pts[-1] != serie[-1]:
                pts.append(serie[-1])

            return pts

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