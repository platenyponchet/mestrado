import pywt
import numpy as np
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics


class WaveletCompressor:
    def __init__(self, wavelet="db4", level=4, cr=10):
        self.wavelet = wavelet
        self.level = level
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

            coeffs = pywt.wavedec(x_norm, self.wavelet, level=self.level)

            coeff_arr, slices = pywt.coeffs_to_array(coeffs)
            N = len(coeff_arr)

            tamanho_original = N * 8
            overhead_fixo = (3 + 2 * (self.level + 2)) * 8  # xmin, xmax, N + slices

            target = 1 - 1 / self.cr
            K = max(1, int((tamanho_original * (1 - target) - overhead_fixo) / 12))

            # mantém os K maiores em magnitude — hard thresholding global
            threshold = np.sort(np.abs(coeff_arr))[::-1][K - 1]
            compressed_arr = coeff_arr * (np.abs(coeff_arr) >= threshold)

            tamanho_transmitido = K * 12 + overhead_fixo
            compression_ratio = 100 * (1 - tamanho_transmitido / tamanho_original)

            return compressed_arr, slices, compression_ratio, xmin, xmax, len(x)

        (compressed_arr, slices, ratio, xmin, xmax, n), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        # reconstrução fora do monitor
        t = [p[0] for p in serie]

        coeffs_rec = pywt.array_to_coeffs(compressed_arr, slices, output_format="wavedec")
        x_rec = pywt.waverec(coeffs_rec, self.wavelet)
        x_rec = x_rec[:n]
        x_rec = x_rec * (xmax - xmin) + xmin

        reconstruido = list(zip(t, x_rec.tolist()))

        original = [v for _, v in serie]
        reconstruido_vals = [v for _, v in reconstruido]
        self.metrics = Metrics(original, reconstruido_vals).compute_metrics()

        return reconstruido