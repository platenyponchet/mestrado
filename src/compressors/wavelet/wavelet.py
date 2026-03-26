import pywt
import numpy as np
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics

class WaveletCompressor:
    def __init__(self, wavelet="db4", level=4, cr=80):
        self.wavelet = wavelet
        self.level = level
        self.cr = cr  # Agora tratado como % de redução (ex: 80 significa 80% menor)

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None
        self.metrics = None

    def compress(self, serie):

        def _compress():
            # Força float32 para garantir que cada ponto ocupe 4 bytes
            x = np.array([p[1] for p in serie], dtype=np.float32)

            xmin, xmax = np.min(x), np.max(x)
            x_norm = (x - xmin) / (xmax - xmin + 1e-12)

            coeffs = pywt.wavedec(x_norm, self.wavelet, level=self.level)
            coeff_arr, slices = pywt.coeffs_to_array(coeffs)
            
            N = len(x)
            byte_sz = 4 # float32 e int32 ocupam 4 bytes
            
            # --- CÁLCULO DO ORÇAMENTO BASEADO EM % ---
            tamanho_original = N * byte_sz
            
            # Se CR=80, queremos que o tamanho_alvo seja 20% do original (1 - 80/100)
            percentual_manter = round((1 - self.cr / 100),10)
            tamanho_alvo = tamanho_original * percentual_manter

            # Metadados: xmin(4), xmax(4), N(4) + estrutura de cada nível (2 valores por slice)
            # O "+2" no level é uma margem para a estrutura interna do objeto slices
            overhead_fixo = (3 + 2 * (self.level + 2)) * byte_sz

            # Cada coeficiente 'K' enviado custa 8 bytes: 4 (valor) + 4 (índice original)
            custo_p_coeficiente = 8
            K = max(1, int((tamanho_alvo - overhead_fixo) / custo_p_coeficiente))

            # Hard Thresholding: mantém apenas os K maiores em magnitude
            abs_coeffs = np.abs(coeff_arr)
            # Ordena decrescente e pega o valor na posição K-1 como limite
            threshold = np.sort(abs_coeffs)[::-1][K - 1] if K <= len(abs_coeffs) else 0
            compressed_arr = coeff_arr * (abs_coeffs >= threshold)

            # Cálculo final do CR real atingido
            tamanho_transmitido = (K * custo_p_coeficiente) + overhead_fixo
            cr_real = 100 * (1 - (tamanho_transmitido / tamanho_original))

            return compressed_arr, slices, cr_real, xmin, xmax, len(x)

        # Execução com monitoramento
        (compressed_arr, slices, ratio, xmin, xmax, n), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        # --- RECONSTRUÇÃO ---
        t = [p[0] for p in serie]
        coeffs_rec = pywt.array_to_coeffs(compressed_arr, slices, output_format="wavedec")
        x_rec = pywt.waverec(coeffs_rec, self.wavelet)
        
        # Ajusta tamanho (waverec pode retornar um ponto a mais dependendo da wavelet)
        x_rec = x_rec[:n] 
        # Reverte a normalização
        x_rec = x_rec * (xmax - xmin) + xmin

        reconstruido = list(zip(t, x_rec.tolist()))

        # Cálculo de métricas de erro (RMSE, MAE, etc)
        original_vals = [p[1] for p in serie]
        reconstruido_vals = [v for _, v in reconstruido]
        self.metrics = Metrics(original_vals, reconstruido_vals).compute_metrics()

        return reconstruido