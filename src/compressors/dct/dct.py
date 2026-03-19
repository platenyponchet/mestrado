import numpy as np
from scipy.fftpack import dct, idct
from ..utils.monitor import medir_pico_memoria


class DCTCompressor:
    def __init__(self, cr=10):
        self.cr = cr

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None

    def compress(self, serie):

        def _compress():
            t = [p[0] for p in serie]
            x = np.array([p[1] for p in serie], dtype=np.float64)

            # normalização
            xmin, xmax = np.min(x), np.max(x)
            x_norm = (x - xmin) / (xmax - xmin + 1e-12)

            # DCT
            coeffs = dct(x_norm, norm='ortho')
            N = len(coeffs)
            K = max(1, int(N / self.cr))

            # zera coeficientes acima de K
            compressed_coeffs = np.zeros(N)
            compressed_coeffs[:K] = coeffs[:K]

            compressed_len = K
            original_len = N
            compression_ratio = 100 * (1 - compressed_len / original_len)

            # reconstrução
            x_rec = idct(compressed_coeffs, norm='ortho')
            x_rec = x_rec[:len(x)]

            # desnormalização
            x_rec = x_rec * (xmax - xmin) + xmin

            reconstruido = list(zip(t, x_rec.tolist()))

            return reconstruido, compression_ratio

        (reconstruido, ratio), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        return reconstruido