import numpy as np
from scipy.fftpack import dct, idct
from ..utils.monitor import medir_pico_memoria
from ..utils.metrics import Metrics

class DCTCompressor:
    def __init__(self, cr=80):
        self.cr = cr # % de redução desejada (ex: 80 para 80% menor)

        self.compression_ratio = None
        self.execution_time = None
        self.memory_usage_mb = None
        self.metrics = None

    def compress(self, serie):

        def _compress():
            # Força float32 para basear o cálculo em 4 bytes
            x = np.array([p[1] for p in serie], dtype=np.float32)

            xmin, xmax = np.min(x), np.max(x)
            # Normalização (ajuda na estabilidade numérica da DCT)
            x_norm = (x - xmin) / (xmax - xmin + 1e-12)

            # Aplica a Transformada Discreta de Cosseno
            coeffs = dct(x_norm, norm='ortho')
            
            N = len(x)
            byte_sz = 4
            
            # --- CÁLCULO DO ORÇAMENTO BASEADO EM % ---
            tamanho_original = N * byte_sz
            
            # Se CR=80, queremos que o tamanho_alvo seja 20% do original
            percentual_manter = round((1 - self.cr / 100),10)
            tamanho_alvo = tamanho_original * percentual_manter

            # OVERHEAD: Apenas xmin, xmax e N (3 metadados fixos)
            overhead_fixo = 3 * byte_sz

            # CÁLCULO DE K: 
            # Na DCT, geralmente enviamos os K primeiros coeficientes em ordem.
            # Como eles estão em sequência, NÃO precisamos enviar o índice de cada um.
            # Portanto, cada coeficiente custa apenas 4 bytes (o valor float32).
            custo_p_coeficiente = 4 
            K = max(1, int((tamanho_alvo - overhead_fixo) / custo_p_coeficiente))

            # Mantém apenas os K primeiros (Truncamento de baixa frequência)
            compressed_coeffs = np.zeros(N, dtype=np.float32)
            compressed_coeffs[:K] = coeffs[:K]

            # Cálculo final do CR real atingido
            tamanho_transmitido = (K * custo_p_coeficiente) + overhead_fixo
            cr_real = 100 * (1 - (tamanho_transmitido / tamanho_original))

            return compressed_coeffs, cr_real, xmin, xmax, len(x)

        # Execução com monitoramento de memória e tempo
        (compressed_coeffs, ratio, xmin, xmax, n), t_exec, mem = medir_pico_memoria(_compress)

        self.execution_time = t_exec
        self.memory_usage_mb = mem
        self.compression_ratio = ratio

        # --- RECONSTRUÇÃO ---
        t = [p[0] for p in serie]

        # Inversa da DCT
        x_rec = idct(compressed_coeffs, norm='ortho')
        x_rec = x_rec[:n]
        # Reverte a escala original
        x_rec = x_rec * (xmax - xmin) + xmin

        reconstruido = list(zip(t, x_rec.tolist()))

        # Cálculo de métricas
        original_vals = [p[1] for p in serie]
        reconstruido_vals = [v for _, v in reconstruido]
        self.metrics = Metrics(original_vals, reconstruido_vals).compute_metrics()

        return reconstruido