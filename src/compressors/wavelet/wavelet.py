import pywt
import numpy as np
from ..utils.monitor import medir_pico_memoria


class WaveletCompressor:
    def __init__(self, wavelet="db1", level=2, keep=1):
        self.wavelet = wavelet
        self.level = level
        self.keep = keep

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

            # wavelet
            coeffs = pywt.wavedec(x_norm, self.wavelet, level=self.level)

            # mantém apenas aproximação + nível escolhido
            compressed_coeffs = []

            for i in range(len(coeffs)):
                if i == 0 or i == self.keep:
                    compressed_coeffs.append(coeffs[i])
                else:
                    compressed_coeffs.append(np.zeros_like(coeffs[i]))

            # tamanho "comprimido"
            compressed_len = sum(
                np.count_nonzero(c) for c in compressed_coeffs
            )

            original_len = len(x)

            compression_ratio = 100 * (1 - compressed_len / original_len)

            # reconstrução
            x_rec = pywt.waverec(compressed_coeffs, self.wavelet)
            x_rec = x_rec[:len(x)]

            # desnormalização
            x_rec = x_rec * (xmax - xmin) + xmin

            reconstruido = list(zip(t, x_rec))

            return reconstruido, compression_ratio

        (reconstruido, ratio), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        return reconstruido