# Hallazgos — API CPNU (Consulta de Procesos, Rama Judicial)

Resultado de las pruebas de exploración (julio 2026). Objetivo: evaluar si podemos
cruzar las búsquedas del sistema LAFT contra los procesos judiciales.

## Contrato de la API (descubierto empíricamente)

- **Host/puerto:** `https://consultaprocesos.ramajudicial.gov.co:448` — ⚠️ **puerto 448**, no el 443.
- **Sin autenticación** (no requiere token ni API key).
- **Sin documentación oficial** — es la API interna que consume la SPA del portal.

### Endpoints verificados

| Endpoint | Método | Devuelve |
|---|---|---|
| `/api/v2/Procesos/Consulta/NombreRazonSocial?nombre=&tipoPersona=nat\|jur&SoloActivos=&pagina=` | GET | Lista de procesos (paginada, 20/pág) |
| `/api/v2/Procesos/Consulta/NumeroRadicacion?numero=&SoloActivos=&pagina=` | GET | Proceso(s) por radicado |
| `/api/v2/Proceso/Detalle/{idProceso}` | GET | Metadatos del proceso |
| `/api/v2/Proceso/Actuaciones/{idProceso}?pagina=` | GET | Línea de tiempo de actuaciones (40/pág) |

### Campos disponibles

**Búsqueda (por proceso):** `idProceso`, `llaveProceso` (radicado 23 díg.), `fechaProceso`,
`despacho`, `sujetosProcesales` (texto libre: "Demandante: … | Demandado: …").

**Detalle:** `ponente`, `tipoProceso`, `claseProceso` (ej. "ACCIONES DE TUTELA"),
`subclaseProceso`, `recurso`, `ubicacion` (ej. "Archivo"), `esPrivado`, `ultimaActualizacion`.

**Actuaciones:** `fechaActuacion`, `actuacion` (tipo), `anotacion` (nota), `conDocumentos`.

## Limitaciones críticas para LAFT

1. **🔴 NO hay número de cédula/documento en NINGUNA respuesta.** Ni en la búsqueda, ni en
   el detalle. La búsqueda es **solo por nombre** → imposible confirmar por cédula que un
   proceso es de *nuestra* persona.
2. **🟡 Homónimos (riesgo, no ruido garantizado).** La búsqueda por nombre matchea el nombre
   dentro de `sujetosProcesales`, en CUALQUIER rol (demandante o demandado). Verificado con
   "Humberto Domínguez Moran": los 32 resultados SÍ eran de esa persona (aparece en todas las
   filas, como demandante o dentro del demandado). Es decir, para un nombre completo y
   específico el match es correcto. El riesgo de homónimos aparece con **nombres comunes**
   (varias personas con el mismo nombre) y, al no haber cédula, no se pueden separar
   automáticamente → en esos casos requiere revisión humana.
3. **🟡 Mezcla todo tipo de proceso.** Tutelas, administrativo, civil, laboral, penal… La
   mayoría (tutelas, etc.) **no son señal de riesgo LAFT**. Habría que filtrar por
   `claseProceso` para quedarnos con lo relevante (penal, etc.).
4. **🟡 Bloqueo por IP de datacenter.** Desde IP de nube/AWS responde **406** (WAF). Desde IP
   residencial (PC del usuario) responde 200. → El servidor EC2 de producción probablemente
   **sea bloqueado**; se necesitaría proxy residencial/colombiano o correr desde otra red.
5. **🟡 API no oficial / términos de uso.** Sin SLA, puede cambiar sin aviso; no se permiten
   consultas masivas. Válido solo para consulta individual y bajo volumen.

## Diferencia frente a las listas LAFT actuales

| | Listas LAFT (ConsultaListasPeps) | Rama Judicial (CPNU) |
|---|---|---|
| Criterio de búsqueda | **Cédula** (match exacto) | **Nombre** (match amplio) |
| Devuelve documento | Sí | **No** |
| Precisión | Alta | Baja (homónimos) |
| Naturaleza | Señal de riesgo directa | Apoyo investigativo (verificar a mano) |

## Conclusión

**Técnicamente viable** como consulta **complementaria, individual y opcional**, presentada
como "posibles procesos judiciales (informativo, requiere verificación)". **No** sirve para
cargas masivas ni como match automático de riesgo. El mayor obstáculo operativo es el
**bloqueo por IP en el servidor** y la **imposibilidad de desambiguar por cédula**.
