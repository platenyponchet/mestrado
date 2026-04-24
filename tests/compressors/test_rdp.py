import pytest
from src.compressors.rdp import RDPCompressor


# ── Testes unitários: RDPCompressor._dist ─────────────────────────────────────

class TestDist:
    def setup_method(self):
        self.c = RDPCompressor(epsilon=1.0)

    def test_ponto_sobre_a_reta_distancia_zero(self):
        # (1,1) está sobre a reta (0,0)-(2,2)
        assert self.c._dist((1, 1), (0, 0), (2, 2)) == pytest.approx(0.0, abs=1e-9)

    def test_distancia_perpendicular_conhecida(self):
        # Reta y=0 de (0,0) a (2,0); ponto (1,5) → distância = 5
        assert self.c._dist((1, 5), (0, 0), (2, 0)) == pytest.approx(5.0)

    def test_endpoints_iguais_usa_distancia_vertical(self):
        # a == b: usa |y - y1|
        assert self.c._dist((1, 3), (2, 2), (2, 2)) == pytest.approx(abs(3 - 2))


# ── Testes unitários: RDPCompressor._rdp ──────────────────────────────────────

class TestRDP:
    def test_menos_de_tres_pontos_retorna_todos(self):
        c = RDPCompressor(epsilon=1.0)
        pts = [(0, 0), (1, 1)]
        assert c._rdp(pts) == pts

    def test_pontos_colineares_retorna_apenas_extremos(self):
        # (0,0), (1,1), (2,2), (3,3) — todos sobre y=x
        c = RDPCompressor(epsilon=0.5)
        result = c._rdp([(0, 0), (1, 1), (2, 2), (3, 3)])
        assert result == [(0, 0), (3, 3)]

    def test_pico_acima_epsilon_e_preservado(self):
        # (1, 100) está muito longe da reta (0,0)-(2,0) → deve ser mantido
        c = RDPCompressor(epsilon=0.5)
        result = c._rdp([(0, 0), (1, 100), (2, 0)])
        assert len(result) == 3

    def test_epsilon_zero_preserva_pontos_nao_colineares(self):
        # Zigzag: nenhum ponto intermediário é colinear com seus vizinhos
        # → com epsilon=0 todos devem ser preservados
        c = RDPCompressor(epsilon=0.0)
        pts = [(0, 0), (1, 1), (2, 0), (3, 1), (4, 0)]
        result = c._rdp(pts)
        assert len(result) == len(pts)

    def test_epsilon_alto_remove_intermediarios(self):
        # Com epsilon muito alto, apenas extremos sobram
        c = RDPCompressor(epsilon=1000.0)
        pts = [(i, float(i)) for i in range(10)]
        result = c._rdp(pts)
        assert result == [pts[0], pts[-1]]


# ── Testes de integração: RDPCompressor ──────────────────────────────────────

class TestRDPCompressor:
    def test_compress_retorna_tamanho_correto(self, serie_media):
        c = RDPCompressor(epsilon=1.0)
        result = c.compress(serie_media)
        assert len(result) == len(serie_media)

    def test_compression_ratio_na_faixa(self, serie_media):
        c = RDPCompressor(epsilon=1.0)
        c.compress(serie_media)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_nao_negativo(self, serie_media):
        c = RDPCompressor(epsilon=1.0)
        c.compress(serie_media)
        assert c.execution_time >= 0

    def test_memory_usage_nao_negativo(self, serie_media):
        c = RDPCompressor(epsilon=1.0)
        c.compress(serie_media)
        assert c.memory_usage_mb >= 0

    def test_metrics_contem_todas_as_chaves(self, serie_media, metric_keys):
        c = RDPCompressor(epsilon=1.0)
        c.compress(serie_media)
        assert set(c.metrics.keys()) == metric_keys

    def test_epsilon_maior_gera_cr_maior(self, serie_media):
        c_strict = RDPCompressor(epsilon=0.01)
        c_loose = RDPCompressor(epsilon=100.0)
        c_strict.compress(serie_media)
        c_loose.compress(serie_media)
        assert c_loose.compression_ratio >= c_strict.compression_ratio

    def test_serie_constante_alta_compressao(self, serie_constante):
        # Série constante: todos os pontos são colineares → só extremos sobram
        c = RDPCompressor(epsilon=0.01)
        c.compress(serie_constante)
        assert c.compression_ratio > 80
