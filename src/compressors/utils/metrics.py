import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from math import log10, isinf
from skimage.metrics import structural_similarity as ssim
from scipy.signal import find_peaks


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
        if range_true == 0:
            return 0.0
        return self.rmse() / range_true

    def ssim(self):
        s_true = self.__serie1.to_numpy()
        s_pred = self.__serie2.to_numpy()
        
        range_true = s_true.max() - s_true.min()
        if range_true == 0:
            return 1.0 if np.array_equal(s_true, s_pred) else 0.0

        return float(ssim(s_true, s_pred, data_range=range_true))

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

    def peak_recall(self, prominence: float = None, position_tolerance: int = None):
        """
        Fração dos picos da série original que foram preservados na série comprimida.

        Um pico original é considerado preservado se existe ao menos um pico
        na série comprimida dentro da janela de tolerância de posição.

        Parâmetros
        ----------
        prominence : float, opcional
            Proeminência mínima para considerar um ponto como pico.
            Padrão: 10% do range da série original.
        position_tolerance : int, opcional
            Tolerância em número de amostras para casar picos entre as séries.
            Padrão: 1% do comprimento da série (mínimo 1).

        Retorna
        -------
        float : valor entre 0.0 e 1.0, ou None se não houver picos na original.
        """
        s_true = self.__serie1.to_numpy()
        s_pred = self.__serie2.to_numpy()

        if prominence is None:
            prominence = 0.1 * (s_true.max() - s_true.min())
        if position_tolerance is None:
            position_tolerance = max(1, int(0.01 * len(s_true)))

        peaks_true, _ = find_peaks(s_true, prominence=prominence)

        if len(peaks_true) == 0:
            return None

        peaks_pred, _ = find_peaks(s_pred, prominence=prominence)

        preserved = sum(
            1 for p in peaks_true
            if np.any(np.abs(peaks_pred - p) <= position_tolerance)
        )

        return preserved / len(peaks_true)

    def peak_amplitude_error(self, prominence: float = None, position_tolerance: int = None):
        """
        Erro médio normalizado de amplitude nos picos preservados.

        Para cada pico da série original que tem correspondência na comprimida
        (dentro da tolerância de posição), calcula o erro absoluto de amplitude
        normalizado pelo valor do pico original.

        Parâmetros
        ----------
        prominence : float, opcional
            Proeminência mínima para considerar um ponto como pico.
            Padrão: 10% do range da série original.
        position_tolerance : int, opcional
            Tolerância em número de amostras para casar picos entre as séries.
            Padrão: 1% do comprimento da série (mínimo 1).

        Retorna
        -------
        float : erro médio em percentual (0–100+), ou None se não houver picos casados.
        """
        s_true = self.__serie1.to_numpy()
        s_pred = self.__serie2.to_numpy()

        if prominence is None:
            prominence = 0.1 * (s_true.max() - s_true.min())
        if position_tolerance is None:
            position_tolerance = max(1, int(0.01 * len(s_true)))

        peaks_true, _ = find_peaks(s_true, prominence=prominence)

        if len(peaks_true) == 0:
            return None

        peaks_pred, _ = find_peaks(s_pred, prominence=prominence)

        errors = []
        for p in peaks_true:
            candidates = peaks_pred[np.abs(peaks_pred - p) <= position_tolerance]
            if len(candidates) == 0:
                continue
            # Pico mais próximo em posição
            nearest = candidates[np.argmin(np.abs(candidates - p))]
            amp_true = s_true[p]
            amp_pred = s_pred[nearest]
            if amp_true != 0:
                errors.append(abs(amp_true - amp_pred) / abs(amp_true) * 100)

        return float(np.mean(errors)) if errors else None

    @staticmethod
    def energy(serie: pd.Series):
        return serie.sum() / 60

    @staticmethod
    def energy_total(serie: pd.Series):
        return serie.abs().sum() / 60

    def energy_error(self):
        e1 = Metrics.energy(self.__serie1)
        e2 = Metrics.energy(self.__serie2)

        if e1 == 0:
            return None

        return 100 * abs((e1 - e2) / e1)

    def energy_error_total(self):
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
            "PeakRecall": self.peak_recall(),
            "PeakAmplitudeError": self.peak_amplitude_error(),
        }

        return response