import numpy as np
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics
from math import sqrt, pow
from typing import Tuple, Optional


class ARC_SDT:
    def __init__(self, percentual_error: float, first_point: Tuple[int, float], min_absolute_error: float = 1):
        self.__percentual_error = percentual_error
        self.__corridor_point = first_point
        self.__last_inbound_point = first_point
        self.__ms = pow(first_point[1], 2)
        self.__N = 1
        self.__min_absolute_error = min_absolute_error

        self.__error = max(sqrt(self.__ms) * percentual_error / 100.0, self.__min_absolute_error)

        self.__upper_door_pivot = (first_point[0], first_point[1] + self.__error)
        self.__lower_door_pivot = (first_point[0], first_point[1] - self.__error)
        self.__max_upper_slope = float('-inf')
        self.__min_lower_slope = float('inf')

    def set_error(self, new_error: float):
        self.__percentual_error = new_error

    def process_new_point(self, incoming_point: Tuple[int, float], ignore_rms=False) -> Tuple[bool, Optional[Tuple[int, float]]]:
        if not ignore_rms:
            self.__N += 1
            self.__ms = self.__ms + (pow(incoming_point[1], 2) - self.__ms) / self.__N
            self.__error = max(sqrt(self.__ms) * self.__percentual_error / 100.0, self.__min_absolute_error)
            self.__upper_door_pivot = (self.__corridor_point[0], self.__corridor_point[1] + self.__error)
            self.__lower_door_pivot = (self.__corridor_point[0], self.__corridor_point[1] - self.__error)

        upper_slope = (incoming_point[1] - self.__upper_door_pivot[1]) / (incoming_point[0] - self.__upper_door_pivot[0])
        lower_slope = (incoming_point[1] - self.__lower_door_pivot[1]) / (incoming_point[0] - self.__lower_door_pivot[0])

        if upper_slope > self.__max_upper_slope:
            self.__max_upper_slope = upper_slope
        if lower_slope < self.__min_lower_slope:
            self.__min_lower_slope = lower_slope

        if self.__max_upper_slope > self.__min_lower_slope:
            self.__corridor_point = self.__last_inbound_point
            self.__upper_door_pivot = (self.__corridor_point[0], self.__corridor_point[1] + self.__error)
            self.__lower_door_pivot = (self.__corridor_point[0], self.__corridor_point[1] - self.__error)
            self.__max_upper_slope = float('-inf')
            self.__min_lower_slope = float('inf')
            self.process_new_point(incoming_point, ignore_rms=True)
            return False, self.__corridor_point
        else:
            self.__last_inbound_point = incoming_point
            return True, None


class ARCSDTCompressor:
    def __init__(self, percentual_error: float = 10.0, target_cr: float = 80.0,
                 kp: float = 10.0, ki: float = 2, kd: float = 0.0,
                 update_interval: int = 1, min_absolute_error: float = 1.0):
        self.percentual_error = target_cr
        self.target_cr = target_cr
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.update_interval = update_interval
        self.min_absolute_error = min_absolute_error

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None
        self.metrics = None

    def compress(self, serie):

        def _compress():
            integral = 0.0
            prev_error = None
            deriv_filtered = 0.0
            deriv_filter_alpha = 0.9
            output_limits = (1, 10000)  # Limites para o erro percentual

            def pid_update(measured, dt=1.0):
                nonlocal integral, prev_error, deriv_filtered

                error = self.target_cr - measured

                if prev_error is not None and (error * prev_error) < 0:
                    integral = 0.0

                tentative_integral = integral + error * dt

                raw_deriv = 0.0
                if prev_error is not None and dt > 0:
                    raw_deriv = (error - prev_error) / dt
                deriv_filtered = (deriv_filter_alpha * deriv_filtered +
                                (1 - deriv_filter_alpha) * raw_deriv)

                out = (self.kp * error) + (self.ki * tentative_integral) + (self.kd * deriv_filtered)

                low, high = output_limits
                if out < low or out > high:
                    out = max(low, min(high, out))
                else:
                    integral = tentative_integral

                prev_error = error
                return out

            pts = [serie[0]]
            arcsdt = ARC_SDT(self.percentual_error, serie[0], self.min_absolute_error)

            for i, point in enumerate(serie[1:], start=1):
                valid, corridor_point = arcsdt.process_new_point(point)
                if not valid:
                    pts.append(corridor_point)

                if (i + 1) % self.update_interval == 0 or i == len(serie) - 1:
                    current_cr = 100 * (1 - len(pts) / (i + 1))
                    new_error = pid_update(current_cr)
                    arcsdt.set_error(new_error)

            if pts[-1] != serie[-1]:
                pts.append(serie[-1])

            compression_ratio = 100 * (1 - len(pts) / len(serie))

            return pts, compression_ratio

        # 🔥 apenas a compressão é monitorada
        (pts, ratio), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        # reconstrução fora do monitor
        reconstruido = []
        idx = 0

        for i in range(len(pts) - 1):
            t0, v0 = pts[i]
            t1, v1 = pts[i + 1]

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