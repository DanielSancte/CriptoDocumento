# Aplicación de cifrado PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una aplicación de escritorio para Windows que combine PDF, sanee contenido activo, aplique permisos configurables y genere un único PDF cifrado con AES-256 sin modificar los originales ni almacenar contraseñas.

**Architecture:** Una interfaz PySide6 consumirá servicios de dominio independientes para validar entradas, sanear y combinar páginas, cifrar/publicar la salida de forma transaccional y verificar el resultado. La lógica PDF permanecerá fuera de los widgets para poder probarla con archivos temporales; el procesamiento se ejecutará en un trabajador para no bloquear la ventana.

**Tech Stack:** Python 3.12, PySide6, pikepdf/qpdf, pytest, pytest-qt, PyInstaller y GitHub Actions para una compilación reproducible de Windows.

**Spec:** `docs/superpowers/specs/2026-11-19-aplicacion-cifrado-pdf-design.md`

## Global Constraints

- Plataforma objetivo inicial: Windows 10 22H2 y Windows 11 de 64 bits; el ejecutable no requerirá Python instalado.
- Operación local y sin solicitudes de red iniciadas por la aplicación.
- Cifrado obligatorio: manejador PDF `R=6`, AES-256, metadatos cifrados y contraseña administrativa aleatoria no persistida.
- Los archivos originales deben permanecer idénticos byte a byte.
- Nunca se escribirá al disco una versión combinada sin cifrar.
- No se almacenarán, registrarán ni transmitirán contraseñas.
- Las restricciones son permisos PDF orientativos: impresión completa, extracción de contenido y modificación general.
- Los campos de contraseña se limpiarán después de éxito o error.
- Los temporales se crearán en la carpeta de destino y solo se publicarán tras validar el PDF cifrado.
- La interfaz, documentación y mensajes para el funcionario estarán en español.
- El código debe usar anotaciones de tipo y rutas mediante `pathlib.Path`.
- Las versiones exactas de dependencias se resolverán y fijarán en `requirements.lock` durante Task 1; no se actualizarán durante la implementación salvo incompatibilidad demostrada.

## Review Focus

- PDF con referencias internas, anotaciones o formularios complejos: debe conservar la apariencia de página sin mantener acciones ni contenido activo; Task 3 lo fija con pruebas de saneamiento.
- Contraseña Unicode o demasiado extensa: debe validarse mediante un guardado controlado y rechazarse sin truncamiento ni transformación silenciosa; Task 2 y Task 4 lo prueban.
- Destino existente, sin permisos o en ruta sincronizada/red: no debe sobrescribirse por fallo y debe advertir antes de procesar; Task 4 y Task 6 cubren estos casos.
- Documento grande o cancelación/cierre durante el proceso: la UI debe continuar respondiendo, no publicar una salida parcial y comunicar el límite de memoria; Task 5 y Task 6 lo prueban.
- PDF firmado, cifrado, dañado o que desaparece entre selección y proceso: debe advertir o fallar indicando el archivo, conservando originales y destino; Task 3 y Task 4 lo prueban.

---

## Mapa de archivos

```text
pyproject.toml                         metadatos, dependencias y configuración de pruebas
requirements.lock                     versiones exactas para construcción reproducible
src/pdf_protector/__init__.py         versión del producto
src/pdf_protector/__main__.py         punto de entrada de escritorio
src/pdf_protector/domain.py           tipos, permisos y errores compartidos
src/pdf_protector/passwords.py        validación y generación de credenciales
src/pdf_protector/pdf_service.py      inspección, saneamiento, combinación y cifrado
src/pdf_protector/output_service.py   publicación transaccional y verificación final
src/pdf_protector/worker.py           ejecución cancelable fuera del hilo de UI
src/pdf_protector/main_window.py      ventana, estado visual y diálogos
src/pdf_protector/resources.qrc       recursos Qt
tests/conftest.py                     fábricas de PDF y fixtures comunes
tests/test_passwords.py               pruebas de credenciales
tests/test_pdf_service.py             pruebas de combinación, saneamiento y permisos
tests/test_output_service.py          pruebas de atomicidad, validación y originales
tests/test_worker.py                  pruebas de progreso, error y cancelación
tests/test_main_window.py             pruebas del flujo de interfaz
tests/test_packaged_app.py            smoke test del ejecutable
packaging/pdf-protector.spec          configuración de PyInstaller
scripts/build.ps1                     construcción reproducible en Windows
.github/workflows/windows-build.yml   verificación y artefacto de Windows
README.md                              uso, seguridad, compilación y limitaciones
THIRD_PARTY_LICENSES.md                atribuciones de dependencias distribuidas
```

### Task 1: Base reproducible y tipos de dominio

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.lock`
- Create: `src/pdf_protector/__init__.py`
- Create: `src/pdf_protector/domain.py`
- Create: `tests/test_domain.py`

**Interfaces:**
- Consumes: ninguna.
- Produces: `PdfPermissions(printing: bool, copying: bool, editing: bool)`, `ProtectionRequest(sources: tuple[Path, ...], destination: Path, user_password: str, permissions: PdfPermissions)`, `ProcessingResult(destination: Path, pages: int)`, `SourceInspection(path: Path, pages: int, has_signatures: bool)`, y jerarquía `ProtectionError` con `ValidationError`, `SourcePdfError`, `PasswordCompatibilityError`, `DestinationError`, `CancelledError`.

- [ ] **Step 1: Escribir las pruebas fallidas del dominio**

En `tests/test_domain.py`, probar `PdfPermissions` inmutable, rechazo de `ProtectionRequest` sin fuentes, rutas duplicadas o contraseña vacía, y conservación del orden de `sources`.

- [ ] **Step 2: Ejecutar la prueba y confirmar el fallo**

Run: `python -m pytest tests/test_domain.py -v`  
Expected: FAIL por ausencia de `pdf_protector.domain`.

- [ ] **Step 3: Crear proyecto y tipos mínimos**

Configurar paquete `src`, Python `>=3.12,<3.13`, dependencias de ejecución PySide6 y pikepdf, y dependencias de desarrollo pytest, pytest-qt y PyInstaller. Implementar los dataclasses y errores exactamente con las firmas del bloque Interfaces; la contraseña se excluye de `repr` mediante `field(repr=False)`.

- [ ] **Step 4: Resolver versiones y ejecutar pruebas**

Generar `requirements.lock` desde un entorno limpio y ejecutar `python -m pytest tests/test_domain.py -v`.  
Expected: PASS y el texto de `repr(ProtectionRequest)` no contiene la contraseña.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.lock src/pdf_protector tests/test_domain.py
git commit -m "chore: initialize PDF protector domain"
```

### Task 2: Contraseñas seguras y compatibles

**Files:**
- Create: `src/pdf_protector/passwords.py`
- Create: `tests/test_passwords.py`

**Interfaces:**
- Consumes: `PasswordCompatibilityError` de Task 1.
- Produces: `generate_owner_password() -> str`, `validate_password_pair(password: str, confirmation: str) -> None`, `validate_pdf_password(password: str) -> None`.

- [ ] **Step 1: Escribir pruebas fallidas de credenciales**

Probar que la clave administrativa tiene al menos 256 bits de entropía usando `secrets`, que dos llamadas difieren, que vacío y confirmación diferente fallan, que espacios y Unicode se conservan exactamente, y que una contraseña que qpdf no acepte levanta `PasswordCompatibilityError` sin devolver una versión modificada.

- [ ] **Step 2: Confirmar el fallo**

Run: `python -m pytest tests/test_passwords.py -v`  
Expected: FAIL por ausencia de las funciones.

- [ ] **Step 3: Implementar validación y generación**

Usar `secrets.token_urlsafe(32)` para la clave administrativa. `validate_password_pair` compara literalmente y `validate_pdf_password` realiza una comprobación compatible con `R=6` sin registrar la entrada ni normalizarla.

- [ ] **Step 4: Ejecutar pruebas**

Run: `python -m pytest tests/test_passwords.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_protector/passwords.py tests/test_passwords.py
git commit -m "feat: validate PDF credentials safely"
```

### Task 3: Inspección, saneamiento y combinación en memoria

**Files:**
- Create: `src/pdf_protector/pdf_service.py`
- Create: `tests/conftest.py`
- Create: `tests/test_pdf_service.py`

**Interfaces:**
- Consumes: `PdfPermissions`, `SourceInspection`, `SourcePdfError` y `CancelledError` de Task 1; `generate_owner_password` de Task 2.
- Produces: `inspect_source(path: Path) -> SourceInspection`, `build_encrypted_pdf(request: ProtectionRequest, sink: BinaryIO, is_cancelled: Callable[[], bool] = lambda: False, on_progress: Callable[[int, int], None] | None = None) -> int` donde el entero es el total de páginas.

- [ ] **Step 1: Crear fixtures y pruebas fallidas de inspección**

En `tests/conftest.py`, crear fábricas de PDF mínimo, multipágina, cifrado, dañado, firmado de prueba, con metadatos, JavaScript, adjunto, anotación y formulario con apariencia. En `tests/test_pdf_service.py`, probar conteo, detección de firma y errores que incluyen el nombre del origen cifrado/dañado/desaparecido.

- [ ] **Step 2: Confirmar fallos de inspección**

Run: `python -m pytest tests/test_pdf_service.py -k inspect -v`  
Expected: FAIL por ausencia de `inspect_source`.

- [ ] **Step 3: Implementar `inspect_source`**

Abrir con pikepdf sin contraseña, traducir exclusivamente errores conocidos a `SourcePdfError`, detectar firmas recorriendo campos `/FT /Sig` y firmas de certificación, y cerrar siempre el archivo.

- [ ] **Step 4: Verificar inspección**

Run: `python -m pytest tests/test_pdf_service.py -k inspect -v`  
Expected: PASS.

- [ ] **Step 5: Escribir pruebas fallidas de combinación y saneamiento**

Probar orden y total de páginas, ausencia de `/OpenAction`, `/AA`, JavaScript, `/EmbeddedFiles`, `/AcroForm`, metadatos heredados y outlines; comprobar que anotaciones/formularios mantienen apariencia visible aplanada, que cancelar entre fuentes levanta `CancelledError`, y que los hashes de los originales no cambian.

- [ ] **Step 6: Escribir pruebas fallidas de cifrado y las ocho combinaciones de permisos**

Parametrizar los ocho valores de `PdfPermissions`; abrir el resultado con clave incorrecta debe fallar, con clave del usuario debe funcionar, y `encryption.bits == 256`, `encryption.R == 6`, métodos AESv3 y bits de impresión/extracción/modificación deben coincidir exactamente.

- [ ] **Step 7: Confirmar fallos de procesamiento**

Run: `python -m pytest tests/test_pdf_service.py -k "combine or sanitize or encrypt or permissions or cancel" -v`  
Expected: FAIL porque falta `build_encrypted_pdf`.

- [ ] **Step 8: Implementar combinación, saneamiento y cifrado**

Crear un `pikepdf.Pdf.new()`, copiar páginas en orden y aplanar apariencias antes de eliminar estructuras interactivas y activas a nivel de catálogo/página. Guardar directamente en `sink` con `pikepdf.Encryption(R=6, aes=True, metadata=True, user=request.user_password, owner=generate_owner_password(), allow=...)`; mapear impresión a `print_highres`, copia a `extract`, y edición a todos los permisos `modify_*`, manteniendo accesibilidad habilitada.

- [ ] **Step 9: Ejecutar pruebas del servicio**

Run: `python -m pytest tests/test_pdf_service.py -v`  
Expected: PASS; ninguna prueba crea un PDF combinado sin cifrar en disco.

- [ ] **Step 10: Commit**

```bash
git add src/pdf_protector/pdf_service.py tests/conftest.py tests/test_pdf_service.py
git commit -m "feat: sanitize merge and encrypt PDF sources"
```

### Task 4: Publicación transaccional y verificación

**Files:**
- Create: `src/pdf_protector/output_service.py`
- Create: `tests/test_output_service.py`

**Interfaces:**
- Consumes: `ProtectionRequest`, `ProcessingResult`, errores de Task 1, `validate_pdf_password` de Task 2 y `build_encrypted_pdf` de Task 3.
- Produces: `protect_to_destination(request: ProtectionRequest, *, overwrite_confirmed: bool = False, is_cancelled: Callable[[], bool] = lambda: False, on_progress: Callable[[int, int], None] | None = None) -> ProcessingResult`, `is_remote_or_synced(path: Path) -> bool`.

- [ ] **Step 1: Escribir pruebas fallidas de publicación**

Probar extensión `.pdf`, destino existente sin confirmación, carpeta no escribible, contraseña incompatible, ruta de red/sincronizada detectada, desaparición de origen entre validación y apertura y éxito con renombrado final. Comprobar hashes de orígenes y destino previo antes/después.

- [ ] **Step 2: Escribir pruebas fallidas de recuperación**

Inyectar fallo de guardado, verificación y cancelación; en cada caso no debe existir destino nuevo, el destino anterior no cambia y no queda ningún temporal. Inspeccionar los temporales durante el guardado para confirmar que requieren contraseña y usan AES-256.

- [ ] **Step 3: Confirmar fallos**

Run: `python -m pytest tests/test_output_service.py -v`  
Expected: FAIL por ausencia del servicio.

- [ ] **Step 4: Implementar publicación transaccional**

Validar primero; crear un temporal de nombre aleatorio en la carpeta destino; escribirlo cifrado; reabrirlo con la contraseña del usuario; comprobar páginas, `bits=256`, `R=6` y métodos AESv3; cerrar; publicar con `os.replace` solo cuando se confirmó sobrescritura y siempre limpiar el temporal en `finally`.

- [ ] **Step 5: Ejecutar pruebas del servicio de salida**

Run: `python -m pytest tests/test_output_service.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pdf_protector/output_service.py tests/test_output_service.py
git commit -m "feat: publish protected PDFs transactionally"
```

### Task 5: Trabajador de procesamiento y cancelación

**Files:**
- Create: `src/pdf_protector/worker.py`
- Create: `tests/test_worker.py`

**Interfaces:**
- Consumes: `ProtectionRequest`, `ProcessingResult` y `protect_to_destination`.
- Produces: `ProtectionWorker(QObject)` con señales `progress(int, int)`, `succeeded(ProcessingResult)`, `failed(str)`, `cancelled()` y slots `run()` y `cancel()`; nunca incluye contraseñas en señales o mensajes.

- [ ] **Step 1: Escribir pruebas fallidas del trabajador**

Con `pytest-qt`, probar éxito, progreso monotónico, traducción de cada `ProtectionError` a mensaje español sin contraseña, excepción inesperada genérica sin detalles sensibles y cancelación antes/durante procesamiento.

- [ ] **Step 2: Confirmar el fallo**

Run: `python -m pytest tests/test_worker.py -v`  
Expected: FAIL por ausencia de `ProtectionWorker`.

- [ ] **Step 3: Implementar trabajador**

Usar `QObject` movible a `QThread`, un `threading.Event` privado para cancelar y un mapeo exhaustivo de errores a mensajes. Borrar la referencia al request en `finally`.

- [ ] **Step 4: Ejecutar pruebas**

Run: `python -m pytest tests/test_worker.py -v`  
Expected: PASS sin avisos de hilos Qt vivos.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_protector/worker.py tests/test_worker.py
git commit -m "feat: process PDFs without blocking the interface"
```

### Task 6: Interfaz completa y accesible

**Files:**
- Create: `src/pdf_protector/main_window.py`
- Create: `src/pdf_protector/__main__.py`
- Create: `src/pdf_protector/resources.qrc`
- Create: `tests/test_main_window.py`

**Interfaces:**
- Consumes: tipos de Task 1, `validate_password_pair`, `inspect_source`, `is_remote_or_synced` y `ProtectionWorker`.
- Produces: `MainWindow(QMainWindow)` y `main() -> int`.

- [ ] **Step 1: Escribir pruebas fallidas de selección y orden**

Probar selección múltiple solo `.pdf`, rechazo informativo de duplicados, botones Subir/Bajar/Quitar, orden estable, y que quitar no borra archivos. Añadir caso donde un origen desaparece después de seleccionarlo.

- [ ] **Step 2: Escribir pruebas fallidas de formulario y accesibilidad**

Probar casillas desactivadas por defecto, etiquetas `Permitir impresión`, `Permitir copiar contenido` y `Permitir edición`, campos ocultos, mostrar/ocultar, navegación por teclado, nombres accesibles y botón deshabilitado sin lista/contraseña coincidente.

- [ ] **Step 3: Escribir pruebas fallidas del flujo de ejecución**

Simular guardar/cancelar, confirmación de sobrescritura, aviso de ruta sincronizada/red, aviso por firma, progreso, cancelación, éxito con `Abrir carpeta`, error, limpieza de ambas contraseñas en éxito/error y cierre de ventana durante un trabajo sin publicar parcial.

- [ ] **Step 4: Confirmar fallos de UI**

Run: `python -m pytest tests/test_main_window.py -v`  
Expected: FAIL por ausencia de `MainWindow`.

- [ ] **Step 5: Implementar ventana y punto de entrada**

Construir la única ventana del wireframe aprobado; usar modelos Qt para la lista, diálogos nativos para entradas/destino, `QProgressDialog` para ejecución y un `QThread` por trabajo. Proponer `documentos_protegidos.pdf`, impedir mutaciones durante procesamiento y limpiar contraseñas al terminar.

- [ ] **Step 6: Ejecutar pruebas de UI y suite completa**

Run: `python -m pytest tests/test_main_window.py -v`  
Expected: PASS.  
Run: `python -m pytest -v`  
Expected: todas PASS.

- [ ] **Step 7: Commit**

```bash
git add src/pdf_protector/main_window.py src/pdf_protector/__main__.py src/pdf_protector/resources.qrc tests/test_main_window.py
git commit -m "feat: add Spanish desktop protection workflow"
```

### Task 7: Ejecutable, documentación y validación en Windows limpio

**Files:**
- Create: `packaging/pdf-protector.spec`
- Create: `scripts/build.ps1`
- Create: `.github/workflows/windows-build.yml`
- Create: `tests/test_packaged_app.py`
- Create: `README.md`
- Create: `THIRD_PARTY_LICENSES.md`

**Interfaces:**
- Consumes: `pdf_protector.__main__:main` y todos los módulos anteriores.
- Produces: `dist/ProtectorPDF/ProtectorPDF.exe` como distribución por carpeta; se elegirá `onedir` para inicio más rápido y extracción menos opaca que `onefile`.

- [ ] **Step 1: Escribir smoke test fallido del paquete**

`tests/test_packaged_app.py` debe lanzar `ProtectorPDF.exe --smoke-test`, exigir código 0, confirmar carga de Qt/pikepdf, crear y verificar un PDF AES-256 de prueba en una carpeta temporal y comprobar que stdout/stderr no contiene la contraseña centinela.

- [ ] **Step 2: Confirmar fallo antes del empaquetado**

Run: `python -m pytest tests/test_packaged_app.py -v`  
Expected: SKIP explícito si `dist/ProtectorPDF/ProtectorPDF.exe` no existe, nunca falso PASS.

- [ ] **Step 3: Crear configuración y script de construcción**

`scripts/build.ps1` creará `.venv-build`, instalará solo `requirements.lock`, ejecutará suite, construirá con `packaging/pdf-protector.spec` y ejecutará el smoke test. Incluir plugins Qt requeridos y binarios nativos de pikepdf/qpdf; no incluir herramientas de desarrollo.

- [ ] **Step 4: Documentar uso y límites**

README en español: selección/orden, contraseña, permisos, guardado, originales intactos, advertencia de rutas sincronizadas, firmas invalidadas, ausencia de recuperación y naturaleza orientativa de restricciones. `THIRD_PARTY_LICENSES.md` registrará nombre, versión, licencia y enlace oficial de cada dependencia distribuida.

- [ ] **Step 5: Añadir compilación automatizada de Windows**

El workflow instalará Python 3.12 x64, ejecutará `scripts/build.ps1`, subirá la carpeta `ProtectorPDF` como artefacto y no publicará releases automáticamente.

- [ ] **Step 6: Construir y verificar localmente**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build.ps1`  
Expected: suite PASS, smoke test PASS y `dist/ProtectorPDF/ProtectorPDF.exe` presente.

- [ ] **Step 7: Validar manualmente en entorno Windows limpio**

En Windows 10 22H2 y Windows 11 x64 sin Python y sin red: abrir aplicación, combinar dos PDF, comprobar orden, restricciones y AES-256, confirmar originales idénticos, provocar contraseña incorrecta y cancelar un proceso. Registrar resultados en una sección `Validación de distribución` del README.

- [ ] **Step 8: Commit**

```bash
git add packaging scripts .github tests/test_packaged_app.py README.md THIRD_PARTY_LICENSES.md
git commit -m "build: package and verify Windows application"
```

### Task 8: Verificación final contra el diseño

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: aplicación terminada y criterios del diseño.
- Produces: evidencia final reproducible y lista de limitaciones conocidas.

- [ ] **Step 1: Ejecutar controles automatizados finales**

Run: `python -m pytest -v`  
Expected: todas PASS.  
Run: `powershell -ExecutionPolicy Bypass -File scripts/build.ps1`  
Expected: compilación y smoke test PASS.

- [ ] **Step 2: Auditar artefactos y secretos**

Buscar temporales, contraseñas centinela, trazas de depuración y solicitudes de red en código/configuración. Confirmar que solo `dist/ProtectorPDF` es el entregable y que no contiene documentos de prueba ni credenciales.

- [ ] **Step 3: Ejecutar la matriz de aceptación**

Recorrer los 16 criterios de la sección 11 del diseño y anotar en README la prueba automatizada o validación manual que demuestra cada uno. Cualquier criterio sin evidencia bloquea la entrega.

- [ ] **Step 4: Documentar limitaciones observadas**

Registrar únicamente límites medidos: tamaño/memoria, lectores PDF probados, comportamiento de rutas de red/sincronizadas y advertencias de SmartScreen por ejecutable no firmado.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: record final acceptance evidence"
```
