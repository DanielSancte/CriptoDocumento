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
- El uso de memoria crece con el tamaño y la complejidad de los documentos. Esta versión no define un tamaño máximo garantizado.

## Construcción reproducible

Requisitos de construcción: Windows x64, CPython 3.12.2 x64 y PowerShell. Las versiones de los paquetes y sus hashes están fijados en `requirements.lock`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

El script recrea `.venv-build`, instala únicamente `requirements.lock` con verificación de hashes, ejecuta las pruebas, construye con PyInstaller y ejecuta el smoke test del paquete. El resultado es la carpeta `dist/ProtectorPDF`, cuyo punto de entrada es `dist/ProtectorPDF/ProtectorPDF.exe`.

El workflow de GitHub Actions ejecuta el mismo script en Windows y sube esa carpeta como artefacto. No crea releases, instaladores ni firmas.

## Validación de distribución

### Evidencia local automatizada

El 19 de noviembre de 2026 se ejecutó `scripts/build.ps1` en un host de desarrollo Windows NT x64 build 26200.9457 con CPython 3.12.2 x64. La suite fuente terminó con **84 pruebas aprobadas** y el smoke test del paquete con **1 prueba aprobada**. Se generó `dist/ProtectorPDF/ProtectorPDF.exe` junto con este README y los avisos de licencias.

El smoke ejecutó el `.exe` real con `--smoke-test`, cargó Qt 6.12.0 y pikepdf 10.18.2/qpdf 12.4.2, creó un PDF de una página, rechazó una contraseña incorrecta y confirmó AES-256 revisión 6. La contraseña centinela no apareció en `stdout`, `stderr` ni en el informe JSON. Esta evidencia prueba el build local empaquetado, pero **no sustituye** la aceptación en una instalación limpia.

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
6. Revisar en dos lectores compatibles, cuando estén disponibles, las restricciones solicitadas y recordar que son orientativas.
7. Repetir `Get-FileHash` sobre los originales y confirmar que los hashes no cambiaron.
8. Iniciar un segundo proceso, pulsar **Cancelar** y comprobar que no queda salida final ni temporal.
9. Ejecutar con PowerShell `Start-Process -Wait -PassThru .\ProtectorPDF.exe -ArgumentList '--smoke-test'` y comprobar `ExitCode` igual a `0`.
10. Registrar versión exacta de Windows, lectores probados, hashes, resultados y cualquier aviso de SmartScreen.

## Licencias

Las dependencias redistribuidas y sus licencias se documentan en [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
