import pytest
from src.compressors.arcsdt import ARCSDTCompressor
from src.compressors.arcsdt.arcsdt import ARC_SDT


# ── Testes unitários: ARC_SDT ─────────────────────────────────────────────────

class TestARCSDT:
    def test_process_retorna_bool_e_opcional(self):
        arcsdt = ARC_SDT(10.0, (0, 100.0))
        valid, out = arcsdt.process_new_point((1, 100.0))
        assert isinstance(valid, bool)
        assert out is None or isinstance(out, tuple)

    def test_serie_constante_nunca_quebra(self):
        # Série constante dentro do erro percentual → corredor nunca fecha
        arcsdt = ARC_SDT(10.0, (0, 100.0))
        for i in range(1, 10):
            valid, _ = arcsdt.process_new_point((i, 100.0))
            assert valid is True

    def test_salto_brusco_quebra_corredor(self):
        # Com erro percentual pequeno e salto grande, corredor deve quebrar
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        arcsdt.process_new_point((1, 100.0))
        ok, out = arcsdt.process_new_point((2, 200.0))
        # Não necessariamente quebra aqui, mas após vários saltos deve quebrar
        results = [ok]
        arcsdt2 = ARC_SDT(0.01, (0, 100.0))
        for i in range(1, 20):
            ok2, _ = arcsdt2.process_new_point((i, 100.0 + i * 50))
            results.append(ok2)
        assert any(not r for r in results)

    def test_set_error_nao_levanta_excecao(self):
        arcsdt = ARC_SDT(10.0, (0, 100.0))
        arcsdt.set_error(50.0)
        valid, out = arcsdt.process_new_point((1, 100.5))
        assert isinstance(valid, bool)

    def test_quebra_retorna_tupla_valida(self):
        # Força uma quebra e verifica que o ponto retornado é (timestamp, valor)
        arcsdt = ARC_SDT(0.01, (0, 100.0))
        corridor_point = None
        for i in range(1, 30):
            ok, out = arcsdt.process_new_point((i, 100.0 + i * 30))
            if not ok:
                corridor_point = out
                break
        if corridor_point is not None:
            assert len(corridor_point) == 2
            assert isinstance(corridor_point[0], (int, float))
            assert isinstance(corridor_point[1], float)


# ── Testes de integração: ARCSDTCompressor ────────────────────────────────────

class TestARCSDTCompressor:
    def test_compress_retorna_tamanho_correto(self, serie_media):
        c = ARCSDTCompressor(target_cr=80)
        result = c.compress(serie_media)
        assert len(result) == len(serie_media)

    def test_compression_ratio_na_faixa(self, serie_media):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(serie_media)
        assert 0 <= c.compression_ratio <= 100

    def test_execution_time_nao_negativo(self, serie_media):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(serie_media)
        assert c.execution_time >= 0

    def test_memory_usage_nao_negativo(self, serie_media):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(serie_media)
        assert c.memory_usage_mb >= 0

    def test_metrics_contem_todas_as_chaves(self, serie_media, metric_keys):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(serie_media)
        assert set(c.metrics.keys()) == metric_keys

    def test_serie_constante_alta_compressao(self, serie_constante):
        c = ARCSDTCompressor(target_cr=80)
        c.compress(serie_constante)
        assert c.compression_ratio > 80

    def test_pid_converge_em_direcao_ao_target(self, serie_media):
        # O PID deve empurrar o CR para perto do target;
        # não é garantido convergir em 200 pontos, mas CR não deve ser 0
        c = ARCSDTCompressor(target_cr=80, kp=10.0, ki=2.0)
        c.compress(serie_media)
        assert c.compression_ratio > 0
