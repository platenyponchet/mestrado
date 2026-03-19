import matplotlib.pyplot as plt
import pandas as pd
from math import log10, isinf
from skimage.metrics import structural_similarity as ssim


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
        return float((abs(self.__serie1[mask] - self.__serie2[mask]) / abs(self.__serie1[mask])).mean()) * 100

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

        if signal_power == 0 or noise_power == 0:
            return None

        result = 10 * log10(signal_power / noise_power)
        return None if isinf(result) else result

    def psnr(self):
        max_i = self.__serie1.max()
        mse = self.mse()

        if max_i == 0 or mse == 0:
            return None

        result = 10 * log10((max_i ** 2) / mse)
        return None if isinf(result) else result

    def ssim(self):
        s_true = self.__serie1.to_numpy()
        s_pred = self.__serie2.to_numpy()

        return float(ssim(s_true, s_pred, data_range=s_true.max() - s_true.min()))

    @staticmethod
    def energy(serie: pd.Series):
        return serie.sum() / 60

    @staticmethod
    def energy_total(serie: pd.Series):
        """Energia total: soma dos valores absolutos de potência integrada no tempo.
        Não considera o sentido do fluxo de energia."""
        return serie.abs().sum() / 60

    def energy_error(self):
        """Erro percentual de energia líquida.
        Pode ser alto quando o saldo energético original é próximo de zero
        (ex: instalações com geração solar onde consumo e geração se equilibram)."""
        e1 = Metrics.energy(self.__serie1)
        e2 = Metrics.energy(self.__serie2)

        if e1 == 0:
            return None

        return 100 * abs((e1 - e2) / e1)

    def energy_error_total(self):
        """Erro percentual de energia total (sem considerar sentido do fluxo).
        Robusto para séries com valores negativos, pois o denominador é sempre positivo."""
        e1 = Metrics.energy_total(self.__serie1)
        e2 = Metrics.energy_total(self.__serie2)

        if e1 == 0:
            return None

        return 100 * abs((e1 - e2) / e1)

    def compute_metrics(self):
        response = {
            "MSE": self.mse(),
            "RMSE": self.rmse(),
            "NRMSE": self.nrmse(),
            "MAPE": self.mape(),
            "ISD": self.isd(),
            "PRD": self.prd(),
            "SNR": self.snr(),
            "PSNR": self.psnr(),
            "SSIM": self.ssim(),
            "EnergyError": self.energy_error(),
            "EnergyErrorTotal": self.energy_error_total(),
        }

        return response