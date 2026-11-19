# ProtectorPDF

ProtectorPDF es una aplicación de escritorio para Windows que combina uno o más PDF en el orden elegido y guarda un nuevo documento protegido con contraseña y cifrado AES-256. Los archivos originales no se modifican.

## Ejecutar la aplicación

1. Copie o descomprima la carpeta `ProtectorPDF` completa en una ubicación local.
2. Ejecute `ProtectorPDF.exe`. No mueva solamente el `.exe`: necesita los archivos de la subcarpeta `_internal`.
3. Si Windows muestra una advertencia por editor desconocido, verifique que el archivo provenga del canal interno autorizado. Esta versión no está firmada y no incluye instalador.

No se requiere Python ni conexión de red durante la ejecución. La aplicación no envía documentos, contraseñas ni telemetría.

## Uso

1. Pulse **Agregar PDF** y seleccione archivos PDF sin contraseña. Los archivos dañados o ya protegidos se rechazan.
2. Revise el orden visible. Use **Subir**, **Bajar** o **Quitar**; ese orden será el del resultado.
3. Escriba y confirme la contraseña de apertura. Puede usar espacios y caracteres Unicode compatibles con qpdf. La contraseña no se recorta ni normaliza.
4. Active, si corresponde, los permisos orientativos de impresión, copia y edición.
5. Pulse **Crear PDF protegido**, elija un destino con extensión `.pdf` y confirme cualquier reemplazo solicitado.
6. Espere la verificación final. Puede cancelar el proceso; una cancelación o error no publica una salida parcial.

La aplicación procesa los orígenes en memoria y escribe primero un archivo temporal ya cifrado. Solo publica el destino después de comprobar que se abre con la contraseña elegida y que usa AES-256 revisión 6.

## Seguridad y límites

- Guarde la contraseña en un medio seguro. **No existe recuperación de contraseña** y el proyecto no conserva copias ni claves maestras.
- Envíe la contraseña por un canal distinto del usado para entregar el PDF.
- Los originales permanecen intactos. El destino nunca puede sustituir uno de los archivos seleccionados.
- Las restricciones de impresión, copia y edición son indicaciones para lectores PDF compatibles; no impiden capturas de pantalla ni herramientas que decidan ignorarlas.
- Una ubicación de red o sincronizada (por ejemplo OneDrive, SharePoint, Dropbox, Box o Google Drive) genera una advertencia orientativa. Para reducir conflictos, guarde primero en una carpeta local y copie el resultado después.
- Combinar, aplanar o volver a cifrar un PDF invalida sus firmas digitales. La aplicación advierte antes de continuar cuando detecta firmas.
- Se eliminan contenido activo, adjuntos y metadatos; las apariencias de anotaciones y formularios se aplanan. Un formulario XFA o una apariencia que no pueda conservarse con seguridad se rechaza.
- El uso de memoria crece con el tamaño y la complejidad de los documentos. No se ha medido todavía un máximo de entrada ni de memoria, por lo que esta versión no declara un tamaño recomendado.

## Construcción reproducible

Requisitos de construcción: Windows x64, CPython 3.12.2 x64 y PowerShell. Las versiones de los paquetes y sus hashes están fijados en `requirements.lock`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

El script recrea `.venv-build`, instala únicamente `requirements.lock` con verificación de hashes, ejecuta las pruebas, construye con PyInstaller y ejecuta el smoke test del paquete. El resultado es la carpeta `dist/ProtectorPDF`, cuyo punto de entrada es `dist/ProtectorPDF/ProtectorPDF.exe`.

El workflow de GitHub Actions ejecuta el mismo script en Windows y sube esa carpeta como artefacto. No crea releases, instaladores ni firmas.

## Validación de distribución

### Evidencia local automatizada

El 19 de noviembre de 2026, `scripts/build.ps1` se ejecutó en un host de desarrollo Windows NT x64 build 26200.9457 con CPython 3.12.2 x64. El script recreó su entorno aislado, ejecutó **84 pruebas fuente** y **2 pruebas del paquete**, y generó `dist/ProtectorPDF/ProtectorPDF.exe` junto con este README y los avisos de licencias.

El smoke ejecutó el `.exe` real con `--smoke-test`, cargó Qt 6.12.0 y pikepdf 10.18.2/qpdf 12.4.2, creó un PDF de una página, rechazó una contraseña incorrecta y confirmó AES-256 revisión 6. La contraseña sintética del smoke no apareció en `stdout`, `stderr` ni en el informe JSON. Esta evidencia demuestra el paquete local; **no sustituye** una aceptación manual en una instalación limpia.

### Matriz de aceptación contra el diseño

Las referencias siguientes son pruebas automatizadas de la suite fuente. «Pendiente» no equivale a aprobado y bloquea el cierre de la aceptación de distribución.

| # | Criterio | Evidencia reproducible | Estado |
| --- | --- | --- | --- |
| 1 | Un PDF se procesa sin modificar el original. | `tests/test_pdf_service.py::test_combine_preserves_source_order_total_progress_and_original_bytes` compara SHA-256 antes y después. | Aprobado automatizado |
| 2 | Varios PDF conservan el orden visible y el total de páginas. | La misma prueba combina tres páginas y comprueba orden, contenido y total. | Aprobado automatizado |
| 3 | Solo abre con la contraseña elegida. | `test_encrypt_requires_the_user_password_and_uses_aes256_revision_6` y el smoke del paquete rechazan una contraseña incorrecta. | Aprobado automatizado |
| 4 | El resultado usa AES-256. | `test_encrypt_requires_the_user_password_and_uses_aes256_revision_6` inspecciona 256 bits, revisión 6 y AESV3. | Aprobado automatizado |
| 5 | Las ocho combinaciones de permisos se traducen al PDF. | `test_permissions_map_all_eight_policies_exactly`. | Aprobado automatizado |
| 6 | Una contraseña con espacios y Unicode funciona literalmente. | `tests/test_passwords.py::test_password_validation_passes_spaces_and_unicode_to_qpdf_literally` y `test_worker_request_preserves_literal_password_and_distinguishes_permission_choices`. | Aprobado automatizado |
| 7 | Una contraseña no representable se rechaza sin modificarla. | `test_password_qpdf_rejects_raises_compatibility_error` y `test_password_with_unpaired_surrogate_raises_compatibility_error`. | Aprobado automatizado |
| 8 | La contraseña no llega a registros ni archivos auxiliares. | `tests/test_packaged_app.py::test_packaged_smoke_loads_qt_and_pikepdf_and_produces_aes256` comprueba salida y reporte; las pruebas de `worker` comprueban mensajes sin secreto. | Aprobado automatizado |
| 9 | No persisten contenido activo, adjuntos ni metadatos; las apariencias se aplanan. | `test_sanitize_removes_active_content_and_flattens_visible_appearances`; las pruebas de XFA/apariencia no segura rechazan pérdidas silenciosas. | Aprobado automatizado |
| 10 | Se advierte la invalidación de firmas. | `test_inspect_detects_signature_fields_and_certification_signatures` y `test_signature_warning_is_confirmed_before_destination_selection`. | Aprobado automatizado |
| 11 | No se escribe una combinación sin cifrar en disco. | `test_publishes_only_a_verified_aes256_temporary_by_atomic_claim` abre el temporal, verifica AES-256 y solo después observa el renombre atómico. | Aprobado automatizado |
| 12 | Un origen dañado o protegido informa el error y no publica una salida parcial. | `test_inspect_reports_known_source_errors_with_the_file_name`, `test_missing_source_after_validation_never_publishes_a_destination` y `test_failures_leave_no_new_destination_and_preserve_an_existing_one`. | Aprobado automatizado |
| 13 | Cancelar la elección de destino no cambia archivos. | `test_cancelled_save_dialog_does_not_start_or_change_files`. | Aprobado automatizado |
| 14 | Un error de escritura preserva un destino existente. | `test_failures_leave_no_new_destination_and_preserve_an_existing_one`. | Aprobado automatizado |
| 15 | El ejecutable funciona sin Python ni red en una instalación limpia de Windows definida. | El smoke local empaquetado es evidencia parcial; faltan las dos ejecuciones manuales limpias detalladas abajo. | **Pendiente — bloquea la aceptación final de distribución** |
| 16 | El flujo se realiza por teclado y tiene etiquetas comprensibles. | `test_form_defaults_labels_accessibility_and_keyboard_focus` y `test_tab_navigation_follows_the_visible_workflow`. | Aprobado automatizado |

### Auditoría del artefacto

El único entregable es la carpeta `dist/ProtectorPDF`; debe distribuirse completa, sin los directorios de construcción o pruebas. La revisión de código y configuración no encontró cliente de red propio, telemetría, registros de depuración ni credenciales de usuario. Las contraseñas literales propias son valores sintéticos, claramente identificados, usados por las pruebas y el smoke; no son credenciales y el smoke comprueba que no se escriben en su salida ni en su informe. Dependencias redistribuidas pueden incluir ejemplos de API sin credenciales reales. La carpeta distribuida no contiene documentos PDF de prueba. Las pruebas transaccionales comprueban además que el temporal es cifrado y se elimina en éxito, error o cancelación.

### Límites medidos y alcance de validación

- **Tamaño y memoria:** no se ha ejecutado una medición de documentos grandes ni de memoria; no se declara máximo ni recomendación de tamaño.
- **Lectores PDF:** no se ha completado una prueba manual con lectores PDF. La única comprobación técnica local usa pikepdf 10.18.2/qpdf 12.4.2; las restricciones de permisos siguen dependiendo del lector.
- **Rutas de red o sincronizadas:** la prueba automatizada cubre una ruta UNC y una ruta con `OneDrive` como advertencias, y una ruta local como no advertida. No se ha medido una escritura real en un recurso de red o carpeta sincronizada.
- **SmartScreen:** el ejecutable no está firmado. No se ha observado aún el aviso en una máquina limpia; su comportamiento queda pendiente de la aceptación manual.

### Aceptación manual en Windows limpio

La aceptación en equipos limpios sigue **pendiente**. No se afirma compatibilidad validada hasta completar ambos ambientes:

| Ambiente | Python instalado | Red durante la prueba | Estado |
| --- | --- | --- | --- |
| Windows 10 22H2 x64 | No | Desconectada | Pendiente |
| Windows 11 x64 | No | Desconectada | Pendiente |

Lista reproducible para cada ambiente:

1. Partir de una máquina virtual limpia con un lector PDF disponible, sin Python, y desconectar la red.
2. Copiar la carpeta `ProtectorPDF` completa y abrir `ProtectorPDF.exe`.
3. Calcular `Get-FileHash -Algorithm SHA256` de dos PDF de prueba y guardar los valores.
4. Agregar ambos archivos, invertir su orden visible, elegir una contraseña con espacios y Unicode, configurar los tres permisos y crear el resultado en una carpeta local.
5. Confirmar el orden y total de páginas; comprobar que una contraseña incorrecta falla y que la correcta abre el documento.
6. Revisar en dos lectores compatibles las restricciones solicitadas y recordar que son orientativas; anotar exactamente cuáles fueron los lectores y sus versiones.
7. Repetir `Get-FileHash` sobre los originales y confirmar que los hashes no cambiaron.
8. Iniciar un segundo proceso, pulsar **Cancelar** y comprobar que no queda salida final ni temporal.
9. Ejecutar con PowerShell `Start-Process -Wait -PassThru .\ProtectorPDF.exe -ArgumentList '--smoke-test'` y comprobar `ExitCode` igual a `0`.
10. Registrar versión exacta de Windows, lectores probados, hashes, resultados y cualquier aviso de SmartScreen.

## Licencias

Las dependencias redistribuidas y sus licencias se documentan en [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
