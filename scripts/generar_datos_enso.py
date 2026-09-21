#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera `website/data/enso.json`, la fuente del Observatorio ENSO de la home.

Entrada: la tabla ONI de la NOAA ("Data T sea surface.xlsx", hoja Sheet1) con
columnas SEAS / YR / TOTAL / ANOM, una fila por temporada trimestral solapada.

Qué hace:
  1. Lee la serie de anomalías (ONI) y le asigna el mes central de cada temporada.
  2. Detecta episodios El Nino / La Nina con la definicion operativa de la NOAA
     (>= 5 temporadas solapadas consecutivas con |ONI| >= 0.5) y los clasifica
     por intensidad segun el pico.
  3. Extrae caracteristicas por ventana deslizante (tiempo, Welch, STFT), las
     etiqueta y corre Kruskal-Wallis + correccion FDR de Benjamini-Hochberg.
  4. Calcula la matriz de correlacion de las variables significativas y el PCA.
  5. Evalua capacidad predictiva real: regresion logistica multinomial entrenada
     solo con el pasado y evaluada sobre el futuro, para varios horizontes.

Por que existe este script y no un management command: necesita numpy/scipy/
pandas/openpyxl, que no estan en requirements.txt del sitio. El JSON resultante
se versiona y la web solo lo lee.

Uso:
    python3 scripts/generar_datos_enso.py \
        --input "/ruta/Data T sea surface.xlsx" \
        --output website/data/enso.json
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal, stats
from scipy.integrate import trapezoid

# Umbral operativo de la NOAA y racha minima que define un episodio.
THR = 0.5
NEED_RUN = 5
WIN = 36          # meses por ventana
STEP = 1
FS = 12.0         # muestras por anio
ALPHA = 0.05      # nivel FDR
R_COLINEAL = 0.90

# Mes central de cada temporada trimestral solapada de la NOAA.
SEASON_CENTER = {
    'DJF': 1, 'JFM': 2, 'FMA': 3, 'MAM': 4, 'AMJ': 5, 'MJJ': 6,
    'JJA': 7, 'JAS': 8, 'ASO': 9, 'SON': 10, 'OND': 11, 'NDJ': 12,
}
MES_ES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
          'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

# Etiquetas legibles de cada caracteristica, para que el tablero no muestre
# nombres crudos de variable.
FEATURE_LABELS = {
    'mean': 'Media', 'median': 'Mediana', 'std': 'Desviación estándar',
    'var': 'Varianza', 'rms': 'Valor eficaz (RMS)', 'skew': 'Asimetría',
    'kurt': 'Curtosis', 'iqr': 'Rango intercuartílico', 'p2_5': 'Percentil 2,5',
    'p25': 'Percentil 25', 'p75': 'Percentil 75', 'p97_5': 'Percentil 97,5',
    'ptp': 'Rango total', 'zcr': 'Cruces por cero', 'energy': 'Energía',
    'hjorth_activity': 'Hjorth: actividad', 'hjorth_mobility': 'Hjorth: movilidad',
    'hjorth_complexity': 'Hjorth: complejidad',
    'spec_centroid': 'Centroide espectral', 'spec_bandwidth': 'Ancho de banda espectral',
    'spec_entropy': 'Entropía espectral', 'spec_rolloff85': 'Roll-off espectral 85 %',
    'spec_total_power': 'Potencia espectral total',
    'bp_0': 'Potencia banda ENSO (2-7 años)', 'bp_0_rel': 'Potencia relativa banda ENSO',
    'bp_1': 'Potencia banda anual', 'bp_1_rel': 'Potencia relativa banda anual',
    'bp_2': 'Potencia banda intraanual', 'bp_2_rel': 'Potencia relativa banda intraanual',
    'tf_mean_power': 'STFT: potencia media', 'tf_var_power': 'STFT: varianza de potencia',
    'tf_entropy': 'STFT: entropía', 'tf_flux': 'STFT: flujo espectral',
}
FEATURE_FAMILY = {
    **{k: 'tiempo' for k in ('mean', 'median', 'std', 'var', 'rms', 'skew', 'kurt',
                             'iqr', 'p2_5', 'p25', 'p75', 'p97_5', 'ptp', 'zcr', 'energy',
                             'hjorth_activity', 'hjorth_mobility', 'hjorth_complexity')},
    **{k: 'frecuencia' for k in ('spec_centroid', 'spec_bandwidth', 'spec_entropy',
                                 'spec_rolloff85', 'spec_total_power', 'bp_0', 'bp_0_rel',
                                 'bp_1', 'bp_1_rel', 'bp_2', 'bp_2_rel')},
    **{k: 'tiempo-frecuencia' for k in ('tf_mean_power', 'tf_var_power', 'tf_entropy', 'tf_flux')},
}


# --------------------------------------------------------------------------
# 1. Lectura de la serie
# --------------------------------------------------------------------------

def leer_serie(path: Path) -> pd.DataFrame:
    """Lee la tabla ONI y devuelve un DataFrame ordenado con fecha central."""
    df = pd.read_excel(path, header=1)
    df = df[['SEAS', 'YR', 'TOTAL', 'ANOM']].dropna(subset=['SEAS', 'YR', 'ANOM'])
    df['SEAS'] = df['SEAS'].astype(str).str.strip().str.upper()
    df = df[df['SEAS'].isin(SEASON_CENTER)].copy()
    df['YR'] = df['YR'].astype(int)
    df['mes'] = df['SEAS'].map(SEASON_CENTER)
    # NDJ y DJF cruzan de anio: la NOAA rotula la temporada con el anio del mes central.
    df['fecha'] = [date(y, m, 1) for y, m in zip(df['YR'], df['mes'])]
    df = df.sort_values('fecha').reset_index(drop=True)
    df['anom'] = df['ANOM'].astype(float)
    df['sst'] = df['TOTAL'].astype(float)
    return df


def fase(v: float) -> str:
    if v >= THR:
        return 'nino'
    if v <= -THR:
        return 'nina'
    return 'neutral'


# --------------------------------------------------------------------------
# 2. Episodios segun la definicion operativa de la NOAA
# --------------------------------------------------------------------------

def intensidad(pico: float) -> str:
    p = abs(pico)
    if p >= 2.0:
        return 'Muy fuerte'
    if p >= 1.5:
        return 'Fuerte'
    if p >= 1.0:
        return 'Moderado'
    return 'Débil'


def detectar_episodios(df: pd.DataFrame) -> list[dict]:
    """Rachas de >= NEED_RUN temporadas solapadas consecutivas sobre el umbral."""
    episodios = []
    for tipo, signo in (('nino', 1), ('nina', -1)):
        cond = (df['anom'] * signo >= THR).to_numpy()
        i = 0
        while i < len(cond):
            if not cond[i]:
                i += 1
                continue
            j = i
            while j < len(cond) and cond[j]:
                j += 1
            if j - i >= NEED_RUN:
                tramo = df.iloc[i:j]
                pico_idx = (tramo['anom'] * signo).idxmax()
                pico = float(df.loc[pico_idx, 'anom'])
                episodios.append({
                    'tipo': tipo,
                    'inicio': tramo.iloc[0]['fecha'].isoformat(),
                    'fin': tramo.iloc[-1]['fecha'].isoformat(),
                    'inicio_seas': f"{tramo.iloc[0]['SEAS']} {tramo.iloc[0]['YR']}",
                    'fin_seas': f"{tramo.iloc[-1]['SEAS']} {tramo.iloc[-1]['YR']}",
                    'duracion': int(j - i),
                    'pico': round(pico, 2),
                    'pico_fecha': df.loc[pico_idx, 'fecha'].isoformat(),
                    'intensidad': intensidad(pico),
                })
            i = j
    episodios.sort(key=lambda e: e['inicio'])
    return episodios


# --------------------------------------------------------------------------
# 3. Caracteristicas por ventana
# --------------------------------------------------------------------------

def hjorth(x: np.ndarray) -> tuple[float, float, float]:
    dx = np.diff(x, prepend=x[0])
    ddx = np.diff(dx, prepend=dx[0])
    v0, v1, v2 = np.var(x), np.var(dx), np.var(ddx)
    mob = math.sqrt(v1 / v0) if v0 > 0 else 0.0
    cpx = math.sqrt(v2 / v1) / mob if (v1 > 0 and mob > 0) else 0.0
    return float(v0), float(mob), float(cpx)


def features_tiempo(x: np.ndarray) -> dict:
    a, m, c = hjorth(x)
    return {
        'mean': float(np.mean(x)), 'median': float(np.median(x)),
        'std': float(np.std(x)), 'var': float(np.var(x)),
        'rms': float(np.sqrt(np.mean(x ** 2))),
        'skew': float(stats.skew(x, bias=False)),
        'kurt': float(stats.kurtosis(x, bias=False)),
        'iqr': float(stats.iqr(x)),
        'p2_5': float(np.percentile(x, 2.5)), 'p25': float(np.percentile(x, 25)),
        'p75': float(np.percentile(x, 75)), 'p97_5': float(np.percentile(x, 97.5)),
        'ptp': float(np.ptp(x)),
        'zcr': float(((x[:-1] * x[1:]) < 0).mean()) if len(x) > 1 else 0.0,
        'energy': float(np.sum(x ** 2)),
        'hjorth_activity': a, 'hjorth_mobility': m, 'hjorth_complexity': c,
    }


def features_welch(x: np.ndarray) -> dict:
    # Bandas en ciclos/anio: ENSO (2-7 anios), anual, intraanual.
    bands = [(0.143, 0.5), (0.8, 1.2), (1.2, 4.0)]
    nper = min(max(16, len(x) // 4), len(x))
    f, Pxx = signal.welch(x, fs=FS, nperseg=nper)
    Pxx = np.maximum(Pxx, 1e-20)
    psum = float(np.sum(Pxx))
    centroid = float(np.sum(f * Pxx) / psum)
    out = {
        'spec_centroid': centroid,
        'spec_bandwidth': float(np.sqrt(np.sum(((f - centroid) ** 2) * Pxx) / psum)),
        'spec_entropy': float(-np.sum((Pxx / psum) * np.log(Pxx / psum))),
        'spec_rolloff85': float(f[min(int(np.searchsorted(np.cumsum(Pxx) / psum, 0.85)), len(f) - 1)]),
        'spec_total_power': psum,
    }
    for i, (lo, hi) in enumerate(bands):
        idx = (f >= lo) & (f < hi)
        bp = float(trapezoid(Pxx[idx], f[idx])) if np.any(idx) else 0.0
        out[f'bp_{i}'] = bp
        out[f'bp_{i}_rel'] = bp / psum if psum > 0 else 0.0
    return out


def features_stft(x: np.ndarray) -> dict:
    nper = 48 if len(x) >= 48 else max(16, len(x) // 2)
    _, _, Z = signal.stft(x, fs=FS, nperseg=nper)
    S = np.abs(Z) ** 2
    tot = float(S.sum())
    if not np.isfinite(tot) or tot <= 0:
        return {k: float('nan') for k in ('tf_mean_power', 'tf_var_power', 'tf_entropy', 'tf_flux')}
    Pn = S / tot
    return {
        'tf_mean_power': float(S.mean()), 'tf_var_power': float(S.var()),
        'tf_entropy': float(-np.nansum(Pn * np.log(Pn + 1e-20))),
        'tf_flux': float(np.sqrt(((np.diff(S, axis=1)) ** 2).sum(axis=0)).mean()) if S.shape[1] > 1 else 0.0,
    }


def etiqueta_ventana(x: np.ndarray) -> str:
    """Fase en el mes final de la ventana.

    El pipeline original etiquetaba la ventana completa con la regla de racha de
    la NOAA. Sobre ventanas de 36 meses eso degenera: casi cualquier tramo de
    tres anios contiene al menos cinco meses seguidos por encima de +0,5, asi
    que el 79 % de las ventanas caia en la clase Nino y La Nina casi desaparecia.
    Etiquetar por el estado al cierre de la ventana da tres clases equilibradas,
    es directamente interpretable ("que fase hay al final de estos 36 meses") y
    encadena con el panel de pronostico, donde el horizonte 0 es justo este caso.
    """
    return {'nino': 'Nino', 'nina': 'Nina', 'neutral': 'Neutral'}[fase(float(x[-1]))]


def construir_features(serie: np.ndarray, fechas: list) -> pd.DataFrame:
    filas, meta = [], []
    for i in range(0, len(serie) - WIN + 1, STEP):
        x = serie[i:i + WIN]
        filas.append({**features_tiempo(x), **features_welch(x), **features_stft(x)})
        meta.append({'inicio': fechas[i], 'fin': fechas[i + WIN - 1], 'label': etiqueta_ventana(x)})
    F = pd.DataFrame(filas)
    M = pd.DataFrame(meta)
    F['label'] = M['label']
    F['fin'] = M['fin']
    return F


# --------------------------------------------------------------------------
# 4. Kruskal-Wallis + FDR, correlacion y PCA
# --------------------------------------------------------------------------

def bh_fdr(p: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """Benjamini-Hochberg. Devuelve (q-values, rechazos)."""
    m = len(p)
    orden = np.argsort(p)
    q_ord = np.minimum.accumulate((np.array(p)[orden] * m / (np.arange(m) + 1))[::-1])[::-1]
    q = np.empty(m)
    q[orden] = np.clip(q_ord, 0, 1)
    return q, q <= alpha


def kruskal_fdr(F: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    cols = [c for c in F.columns if c not in ('label', 'fin')]
    valid = F[cols].replace([np.inf, -np.inf], np.nan)
    cols = [c for c in cols if valid[c].notna().all() and valid[c].nunique() > 1]
    clases = pd.unique(labels)
    H, p = [], []
    for c in cols:
        grupos = [valid.loc[labels == cl, c].to_numpy() for cl in clases]
        grupos = [g for g in grupos if len(g) > 0]
        try:
            h, pv = stats.kruskal(*grupos)
        except ValueError:
            h, pv = 0.0, 1.0
        H.append(float(h))
        p.append(float(pv))
    q, rej = bh_fdr(np.array(p), ALPHA)
    n = len(valid)
    return pd.DataFrame({
        'feature': cols, 'H': H, 'p': p, 'q': q, 'significativa': rej,
        # Epsilon cuadrado: tamanio de efecto para Kruskal-Wallis.
        'epsilon2': [(h - len(clases) + 1) / (n - len(clases)) for h in H],
    }).sort_values('q', kind='stable').reset_index(drop=True)


def quitar_colineales(F: pd.DataFrame, kw: pd.DataFrame) -> list[str]:
    sig = kw[kw['significativa']]['feature'].tolist()
    if len(sig) <= 1:
        return sig
    # pandas 3 devuelve vistas de solo lectura: se copia a numpy antes de tocarla.
    C = np.array(F[sig].corr().abs().to_numpy(dtype=float), copy=True)
    np.fill_diagonal(C, 0.0)
    eff = dict(zip(kw['feature'], kw['epsilon2']))
    keep = set(sig)
    for i, c1 in enumerate(sig):
        for j in range(i + 1, len(sig)):
            c2 = sig[j]
            if c1 in keep and c2 in keep and C[i, j] >= R_COLINEAL:
                keep.discard(c1 if eff.get(c1, 0) < eff.get(c2, 0) else c2)
    return [c for c in sig if c in keep]


def pca_varianza(F: pd.DataFrame, cols: list[str], n: int = 12) -> dict:
    X = F[cols].to_numpy(dtype=float)
    X = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
    # SVD sobre la matriz centrada equivale a PCA sin depender de sklearn.
    _, S, _ = np.linalg.svd(X, full_matrices=False)
    var = (S ** 2) / (len(X) - 1)
    ratio = var / var.sum()
    k = min(n, len(ratio))
    return {
        'componentes': list(range(1, k + 1)),
        'varianza': [round(float(v) * 100, 2) for v in ratio[:k]],
        'acumulada': [round(float(v) * 100, 2) for v in np.cumsum(ratio)[:k]],
        'n_para_95': int(np.searchsorted(np.cumsum(ratio), 0.95) + 1),
        'n_variables': len(cols),
    }


# --------------------------------------------------------------------------
# 5. Capacidad predictiva honesta (entrenar en el pasado, probar en el futuro)
# --------------------------------------------------------------------------

def softmax(Z):
    Z = Z - Z.max(axis=1, keepdims=True)
    e = np.exp(Z)
    return e / e.sum(axis=1, keepdims=True)


def entrenar_logistica(X, y, n_clases, epocas=600, lr=0.35, l2=1e-3, seed=0):
    """Regresion logistica multinomial por descenso de gradiente (sin sklearn)."""
    rng = np.random.default_rng(seed)
    Xb = np.hstack([X, np.ones((len(X), 1))])
    W = rng.normal(0, 0.01, (Xb.shape[1], n_clases))
    Y = np.eye(n_clases)[y]
    for _ in range(epocas):
        G = Xb.T @ (softmax(Xb @ W) - Y) / len(Xb) + l2 * W
        W -= lr * G
    return W


def predecir(W, X):
    return np.argmax(softmax(np.hstack([X, np.ones((len(X), 1))]) @ W), axis=1)


def evaluar_horizontes(F: pd.DataFrame, cols: list[str], serie: np.ndarray,
                       fechas: list, horizontes=(0, 3, 6, 9, 12)) -> list[dict]:
    """Con la ventana que termina en t, predice la fase en t+h.

    Entrenamiento y prueba se separan cronologicamente (sin mezclar futuro con
    pasado), que es la unica forma honesta de medir capacidad predictiva.
    """
    fases = np.array([fase(v) for v in serie])
    clases = ['nina', 'neutral', 'nino']
    idx_fin = np.arange(WIN - 1, WIN - 1 + len(F))   # indice en la serie del fin de cada ventana
    corte = int(len(F) * 0.70)                        # 70% mas antiguo para entrenar
    salida = []
    for h in horizontes:
        objetivo = idx_fin + h
        ok = objetivo < len(serie)
        X = F.loc[ok, cols].to_numpy(dtype=float)
        y = np.array([clases.index(fases[i]) for i in objetivo[ok]])
        n_tr = min(corte, len(X) - 1)
        Xtr, Xte, ytr, yte = X[:n_tr], X[n_tr:], y[:n_tr], y[n_tr:]
        if len(Xte) == 0 or len(np.unique(ytr)) < 2:
            continue
        mu, sd = Xtr.mean(0), np.where(Xtr.std(0) == 0, 1, Xtr.std(0))
        W = entrenar_logistica((Xtr - mu) / sd, ytr, len(clases))
        pred = predecir(W, (Xte - mu) / sd)
        acierto = float((pred == yte).mean())
        # Linea base: predecir siempre la clase mas frecuente del entrenamiento.
        base = float((yte == np.bincount(ytr, minlength=len(clases)).argmax()).mean())
        f1 = []
        for k in range(len(clases)):
            tp = int(((pred == k) & (yte == k)).sum())
            fp = int(((pred == k) & (yte != k)).sum())
            fn = int(((pred != k) & (yte == k)).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            f1.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
        salida.append({
            'horizonte': h,
            'acierto': round(acierto * 100, 1),
            'base': round(base * 100, 1),
            'f1_macro': round(float(np.mean(f1)) * 100, 1),
            'n_prueba': int(len(yte)),
            'desde': fechas[idx_fin[ok][n_tr]].isoformat(),
        })
    return salida


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', required=True, help='Ruta a "Data T sea surface.xlsx"')
    ap.add_argument('--output', default='website/data/enso.json')
    args = ap.parse_args()

    print('[1/6] Leyendo la serie ONI...')
    df = leer_serie(Path(args.input))
    serie = df['anom'].to_numpy(dtype=float)
    fechas = list(df['fecha'])
    print(f'      {len(serie)} temporadas, de {fechas[0]} a {fechas[-1]}')

    print('[2/6] Detectando episodios...')
    episodios = detectar_episodios(df)
    n_nino = sum(1 for e in episodios if e['tipo'] == 'nino')
    n_nina = len(episodios) - n_nino
    print(f'      {n_nino} episodios El Nino y {n_nina} de La Nina')

    print(f'[3/6] Extrayendo caracteristicas ({WIN} meses por ventana)...')
    F = construir_features(serie, fechas)
    labels = F['label'].to_numpy()
    print(f'      {len(F)} ventanas | clases: {pd.Series(labels).value_counts().to_dict()}')

    print('[4/6] Kruskal-Wallis + FDR...')
    kw = kruskal_fdr(F, labels)
    seleccionadas = quitar_colineales(F, kw)
    print(f'      {int(kw["significativa"].sum())} significativas, '
          f'{len(seleccionadas)} tras filtrar colinealidad')

    print('[5/6] Correlacion y PCA...')
    C = F[seleccionadas].corr()
    pca = pca_varianza(F, [c for c in kw['feature'] if c in F.columns])

    print('[6/6] Capacidad predictiva por horizonte...')
    skill = evaluar_horizontes(F, seleccionadas, serie, fechas)
    for s in skill:
        print(f'      +{s["horizonte"]:>2} meses: {s["acierto"]}% (base {s["base"]}%)')

    ultimo = df.iloc[-1]
    ultimo_ep = episodios[-1] if episodios else None
    pico_nino = max((e for e in episodios if e['tipo'] == 'nino'), key=lambda e: e['pico'])
    pico_nina = min((e for e in episodios if e['tipo'] == 'nina'), key=lambda e: e['pico'])

    data = {
        'meta': {
            'fuente': 'NOAA Climate Prediction Center · Oceanic Niño Index (ONI), región Niño 3.4',
            'generado': date.today().isoformat(),
            'umbral': THR,
            'racha_minima': NEED_RUN,
            'ventana_meses': WIN,
            'n_temporadas': len(serie),
            'desde': fechas[0].isoformat(),
            'hasta': fechas[-1].isoformat(),
        },
        'kpis': {
            'ultimo_oni': round(float(ultimo['anom']), 2),
            'ultimo_periodo': f"{ultimo['SEAS']} {ultimo['YR']}",
            'ultimo_mes': f"{MES_ES[int(ultimo['mes'])]} de {int(ultimo['YR'])}",
            'fase_actual': fase(float(ultimo['anom'])),
            'sst_actual': round(float(ultimo['sst']), 2),
            'episodios_nino': n_nino,
            'episodios_nina': n_nina,
            'meses_nino': sum(e['duracion'] for e in episodios if e['tipo'] == 'nino'),
            'meses_nina': sum(e['duracion'] for e in episodios if e['tipo'] == 'nina'),
            'pct_nino': round(100 * sum(1 for v in serie if v >= THR) / len(serie), 1),
            'pct_nina': round(100 * sum(1 for v in serie if v <= -THR) / len(serie), 1),
            'pct_neutral': round(100 * sum(1 for v in serie if abs(v) < THR) / len(serie), 1),
            'nino_mas_fuerte': pico_nino,
            'nina_mas_fuerte': pico_nina,
            'ultimo_episodio': ultimo_ep,
        },
        'serie': [
            {'f': d.isoformat()[:7], 'v': round(float(a), 2), 't': round(float(s), 2)}
            for d, a, s in zip(fechas, serie, df['sst'])
        ],
        'episodios': episodios,
        'modelo': {
            'ventanas': len(F),
            'clases': {k: int(v) for k, v in pd.Series(labels).value_counts().items()},
            'variables_totales': int(len(kw)),
            'significativas': int(kw['significativa'].sum()),
            'seleccionadas': seleccionadas,
            'ranking': [
                {
                    'feature': r['feature'],
                    'nombre': FEATURE_LABELS.get(r['feature'], r['feature']),
                    'familia': FEATURE_FAMILY.get(r['feature'], 'otra'),
                    'H': round(float(r['H']), 1),
                    'q': float(r['q']),
                    'epsilon2': round(float(r['epsilon2']), 4),
                    'significativa': bool(r['significativa']),
                    'seleccionada': r['feature'] in seleccionadas,
                }
                for _, r in kw.iterrows()
            ],
            'correlacion': {
                'variables': [FEATURE_LABELS.get(c, c) for c in seleccionadas],
                'claves': seleccionadas,
                'matriz': [[round(float(C.loc[a, b]), 3) for b in seleccionadas] for a in seleccionadas],
            },
            'pca': pca,
            'distribuciones': {
                c: {
                    cl: {
                        'min': round(float(np.percentile(F.loc[labels == cl, c], 5)), 4),
                        'q1': round(float(np.percentile(F.loc[labels == cl, c], 25)), 4),
                        'mediana': round(float(np.percentile(F.loc[labels == cl, c], 50)), 4),
                        'q3': round(float(np.percentile(F.loc[labels == cl, c], 75)), 4),
                        'max': round(float(np.percentile(F.loc[labels == cl, c], 95)), 4),
                    }
                    for cl in sorted(set(labels)) if (labels == cl).sum() > 0
                }
                for c in seleccionadas
            },
        },
        'pronostico': {
            'horizontes': skill,
            'nota': ('Evaluación retrospectiva: el modelo se entrena solo con el 70 % más '
                     'antiguo de la serie y se mide sobre los años posteriores, que nunca vio. '
                     'No es un pronóstico operativo.'),
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'\n[OK] {out} ({out.stat().st_size / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
