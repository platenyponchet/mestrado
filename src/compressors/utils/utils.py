import matplotlib.pyplot as plt
import pandas as pd
from math import log10, isinf
from skimage.metrics import structural_similarity as ssim


# Removed 
# AUC Score
# Hits

class Metrics:
    __serie1 = None
    __serie2 = None

    def __init__(self, s1, s2):
        self.__serie1 = pd.Series(s1)
        self.__serie2 = pd.Series(s2)
        pass

    def mse(self):
        return float(((self.__serie1 - self.__serie2) ** 2).mean())

    def rmse(self):
        return self.mse() ** 0.5

    def nrmse(self):
        range_true = float(self.__serie1.max() - self.__serie1.min())
        return self.rmse() / range_true

    def mape(self):
        mask = self.__serie1 != 0
        return float((abs(self.__serie1[mask] - self.__serie2[mask]) / self.__serie1[mask]).mean()) * 100

    def jaccard(self, tol=5):
        tolerance = tol/100

        threshold = self.__serie1 * tolerance

        intersection = ((abs(self.__serie1 - self.__serie2) <= threshold).sum())
        union = ((self.__serie1.notna() | self.__serie2.notna()).sum())

        return float(intersection / union)

    def isd(self):
        diff = self.__serie1 - self.__serie2
        return float((diff ** 2).sum())

    def prd(self):
        numerador = ((self.__serie1 - self.__serie2) ** 2).sum() ** 0.5

        denominador = (self.__serie1 ** 2).sum() ** 0.5

        return 100 * float(numerador / denominador)

    def snr(self):
        signal_power = (self.__serie1 ** 2).sum()
        noise_power = ((self.__serie1 - self.__serie2) ** 2).sum()

        result = 10 * log10(signal_power / noise_power)

        return None if isinf(result) else result

    def psnr(self):
        max_i = self.__serie1.max()

        result = 10 * log10((max_i ** 2) / self.mse())

        return None if isinf(result) else result

    def ssim(self):
        s_true = self.__serie1.to_numpy()
        s_pred = self.__serie2.to_numpy()

        return float(ssim(s_true, s_pred, data_range=s_true.max() - s_true.min()))

    @staticmethod
    def energy(serie:pd.Series):
        return serie.sum()/60

    def energy_error(self):
        return 100*abs(float(
            (Metrics.energy(self.__serie1) - Metrics.energy(self.__serie2))/Metrics.energy(self.__serie1)
        ))

    def compute_metrics(self):
        response = {
            "MSE": self.mse(),
            "RMSE": self.rmse(),
            "NRMSE": self.nrmse(),
            "MAPE": self.mape(),
            "Jaccard": self.jaccard(),
            "ISD": self.isd(),
            "PRD": self.prd(),
            "SNR": self.snr(),
            "PSNR": self.psnr(),
            "SSIM": self.ssim(),
            "EnergyError": self.energy_error()
        }

        return response

def plot_compression(orig_values, comp_values, orig_dt=None, comp_dt=None, label="None"):
    plt.figure(figsize=(10, 5))
    plt.plot(orig_dt, orig_values, label=f"Original", alpha=0.5)
    plt.plot(comp_dt, comp_values, label=f"Compressed")
    plt.legend()
    plt.xlabel("datetime")
    plt.ylabel("value")
    plt.title(
        f"{label}"
    )
    plt.grid(True)
    plt.tight_layout()
    plt.show()