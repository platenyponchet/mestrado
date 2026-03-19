import numpy as np
from scipy.fftpack import dct, idct
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics


class DCTCompressor:
    def __init__(self, cr=10):
        self.cr = cr

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None
        self.metrics = None

    def compress(self, serie):

        def _compress():
            x = np.array([p[1] for p in serie], dtype=np.float64)

            xmin, xmax = np.min(x), np.max(x)
            x_norm = (x - xmin) / (xmax - xmin + 1e-12)

            coeffs = dct(x_norm, norm='ortho')
            N = len(coeffs)
            K = max(1, int(N / self.cr))

            compressed_coeffs = np.zeros(N)
            compressed_coeffs[:K] = coeffs[:K]

            tamanho_original = N * 8
            tamanho_transmitido = (K + 3) * 8
            compression_ratio = 100 * (1 - tamanho_transmitido / tamanho_original)

            return compressed_coeffs, compression_ratio, xmin, xmax, len(x)

        (compressed_coeffs, ratio, xmin, xmax, n), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        # reconstrução fora do monitor
        t = [p[0] for p in serie]

        x_rec = idct(compressed_coeffs, norm='ortho')
        x_rec = x_rec[:n]
        x_rec = x_rec * (xmax - xmin) + xmin

        reconstruido = list(zip(t, x_rec.tolist()))

        original = [v for _, v in serie]
        reconstruido_vals = [v for _, v in reconstruido]
        self.metrics = Metrics(original, reconstruido_vals).compute_metrics()

        return reconstruido