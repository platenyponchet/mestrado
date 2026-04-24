import pytest
from src.compressors.wavelet import WaveletCompressor


# ── Testes de integração: WaveletCompressor ───────────────────────────────────

class TestWaveletCompressor:
    def test_compress_retorna_tamanho_correto(self, serie_media):
        c = WaveletCompressor(wavelet="db4", level=4, cr=80)
        result = c.compress(serie_media)
        assert len(result) == len(serie_media)

    def test_compression_ratio_na_faixa(self, serie_media):
        c = WaveletCompressor(cr=80)
        c.compress(serie_media)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_nao_negativo(self, serie_media):
        c = WaveletCompressor(cr=80)
        c.compress(serie_media)
        assert c.execution_time >= 0

    def test_memory_usage_nao_negativo(self, serie_media):
        c = WaveletCompressor(cr=80)
        c.compress(serie_media)
        assert c.memory_usage_mb >= 0

    def test_metrics_contem_todas_as_chaves(self, serie_media, metric_keys):
        c = WaveletCompressor(cr=80)
        c.compress(serie_media)
        assert set(c.metrics.keys()) == metric_keys

    def test_cr_maior_comprime_mais(self, serie_media):
        c_baixo = WaveletCompressor(cr=20)
        c_alto = WaveletCompressor(cr=90)
        c_baixo.compress(serie_media)
        c_alto.compress(serie_media)
        assert c_alto.compression_ratio >= c_baixo.compression_ratio

    def test_diferentes_wavelets_retornam_mesmo_tamanho(self, serie_media):
        for wavelet in ("db4", "haar", "sym4"):
            c = WaveletCompressor(wavelet=wavelet, cr=80)
            result = c.compress(serie_media)
            assert len(result) == len(serie_media), f"falhou para wavelet={wavelet}"

    def test_timestamps_preservados(self, serie_media):
        c = WaveletCompressor(cr=80)
        result = c.compress(serie_media)
        assert [t for t, _ in result] == [t for t, _ in serie_media]
