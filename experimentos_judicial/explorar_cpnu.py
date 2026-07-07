#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
explorar_cpnu.py — Script de EXPLORACIÓN (standalone, sin Django, sin base de datos)

Objetivo: descubrir empíricamente el contrato de la API interna de la
Consulta de Procesos Nacional Unificada (CPNU) de la Rama Judicial de Colombia,
para evaluar la viabilidad de integrarla a nuestro sistema de consultas LAFT.

IMPORTANTE (léelo antes de correr):
  1. La API NO es oficial ni documentada. Estos endpoints se infieren del portal
     web (SPA). Pueden cambiar sin aviso.
  2. El portal tiene protección anti-bot (WAF). Desde IPs de datacenter/nube
     responde 406. Corre esto desde tu máquina/servidor (IP residencial o del
     cliente), NO desde el entorno de desarrollo remoto.
  3. Uso RESPONSABLE y de BAJO VOLUMEN. Nada de bucles masivos: la Rama bloquea
     y, además, sus términos no permiten consultas automatizadas masivas.
     Este script es SOLO para entender qué devuelve, no para producción tal cual.
  4. Requiere: pip install requests

Uso:
    python explorar_cpnu.py "PEREZ GOMEZ JUAN"          # por nombre (persona natural)
    python explorar_cpnu.py --radicacion 11001310300120200012300
"""

import sys
import json
import argparse
import requests

# OJO: el API vive en el puerto :448 (no el 443 de la web). Requiere salida a ese puerto.
BASE = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2"

# Headers imitando al navegador que usa el portal (clave para pasar el WAF/406)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-CO,es;q=0.9",
    "Origin": "https://consultaprocesos.ramajudicial.gov.co",
    "Referer": "https://consultaprocesos.ramajudicial.gov.co/procesos/nombrerazonsocial",
    "Connection": "keep-alive",
}

TIMEOUT = 25


def _get(url, params=None):
    """GET con manejo de errores; imprime diagnóstico y devuelve dict/None."""
    print(f"\n>>> GET {url}")
    if params:
        print(f"    params = {params}")
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        print(f"    [ERROR de conexión] {e}")
        return None

    ctype = r.headers.get("Content-Type", "")
    print(f"    HTTP {r.status_code} | Content-Type: {ctype}")

    if r.status_code != 200:
        # 406 = WAF/anti-bot (IP bloqueada o headers insuficientes)
        print(f"    [!] Respuesta no-200. Primeros 300 chars:\n    {r.text[:300]}")
        return None

    if "json" not in ctype.lower():
        print(f"    [!] No es JSON. Primeros 300 chars:\n    {r.text[:300]}")
        return None

    return r.json()


def buscar_por_nombre(nombre, tipo_persona="nat", solo_activos=False):
    """
    Busca procesos por nombre o razón social.
    tipo_persona: 'nat' (natural) | 'jur' (jurídica)
    solo_activos: True = solo procesos activos; False = incluye históricos
    Devuelve la lista de procesos (o []).
    """
    data = _get(
        f"{BASE}/Procesos/Consulta/NombreRazonSocial",
        params={
            "nombre": nombre,
            "tipoPersona": tipo_persona,
            "SoloActivos": "true" if solo_activos else "false",
            "codificacionDespacho": "",
            "pagina": 1,
        },
    )
    if not data:
        return []
    procesos = data.get("procesos", [])
    print(f"    -> {data.get('paginacion', {}).get('cantidadRegistros', len(procesos))} registro(s) reportado(s), "
          f"{len(procesos)} en esta página")
    return procesos


def buscar_por_radicacion(numero):
    """Busca un proceso por número de radicación (23 dígitos)."""
    data = _get(
        f"{BASE}/Procesos/Consulta/NumeroRadicacion",
        params={"numero": numero, "SoloActivos": "false", "pagina": 1},
    )
    return data.get("procesos", []) if data else []


def detalle_proceso(id_proceso):
    """Trae el detalle (sujetos procesales, despacho, etc.) de un proceso."""
    return _get(f"{BASE}/Proceso/Detalle/{id_proceso}")


def actuaciones_proceso(id_proceso):
    """Trae las actuaciones (movimientos) de un proceso."""
    return _get(f"{BASE}/Proceso/Actuaciones/{id_proceso}", params={"pagina": 1})


def _resumen_proceso(p):
    """Imprime un resumen legible de un proceso de la lista."""
    print(
        "      · idProceso={idProceso} | radicado={llaveProceso} | "
        "fecha={fechaProceso} | despacho={despacho}".format(
            idProceso=p.get("idProceso"),
            llaveProceso=p.get("llaveProceso"),
            fechaProceso=p.get("fechaProceso"),
            despacho=(p.get("despacho") or "")[:40],
        )
    )
    if p.get("sujetosProcesales"):
        # Mostramos el campo COMPLETO: el nombre buscado puede estar como
        # demandante O como demandado, así que truncarlo oculta coincidencias reales.
        print(f"        sujetos: {p['sujetosProcesales']}")


def main():
    ap = argparse.ArgumentParser(description="Exploración API CPNU (Rama Judicial)")
    ap.add_argument("nombre", nargs="?", help="Nombre o razón social a buscar")
    ap.add_argument("--tipo", default="nat", choices=["nat", "jur"],
                    help="Tipo de persona: nat (natural) | jur (jurídica)")
    ap.add_argument("--solo-activos", action="store_true",
                    help="Solo procesos activos (por defecto incluye históricos)")
    ap.add_argument("--radicacion", help="Buscar por número de radicación en vez de nombre")
    ap.add_argument("--detalle", help="Traer el detalle de un idProceso")
    ap.add_argument("--actuaciones", help="Traer actuaciones de un idProceso")
    args = ap.parse_args()

    if args.detalle:
        print(json.dumps(detalle_proceso(args.detalle), indent=2, ensure_ascii=False))
        return
    if args.actuaciones:
        print(json.dumps(actuaciones_proceso(args.actuaciones), indent=2, ensure_ascii=False))
        return
    if args.radicacion:
        procesos = buscar_por_radicacion(args.radicacion)
    elif args.nombre:
        procesos = buscar_por_nombre(args.nombre, args.tipo, args.solo_activos)
    else:
        ap.print_help()
        sys.exit(1)

    print(f"\n=== {len(procesos)} proceso(s) en la primera página ===")
    for p in procesos[:10]:
        _resumen_proceso(p)

    if procesos:
        print("\nTip: usa --detalle <idProceso> o --actuaciones <idProceso> "
              "para profundizar en uno.")
        print("Ejemplo idProceso:", procesos[0].get("idProceso"))


if __name__ == "__main__":
    main()
