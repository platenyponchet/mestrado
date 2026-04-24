import pytest
from src.compressors.dct import DCTCompressor


# ── Testes de integração: DCTCompressor ──────────────────────────────────────

class TestDCTCompressor:
    def test_compress_retorna_tamanho_correto(self, serie_media):
        c = DCTCompressor(cr=80)
        result = c.compress(serie_media)
        assert len(result) == len(serie_media)

    def test_compression_ratio_na_faixa(self, serie_media):
        c = DCTCompressor(cr=80)
        c.compress(serie_media)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_nao_negativo(self, serie_media):
        c = DCTCompressor(cr=80)
        c.compress(serie_media)
        assert c.execution_time >= 0

    def test_memory_usage_nao_negativo(self, serie_media):
        c = DCTCompressor(cr=80)
        c.compress(serie_media)
        assert c.memory_usage_mb >= 0

    def test_metrics_contem_todas_as_chaves(self, serie_media, metric_keys):
        c = DCTCompressor(cr=80)
        c.compress(serie_media)
        assert set(c.metrics.keys()) == metric_keys

    def test_cr_maior_comprime_mais(self, serie_media):
        c_baixo = DCTCompressor(cr=20)
        c_alto = DCTCompressor(cr=90)
        c_baixo.compress(serie_media)
        c_alto.compress(serie_media)
        assert c_alto.compression_ratio >= c_baixo.compression_ratio

    def test_cr_zero_reconstroi_bem(self, serie_media):
        # CR=0 mantém todos os coeficientes → reconstrução muito próxima do original
        c = DCTCompressor(cr=0)
        result = c.compress(serie_media)
        original_vals = [v for _, v in serie_media]
        reconstructed_vals = [v for _, v in result]
        mse = sum((a - b) ** 2 for a, b in zip(original_vals, reconstructed_vals)) / len(original_vals)
        assert mse < 1.0

    def test_timestamps_preservados(self, serie_media):
        c = DCTCompressor(cr=80)
        result = c.compress(serie_media)
        original_ts = [t for t, _ in serie_media]
        result_ts = [t for t, _ in result]
        assert original_ts == result_ts
