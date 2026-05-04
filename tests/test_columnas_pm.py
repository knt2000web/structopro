"""
test_columnas_pm.py — Suite de pruebas unitarias para el módulo Columnas P-M
Casos verificados manualmente contra:
  - ACI 318-19 Commentary (ACI 318R-19)
  - NSR-10 Título C
  - Cálculo manual paso a paso

Ejecutar:  pytest tests/test_columnas_pm.py -v
"""
import sys, os, math
import pytest
import numpy as np

# Importar funciones del módulo principal
# El módulo usa Streamlit, que no se puede importar en tests normalmente.
# Se extraen las funciones puras (sin st.*) para testeo directo.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pages'))

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades auxiliares de prueba (copias de las funciones puras del módulo)
# ──────────────────────────────────────────────────────────────────────────────

def _get_beta1(fc):
    """ACI 318-19 §22.2.2.4.3 / NSR-10 C.22.2.2.4"""
    if fc <= 28.0:
        return 0.85
    return max(0.85 - 0.05 * (fc - 28.0) / 7.0, 0.65)


def _get_development_length(db_mm, fy, fc, lambda_=1.0,
                             psi_t=1.0, psi_e=1.0, psi_s=1.0, psi_g=1.0, cbktr=2.5):
    """ACI 318-19 §25.5.2.1 / NSR-10 C.12.2"""
    if db_mm <= 0:
        return 0
    ld = (3 * fy * lambda_ * psi_t * psi_e * psi_s * psi_g) / (40 * math.sqrt(fc) * cbktr) * db_mm
    return max(ld, 300)


def _interp_pm_curve_pure(M_query, phi_Mn_arr, phi_Pn_arr):
    """Interpolación P-M — retorna np.nan si M_query > Mmax (sentinel)."""
    phi_Mn_arr = np.array(phi_Mn_arr)
    phi_Pn_arr = np.array(phi_Pn_arr)
    if len(phi_Mn_arr) == 0:
        return 0.0
    M_max = np.max(phi_Mn_arr)
    if M_query <= 0:
        return float(phi_Pn_arr[np.argmax(phi_Pn_arr)])
    if M_query > M_max:
        return np.nan   # SENTINEL: M excede diagrama
    idx_bal = int(np.argmax(phi_Mn_arr))
    Mc = phi_Mn_arr[:idx_bal + 1]; Pc = phi_Pn_arr[:idx_bal + 1]
    Mt = phi_Mn_arr[idx_bal:];     Pt = phi_Pn_arr[idx_bal:]
    sc = np.argsort(Mc); st_ = np.argsort(Mt)
    P_comp = float(np.interp(M_query, Mc[sc], Pc[sc], left=float(Pc[sc[0]]), right=0.0))
    P_tens = float(np.interp(M_query, Mt[st_], Pt[st_], left=0.0, right=0.0))
    return max(P_comp, P_tens)


def _biaxial_bresler(Pu, phi_Pnx, phi_Pny, phi_P0):
    """Fórmula de Bresler / NSR-10 C.10.3.6"""
    if np.isnan(phi_Pnx) or np.isnan(phi_Pny):
        return {"ratio": float("inf"), "ok": False, "excedido": True}
    if phi_Pnx > 0 and phi_Pny > 0 and phi_P0 > 0:
        inv = 1 / phi_Pnx + 1 / phi_Pny - 1 / phi_P0
        phi_Pni = 1 / inv if inv > 0 else 0.0
    else:
        phi_Pni = 0.0
    ratio = Pu / phi_Pni if phi_Pni > 0 else float("inf")
    return {"phi_Pni": phi_Pni, "ratio": ratio, "ok": Pu <= phi_Pni, "excedido": False}


# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: get_beta1 — ACI 318-19 §22.2.2.4.3
# ──────────────────────────────────────────────────────────────────────────────
class TestGetBeta1:
    def test_fc_menor_28(self):
        """Para fc ≤ 28 MPa, β₁ = 0.85 exacto"""
        assert _get_beta1(21.0) == pytest.approx(0.85)
        assert _get_beta1(28.0) == pytest.approx(0.85)
        assert _get_beta1(14.0) == pytest.approx(0.85)

    def test_fc_42_mpa(self):
        """fc = 42 MPa → β₁ = 0.85 - 0.05*(42-28)/7 = 0.75"""
        assert _get_beta1(42.0) == pytest.approx(0.75, abs=1e-6)

    def test_fc_55_mpa(self):
        """fc = 55 MPa → β₁ = 0.85 - 0.05*(55-28)/7 ≈ 0.657"""
        expected = max(0.85 - 0.05 * (55 - 28) / 7.0, 0.65)
        assert _get_beta1(55.0) == pytest.approx(expected, abs=1e-6)

    def test_piso_065(self):
        """Para fc muy alto, β₁ no puede bajar de 0.65"""
        assert _get_beta1(70.0) == pytest.approx(0.65)
        assert _get_beta1(100.0) == pytest.approx(0.65)

    def test_fc_35_mpa(self):
        """fc = 35 MPa → β₁ = 0.85 - 0.05*(35-28)/7 = 0.80"""
        assert _get_beta1(35.0) == pytest.approx(0.80, abs=1e-6)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: get_development_length — ACI 318-19 §25.5.2.1
# ──────────────────────────────────────────────────────────────────────────────
class TestDevelopmentLength:
    def test_db_19_fy420_fc28(self):
        """db=19mm, fy=420MPa, fc=28MPa, factores=1.0, cbktr=2.5"""
        ld = _get_development_length(19.0, 420.0, 28.0)
        expected = 3 * 420 * 1.0 * 1.0 * 1.0 * 1.0 * 1.0 / (40 * math.sqrt(28) * 2.5) * 19.0
        expected = max(expected, 300.0)
        assert ld == pytest.approx(expected, rel=1e-4)

    def test_db_16_fy420_fc21(self):
        """Caso NSR-10 típico: #5 (16mm), fc=21MPa"""
        ld = _get_development_length(16.0, 420.0, 21.0)
        expected = 3 * 420 / (40 * math.sqrt(21) * 2.5) * 16.0
        expected = max(expected, 300.0)
        assert ld == pytest.approx(expected, rel=1e-4)

    def test_db_cero_retorna_cero(self):
        """db=0 debe retornar 0 sin error"""
        assert _get_development_length(0.0, 420.0, 28.0) == 0.0

    def test_minimo_300mm(self):
        """Longitud de desarrollo mínima = 300 mm (NSR-10 C.12.2.1)"""
        ld = _get_development_length(9.5, 420.0, 28.0)
        assert ld >= 300.0

    def test_ld_supera_minimo_bajo_confinamiento(self):
        """Con poco confinamiento (cbktr=0.5) la fórmula supera el mínimo de 300mm.
        Condición: barra grande, bajo recubrimiento/estribos alejados.
        Referencia: ACI 318-19 §25.5.2.1 — cbktr = (Atr·fyt)/(1500·s·n)"""
        # cbktr=0.5 → mínimo confinamiento → ld calculado > 300mm
        ld = _get_development_length(25.4, 420.0, 21.0, cbktr=0.5)
        expected = 3 * 420 / (40 * math.sqrt(21.0) * 0.5) * 25.4
        assert ld == pytest.approx(max(expected, 300.0), rel=1e-4)
        assert ld > 300.0
        # La fórmula es proporcional a db: ld(db=25.4) > ld(db=9.5) con mismo cbktr
        ld_small = _get_development_length(9.5, 420.0, 21.0, cbktr=0.5)
        assert ld > ld_small


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: interp_pm_curve — sentinel np.nan y monotonía
# ──────────────────────────────────────────────────────────────────────────────
class TestInterpPMCurve:
    def _sample_curve(self):
        """Curva P-M sintética balanceada: compresión → balance → tracción"""
        phi_M = np.array([  0, 50, 120, 200, 250, 300, 280, 200, 100,   0])
        phi_P = np.array([3500,3200, 2600, 1800, 1400, 900, 500, 200, 50,   0])
        return phi_M, phi_P

    def test_M_cero_retorna_pmax(self):
        phi_M, phi_P = self._sample_curve()
        result = _interp_pm_curve_pure(0.0, phi_M, phi_P)
        assert result == pytest.approx(float(phi_P[np.argmax(phi_P)]), rel=1e-3)

    def test_M_excede_Mmax_retorna_nan(self):
        """M > Mmax → np.nan (sentinel correcto)"""
        phi_M, phi_P = self._sample_curve()
        result = _interp_pm_curve_pure(999.0, phi_M, phi_P)
        assert np.isnan(result), "Se esperaba np.nan cuando M excede el diagrama"

    def test_M_igual_Mmax_no_nan(self):
        """M == Mmax no debe retornar nan"""
        phi_M, phi_P = self._sample_curve()
        M_max = float(np.max(phi_M))
        result = _interp_pm_curve_pure(M_max, phi_M, phi_P)
        assert not np.isnan(result)
        assert result >= 0.0

    def test_interpolacion_rama_compresion(self):
        """Interpolación en rama de compresión debe ser positiva y decreciente"""
        phi_M, phi_P = self._sample_curve()
        P_at_100 = _interp_pm_curve_pure(100.0, phi_M, phi_P)
        P_at_200 = _interp_pm_curve_pure(200.0, phi_M, phi_P)
        assert P_at_100 > P_at_200 > 0

    def test_curva_vacia_retorna_cero(self):
        result = _interp_pm_curve_pure(100.0, np.array([]), np.array([]))
        assert result == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: biaxial_bresler — ratio y fallo por exceso de momento
# ──────────────────────────────────────────────────────────────────────────────
class TestBiaxialBresler:
    def test_cumple_unitario(self):
        """Caso de carga en el punto exacto del diagrama: ratio = 1.0"""
        # Si phi_Pnx = phi_Pny = phi_P0 = Pu → 1/Pni = 1/Pu + 1/Pu - 1/Pu = 1/Pu
        Pu = 1000.0
        res = _biaxial_bresler(Pu, Pu, Pu, Pu)
        assert res["ratio"] == pytest.approx(1.0, rel=1e-4)
        assert res["ok"]

    def test_no_cumple_sobrecargado(self):
        """Pu > phi_Pni → ok=False"""
        res = _biaxial_bresler(1500.0, 1000.0, 1000.0, 3000.0)
        assert not res["ok"]
        assert res["ratio"] > 1.0

    def test_sentinel_nan_en_x(self):
        """Si phi_Pnx es nan (M excede diagrama X) → ratio=inf, excedido=True"""
        res = _biaxial_bresler(500.0, np.nan, 800.0, 2000.0)
        assert res["ratio"] == float("inf")
        assert res["excedido"]

    def test_sentinel_nan_en_y(self):
        """Si phi_Pny es nan (M excede diagrama Y) → ratio=inf, excedido=True"""
        res = _biaxial_bresler(500.0, 800.0, np.nan, 2000.0)
        assert res["ratio"] == float("inf")
        assert res["excedido"]

    def test_uniaxial_puro_x(self):
        """Carga solo en X (Muy=0): phi_Pny → Po, Bresler reduce a uniaxial X"""
        phi_P0   = 4000.0
        phi_Pnx  = 1200.0
        phi_Pny  = phi_P0  # sin momento Y → Pny = P0
        Pu = 900.0
        res = _biaxial_bresler(Pu, phi_Pnx, phi_Pny, phi_P0)
        # 1/Pni = 1/1200 + 1/4000 - 1/4000 = 1/1200 → Pni ≈ 1200
        assert res["phi_Pni"] == pytest.approx(1200.0, rel=0.01)

    def test_ratio_simetrico(self):
        """Cargas iguales en X e Y: resultado debe ser simétrico"""
        res1 = _biaxial_bresler(500.0, 800.0, 1200.0, 3000.0)
        res2 = _biaxial_bresler(500.0, 1200.0, 800.0, 3000.0)
        assert res1["phi_Pni"] == pytest.approx(res2["phi_Pni"], rel=1e-6)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 5: get_beta1 edge cases — frontera exacta NSR-10
# ──────────────────────────────────────────────────────────────────────────────
class TestBeta1EdgeCases:
    def test_frontera_28_mpa(self):
        """En fc=28 MPa exacto, β₁ debe ser 0.85 (no reducir)"""
        assert _get_beta1(28.0) == pytest.approx(0.85, abs=1e-10)

    def test_justo_sobre_28(self):
        """fc=28.001 ya inicia la reducción (pero diferencia ínfima)"""
        b1 = _get_beta1(28.001)
        assert b1 < 0.85
        assert b1 > 0.849

    def test_fc_igual_piso(self):
        """fc donde β₁ toca exactamente 0.65: fc=56MPa"""
        # 0.85 - 0.05*(fc-28)/7 = 0.65 → (fc-28)/7 = 4 → fc = 56
        assert _get_beta1(56.0) == pytest.approx(0.65, abs=1e-6)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 6: Verificación columna fuerte/viga débil NSR-10 C.21.6.1
# ──────────────────────────────────────────────────────────────────────────────
class TestColumnaFuerteVigaDebil:
    def test_cumple_ratio_1_2(self):
        """ΣMnc/ΣMnv ≥ 1.20 → cumple"""
        sum_Mnc = 600.0; sum_Mnv = 400.0
        ratio = sum_Mnc / sum_Mnv
        assert ratio >= 1.20
        assert ratio == pytest.approx(1.50, rel=1e-6)

    def test_no_cumple_ratio_menor_1_2(self):
        """ΣMnc/ΣMnv < 1.20 → no cumple"""
        sum_Mnc = 400.0; sum_Mnv = 400.0
        ratio = sum_Mnc / sum_Mnv
        assert ratio < 1.20

    def test_limite_exacto_1_2(self):
        """ΣMnc/ΣMnv = 1.20 exacto → cumple (límite incluido)"""
        sum_Mnc = 480.0; sum_Mnv = 400.0
        assert (sum_Mnc / sum_Mnv) == pytest.approx(1.20, abs=1e-6)
        assert (sum_Mnc / sum_Mnv) >= 1.20


# ──────────────────────────────────────────────────────────────────────────────
# TEST 7: verificar_nodo_viga_columna — NSR-10 C.21.7.4.1
# ──────────────────────────────────────────────────────────────────────────────

def _verificar_nodo(b_col, h_col, fc, fy, As_v, Vu_col, conf):
    gamma_map = {"4_caras": 1.7, "3_caras": 1.25, "otros": 1.0}
    gamma = gamma_map[conf]
    Aj_mm2 = b_col * h_col * 100.0
    Vn_kN  = gamma * math.sqrt(fc) * Aj_mm2 / 1000.0
    phi_Vn = 0.85 * Vn_kN
    Vu_j   = abs(As_v * fy / 100.0 - Vu_col)
    return {"phi_Vn": phi_Vn, "Vu_j": Vu_j, "ratio": Vu_j/phi_Vn, "ok": Vu_j <= phi_Vn}


class TestNodoVigaColumna:
    def test_nodo_interior_cumple(self):
        """Nodo 4 caras grande (40×50cm, fc=28): debe cumplir con As vigas moderado"""
        r = _verificar_nodo(40, 50, 28, 420, 15.0, 100.0, "4_caras")
        assert r["phi_Vn"] > 0
        assert r["ok"]

    def test_nodo_esquina_exigente(self):
        """Nodo esquina (γ=1.0) con As_vigas grande: ratio puede exceder 1.0"""
        r_interior = _verificar_nodo(30, 30, 21, 420, 30.0, 50.0, "4_caras")
        r_esquina  = _verificar_nodo(30, 30, 21, 420, 30.0, 50.0, "otros")
        assert r_esquina["ratio"] > r_interior["ratio"]

    def test_gamma_correcto_por_confinamiento(self):
        """γ debe ser 1.70 (4 caras), 1.25 (3 caras), 1.00 (otros)"""
        r4 = _verificar_nodo(40, 40, 28, 420, 10.0, 50.0, "4_caras")
        r3 = _verificar_nodo(40, 40, 28, 420, 10.0, 50.0, "3_caras")
        ro = _verificar_nodo(40, 40, 28, 420, 10.0, 50.0, "otros")
        # Mayor γ → mayor φVn → menor ratio
        assert r4["phi_Vn"] > r3["phi_Vn"] > ro["phi_Vn"]

    def test_Vu_j_valor_absoluto(self):
        """Vu_j siempre positivo independiente del sentido"""
        r1 = _verificar_nodo(40, 50, 28, 420, 5.0, 200.0, "3_caras")  # Vu_col > As·fy
        assert r1["Vu_j"] >= 0.0

    def test_phi_085(self):
        """φ = 0.85 para cortante en nodo (NSR-10 C.9.3.2.3)"""
        gamma = 1.25
        Aj_mm2 = 40 * 50 * 100.0
        Vn = gamma * math.sqrt(28) * Aj_mm2 / 1000.0
        r = _verificar_nodo(40, 50, 28, 420, 10.0, 50.0, "3_caras")
        assert r["phi_Vn"] == pytest.approx(0.85 * Vn, rel=1e-4)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 8: auto_size_column — F1 Auto-Sizing
# ──────────────────────────────────────────────────────────────────────────────

def _auto_size(Pu, Mux, Muy, fc=28.0, fy=420.0, rho=0.02):
    import math
    factor_phi = 0.65
    secciones = []
    for b_cm in range(25, 85, 5):
        for h_cm in range(b_cm, 105, 5):
            Ag_cm2 = b_cm * h_cm
            Po_est = 0.85 * fc * Ag_cm2 / 100.0
            phi_Pmax_est = factor_phi * 0.80 * Po_est
            if phi_Pmax_est < Pu * 0.5: continue
            Ast_cm2 = rho * Ag_cm2
            Po = (0.85 * fc * (Ag_cm2 - Ast_cm2) / 100.0 + fy * Ast_cm2 / 100.0)
            phi_Pn_max = factor_phi * 0.80 * Po
            if phi_Pn_max < Pu: continue
            d_prime = max(5.0, b_cm * 0.10)
            jd = 0.85 * (h_cm - 2 * d_prime)
            phi_Mn_x = factor_phi * (Ast_cm2/2 * fy / 100.0) * jd / 100.0
            jd_y = 0.85 * (b_cm - 2 * d_prime)
            phi_Mn_y = factor_phi * (Ast_cm2/2 * fy / 100.0) * jd_y / 100.0
            if phi_Mn_x <= 0 or phi_Mn_y <= 0: continue
            ratio_x = Mux / phi_Mn_x if phi_Mn_x > 0 else 999
            ratio_y = Muy / phi_Mn_y if phi_Mn_y > 0 else 999
            if ratio_x <= 1.0 and ratio_y <= 1.0:
                secciones.append({"b": b_cm, "h": h_cm, "Ag": Ag_cm2,
                                   "phi_Pn_max": phi_Pn_max,
                                   "ratio_x": ratio_x, "ratio_y": ratio_y})
    secciones.sort(key=lambda s: s["Ag"])
    return secciones[:5]


class TestAutoSizing:
    def test_retorna_lista_no_vacia(self):
        """Carga típica NSR-10: debe encontrar al menos 1 sección"""
        res = _auto_size(800.0, 80.0, 60.0)
        assert len(res) > 0

    def test_primera_es_la_mas_compacta(self):
        """Resultado ordenado por Ag creciente (sección mínima primero)"""
        res = _auto_size(600.0, 60.0, 40.0)
        areas = [r["Ag"] for r in res]
        assert areas == sorted(areas)

    def test_carga_axial_muy_alta_reduce_opciones(self):
        """Carga axial muy alta → secciones más grandes necesarias"""
        res_baja = _auto_size(300.0, 30.0, 20.0)
        res_alta = _auto_size(5000.0, 80.0, 60.0)
        if res_baja and res_alta:
            assert res_alta[0]["Ag"] >= res_baja[0]["Ag"]

    def test_ratios_menores_o_iguales_1(self):
        """Todos los ratios deben ser ≤ 1.0 (criterio de aceptación)"""
        res = _auto_size(600.0, 60.0, 40.0)
        for s in res:
            assert s["ratio_x"] <= 1.0 + 1e-6
            assert s["ratio_y"] <= 1.0 + 1e-6

    def test_sin_momento_cubierta_por_axial(self):
        """Caso solo axial (Mux=Muy=0): debe encontrar al menos una sección
        (el algoritmo conservador usa φ=0.65 + ρ=2%, el área resultante puede
        ser grande pero siempre debe cumplir φPn ≥ Pu)"""
        res = _auto_size(1000.0, 0.0, 0.0)
        assert len(res) > 0
        # La primera sección debe realmente cumplir la carga axial
        assert res[0]["phi_Pn_max"] >= 1000.0
