"""
app/core/constantes.py

Constantes de ingeniería utilizadas por el motor de cálculo.
Se mantienen centralizadas en un único módulo para facilitar su
ajuste y su verificación en los casos de prueba (RNF-06).

Valores de referencia definidos en el punto 1.3 del informe
(Investigación de conceptos y parámetros GPON).
"""

# ------------------------------------------------------------------
# Pérdidas fijas por elemento pasivo
# ------------------------------------------------------------------
PERDIDA_CONECTOR_DB = 0.4       # dB por conector (SC/APC, LC/APC)
PERDIDA_EMPALME_DB = 0.1        # dB por empalme de fusión

# ------------------------------------------------------------------
# Atenuación de fibra por defecto (ITU-T G.652, ventana 1490/1550 nm)
# ------------------------------------------------------------------
ATENUACION_FIBRA_DEFAULT_DB_KM = 0.28

# ------------------------------------------------------------------
# Pérdida de inserción por relación de división del splitter
# (valores reales típicos, incluyen excess loss - ITU-T G.671)
# ------------------------------------------------------------------
PERDIDAS_SPLITTER_DB = {
    "1:2": 3.5,
    "1:4": 7.0,
    "1:8": 10.5,
    "1:16": 14.0,
    "1:32": 17.5,
    "1:64": 21.0,
}

# ------------------------------------------------------------------
# Parámetros de tráfico (GPON estándar, ITU-T G.984)
# ------------------------------------------------------------------
CAPACIDAD_DOWNSTREAM_MBPS = 2488.0   # 2.488 Gbps compartidos por puerto PON

# Consumo promedio orientativo por perfil de usuario (Mbps)
CONSUMO_PROMEDIO_MBPS = {
    "web": 1.5,
    "streaming": 15.0,
    "videoconferencia": 3.0,
    "descarga": 50.0,
}

# Umbral de utilización a partir del cual se considera congestión
UMBRAL_CONGESTION_PCT = 85.0

# ------------------------------------------------------------------
# Modelo simplificado de tiempo de respuesta (RF-17)
# ------------------------------------------------------------------
# Latencia base del enlace GPON en condiciones normales (sin cola de
# espera), valor de referencia típico para redes PON.
LATENCIA_BASE_MS = 5.0

# Tope de utilización usado en el cálculo, para evitar división por
# cero cuando la demanda satura por completo la capacidad (100%).
# Modelo inspirado en la fórmula de espera M/M/1 (tiempo ∝ 1/(1-ρ)):
# a mayor utilización, la latencia crece de forma no lineal, reflejando
# de manera simplificada el efecto de la congestión.
UTILIZACION_MAX_PARA_CALCULO = 0.99