import pytest
from src.compressors.sdt import SDTCompressor


# ── Testes unitários: SDTCompressor._SDT ─────────────────────────────────────

class TestSDTInner:
    def test_mesmo_timestamp_retorna_valido(self):
        # dx == 0 → retorna True, None sem processar
        sdt = SDTCompressor._SDT(error=5.0, first_point=(0, 100.0))
        valid, out = sdt.process((0, 100.0))
        assert valid is True
        assert out is None

    def test_serie_constante_nunca_quebra(self):
        # Série constante dentro do erro → corredor nunca se fecha
        sdt = SDTCompressor._SDT(error=5.0, first_point=(0, 100.0))
        for i in range(1, 10):
            valid, _ = sdt.process((i, 100.0))
            assert valid is True

    def test_salto_brusco_quebra_corredor(self):
        # Com erro=0.1 e salto de 0→10 seguido de -10, o corredor quebra
        sdt = SDTCompressor._SDT(error=0.1, first_point=(0, 0.0))
        sdt.process((1, 10.0))
        ok, out = sdt.process((2, -10.0))
        assert ok is False
        assert isinstance(out, tuple)
        assert len(out) == 2

    def test_quebra_retorna_ponto_do_corredor(self):
        # O ponto retornado ao quebrar deve ser o último ponto inbound
        sdt = SDTCompressor._SDT(error=0.1, first_point=(0, 0.0))
        sdt.process((1, 10.0))  # último inbound = (1, 10.0)
        ok, out = sdt.process((2, -10.0))
        if not ok:
            assert out == (1, 10.0)


# ── Testes de integração: SDTCompressor ──────────────────────────────────────

class TestSDTCompressor:
    def test_compress_retorna_tamanho_correto(self, serie_media):
        c = SDTCompressor(error=5.0)
        result = c.compress(serie_media)
        assert len(result) == len(serie_media)

    def test_compression_ratio_na_faixa(self, serie_media):
        c = SDTCompressor(error=5.0)
        c.compress(serie_media)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_nao_negativo(self, serie_media):
        c = SDTCompressor(error=5.0)
        c.compress(serie_media)
        assert c.execution_time >= 0

    def test_memory_usage_nao_negativo(self, serie_media):
        c = SDTCompressor(error=5.0)
        c.compress(serie_media)
        assert c.memory_usage_mb >= 0

    def test_metrics_contem_todas_as_chaves(self, serie_media, metric_keys):
        c = SDTCompressor(error=5.0)
        c.compress(serie_media)
        assert set(c.metrics.keys()) == metric_keys

    def test_erro_maior_gera_cr_maior(self, serie_media):
        c_strict = SDTCompressor(error=0.1)
        c_loose = SDTCompressor(error=50.0)
        c_strict.compress(serie_media)
        c_loose.compress(serie_media)
        assert c_loose.compression_ratio >= c_strict.compression_ratio

    def test_serie_constante_alta_compressao(self, serie_constante):
        # Série constante: SDT guarda só primeiro e último → CR alta
        c = SDTCompressor(error=0.1)
        c.compress(serie_constante)
        assert c.compression_ratio > 80
