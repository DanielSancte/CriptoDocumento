# Diseño: aplicación de escritorio para proteger documentos PDF

**Fecha:** 2026-11-19  
**Estado:** aprobado el 2026-11-19

## 1. Intención y contexto

La organización necesita una aplicación interna para que un funcionario prepare documentos PDF antes de enviarlos por correo electrónico. El funcionario podrá seleccionar uno o varios PDF, ordenarlos, unirlos en un solo documento, escoger una contraseña y decidir si el destinatario tendrá permiso para imprimir, copiar o editar.

La aplicación solo preparará el archivo. No se conectará ni se integrará con el correo electrónico. El funcionario adjuntará manualmente el PDF resultante en el sistema de correo que utilice.

La protección real del contenido se realizará con cifrado PDF AES-256. Los permisos de impresión, copia y edición se incorporarán como restricciones estándar del PDF. Estas restricciones dependen de que el lector de PDF las respete; no ofrecen la misma garantía criptográfica que la contraseña de apertura.

## 2. Objetivos

- Ejecutarse como aplicación de escritorio en Windows y distribuirse en formato ejecutable.
- Funcionar completamente sin conexión a Internet.
- Permitir seleccionar uno o varios archivos PDF.
- Permitir ordenar los archivos antes de combinarlos.
- Combinar los archivos seleccionados en un único PDF.
- Solicitar al funcionario una contraseña de apertura y su confirmación.
- Cifrar el resultado con AES-256 conforme al mecanismo de cifrado estándar de PDF.
- Permitir que el funcionario active o desactive individualmente los permisos de impresión, copia y edición.
- Solicitar una ubicación y nombre para guardar el resultado.
- Mantener siempre intactos los archivos originales.
- No almacenar, registrar ni transmitir la contraseña del funcionario.
- Informar claramente el éxito o cualquier error sin dejar un resultado parcial confundible con un archivo válido.

## 3. Fuera de alcance

- Enviar correos electrónicos o integrarse con Outlook, Gmail u otro cliente.
- Administrar destinatarios, mensajes o plantillas de correo.
- Recuperar contraseñas olvidadas.
- Almacenar contraseñas, historiales de contraseñas o archivos procesados.
- Editar el contenido, firmar digitalmente, aplicar OCR o convertir otros formatos a PDF.
- Proteger archivos que no sean PDF.
- Garantizar que todos los lectores PDF respeten las restricciones de impresión, copia y edición.
- Reemplazar una solución de gestión documental o de prevención de fuga de información.

## 4. Antiobjetivos

El producto se considerará incorrecto si modifica los originales, guarda contraseñas, envía documentos fuera del equipo, produce un archivo sin AES-256, permite confundir una salida incompleta con una válida o afirma que los permisos PDF son imposibles de eludir.

## 5. Enfoques considerados

### 5.1 Python + PySide6 + pikepdf/qpdf — seleccionado

PySide6 proporcionará la interfaz de Windows y pikepdf, respaldado por qpdf, realizará la lectura, combinación, cifrado y definición de permisos. Se empaquetará como aplicación de Windows.

**Ventajas:** desarrollo directo, soporte sólido para AES-256 y permisos PDF, operación local, interfaz moderna y ausencia de una licencia comercial obligatoria para este alcance.  
**Costes:** distribución de mayor tamaño y necesidad de comprobar cuidadosamente el empaquetado de dependencias nativas.

### 5.2 C#/.NET

Ofrece una experiencia muy nativa en Windows y buen rendimiento. Se descartó para esta primera versión porque el soporte PDF completo requerido suele depender de elegir y posiblemente adquirir una biblioteca comercial, lo que aumenta coste y decisiones de licencia.

### 5.3 Electron/JavaScript

Ofrece gran flexibilidad visual, pero se descartó porque aumenta considerablemente el tamaño y consumo de memoria sin aportar una ventaja proporcional para una utilidad local de alcance acotado.

### 5.4 Java + JavaFX

Facilitaría una futura distribución multiplataforma, pero se descartó porque el requisito actual es Windows y la distribución del entorno de ejecución añade complejidad innecesaria.

## 6. Experiencia de uso

La aplicación tendrá una única ventana principal con un flujo lineal:

```text
┌──────────────────────────────────────────────────────────────┐
│ Protección de documentos PDF                                │
├──────────────────────────────────────────────────────────────┤
│ Archivos seleccionados                         [Agregar PDF] │
│  1. antecedente.pdf                              [Subir]     │
│  2. informe.pdf                                  [Bajar]     │
│                                                  [Quitar]     │
├──────────────────────────────────────────────────────────────┤
│ Contraseña          [••••••••••••••] [Mostrar]              │
│ Confirmar           [••••••••••••••]                         │
│                                                              │
│ Permitir:  ☐ Impresión   ☐ Copiar contenido   ☐ Edición     │
├──────────────────────────────────────────────────────────────┤
│                              [Crear PDF protegido]           │
└──────────────────────────────────────────────────────────────┘
```

### 6.1 Selección y orden

- `Agregar PDF` abrirá el selector de archivos y admitirá selección múltiple.
- La lista mostrará el nombre de cada archivo y mantendrá el orden de combinación.
- `Subir` y `Bajar` cambiarán la posición del elemento seleccionado.
- `Quitar` lo eliminará de la lista sin borrar el archivo del disco.
- Se evitará añadir dos veces la misma ruta; si sucede, se informará al funcionario.
- Debe existir al menos un PDF para iniciar el proceso.

### 6.2 Contraseña

- La contraseña de apertura será escrita y confirmada por el funcionario.
- Se aceptará cualquier contraseña no vacía; la interfaz recomendará una contraseña robusta sin imponer una política organizacional no definida.
- Los campos ocultarán el texto de forma predeterminada y ofrecerán un control momentáneo para mostrarlo.
- Si las dos entradas no coinciden, no se iniciará el proceso.
- La contraseña existirá en memoria solo durante el procesamiento y no se escribirá en archivos de configuración, registros ni telemetría.
- Antes de procesar se comprobará que la contraseña pueda representarse íntegramente dentro de los límites admitidos por el cifrado PDF y la biblioteca. Si no es compatible, se rechazará con una explicación; nunca se truncará, normalizará ni transformará silenciosamente.
- Al completar o fallar el proceso, se limpiarán ambos campos.

### 6.3 Permisos

Las casillas estarán formuladas como acciones permitidas para evitar ambigüedad:

- `Permitir impresión`
- `Permitir copiar contenido`
- `Permitir edición`

Por seguridad, las tres estarán desactivadas inicialmente. La impresión permitida será de calidad completa. La edición se tratará como permiso general de modificación. Copiar controlará la extracción de texto e imágenes. La accesibilidad se conservará cuando el estándar y la biblioteca la distingan de la copia general.

La contraseña introducida será la contraseña de apertura del documento. Para hacer efectivos los permisos, la aplicación generará criptográficamente una contraseña administrativa aleatoria distinta, que no mostrará ni conservará. Como consecuencia deliberada, los permisos no podrán modificarse posteriormente con esta aplicación sobre el resultado; el funcionario podrá volver a generarlo desde los originales conservados.

### 6.4 Guardado

- Al pulsar `Crear PDF protegido`, se abrirá un diálogo para escoger nombre y ubicación.
- El nombre propuesto será `documentos_protegidos.pdf`.
- La extensión final será `.pdf`.
- La aplicación no sobrescribirá silenciosamente un archivo existente; el diálogo solicitará confirmación.
- La salida se construirá primero como archivo temporal en la carpeta de destino y solo se moverá al nombre definitivo después de completarse y validarse.
- Se permitirán ubicaciones locales, unidades de red y carpetas sincronizadas que el funcionario elija y para las que tenga permisos. La aplicación advertirá que guardar en una carpeta sincronizada puede hacer que el servicio correspondiente transmita el resultado; la aplicación no iniciará esa transmisión.
- Tras el éxito, se mostrará la ruta final y se ofrecerá `Abrir carpeta`, sin abrir automáticamente el documento ni conservar su contraseña.

### 6.5 Tratamiento seguro del contenido

Al combinar documentos se conservarán las páginas, el texto, las imágenes y las anotaciones visibles. La aplicación generará un documento nuevo y seguro:

- Los formularios interactivos se aplanarán para conservar solamente su apariencia visible.
- Se eliminarán archivos adjuntos, JavaScript, acciones automáticas, scripts y demás contenido activo.
- Se eliminarán los metadatos heredados de los documentos de origen.
- No se intentarán conservar estructuras documentales que puedan apuntar incorrectamente al combinar, como marcadores originales; el resultado tendrá una secuencia limpia de páginas.
- Las firmas digitales originales no se conservarán como firmas válidas. Si se detectan, se advertirá antes de crear el resultado, pues combinar o modificar un PDF invalida su firma.

Si un elemento no puede conservarse de forma visible y segura, el procesamiento se detendrá identificando el archivo afectado en vez de descartarlo silenciosamente.

## 7. Procesamiento y seguridad

1. Validar la lista, contraseña, coincidencia y destino.
2. Abrir cada PDF en el orden mostrado.
3. Rechazar con un mensaje identificable cualquier archivo dañado, no compatible o protegido con contraseña. La primera versión no solicitará contraseñas de archivos de origen.
4. Copiar y sanear todas las páginas en ese orden dentro de un documento nuevo mantenido en memoria; nunca se escribirá al disco una versión combinada sin cifrar.
5. Generar la contraseña administrativa con un generador criptográficamente seguro.
6. Guardar directamente una salida temporal cifrada con AES-256, la contraseña de apertura indicada y los permisos seleccionados.
7. Reabrir/verificar la salida temporal para comprobar que es un PDF cifrado y que se puede abrir con la contraseña indicada.
8. Cerrar manejadores, eliminar el temporal en caso de error y publicar el resultado mediante una operación final de reemplazo/movimiento.
9. Limpiar de la interfaz la contraseña y las referencias que puedan liberarse explícitamente.

No se imprimirán contraseñas en consola o registros. Los mensajes de error podrán contener nombres de archivo, pero no credenciales ni contenido documental. No habrá telemetría ni solicitudes de red iniciadas por la aplicación. El requisito de no escribir contenido combinado sin cifrar puede limitar el tamaño procesable según la memoria disponible; la interfaz deberá detectar y comunicar limpiamente ese límite.

## 8. Manejo de errores

La aplicación permanecerá abierta y permitirá corregir el problema. Los mensajes distinguirán al menos:

- No se han seleccionado archivos.
- Las contraseñas están vacías o no coinciden.
- Un archivo no existe, no puede leerse, no es un PDF válido o está protegido.
- No se puede escribir en la carpeta elegida.
- No hay espacio suficiente o el proceso fue interrumpido.
- Falló la combinación, el cifrado o la validación final.

Cuando un archivo de origen sea el causante, se mostrará su nombre. Ante cualquier fallo se conservarán los originales y se eliminará la salida temporal creada por la aplicación. Si ya existía un archivo de destino, no debe quedar alterado por un fallo.

## 9. Arquitectura propuesta

- **Interfaz:** ventana y diálogos PySide6, sin lógica PDF incrustada en los controles.
- **Modelo de selección:** lista ordenada de rutas validadas.
- **Servicio PDF:** combinación de páginas, traducción de las tres decisiones de permisos y cifrado AES-256 mediante pikepdf/qpdf.
- **Servicio de salida:** creación temporal, validación y publicación segura del resultado.
- **Empaquetado:** generación de una aplicación ejecutable para Windows; el plan decidirá entre ejecutable único o carpeta instalable basándose en pruebas reales de inicio y compatibilidad.
- **Configuración:** no se requiere base de datos. Como máximo podrán persistirse preferencias no sensibles en el futuro; la primera versión no necesita historial.

La lógica de procesamiento será independiente de la interfaz para permitir pruebas automatizadas con documentos de muestra.

## 10. Distribución

El entregable será una aplicación para Windows que el funcionario pueda ejecutar sin instalar Python. El paquete incluirá las dependencias necesarias y un archivo breve de instrucciones. La primera versión no presupone firma digital del ejecutable ni instalador corporativo; ambos quedan como mejoras posteriores si la organización dispone de certificado o mecanismo de despliegue.

Se documentarán las licencias de las dependencias incluidas. El proceso de construcción será reproducible desde el repositorio.

## 11. Pruebas y criterios de aceptación

La implementación se considerará aceptable cuando las pruebas demuestren que:

1. Un PDF se procesa y el original conserva exactamente sus bytes.
2. Varios PDF se combinan respetando el orden visible y el total de páginas esperado.
3. El resultado requiere la contraseña elegida; una contraseña incorrecta no lo abre.
4. La inspección técnica confirma cifrado AES-256.
5. Las ocho combinaciones posibles de los tres permisos se traducen correctamente al PDF.
6. Una contraseña con espacios y caracteres Unicode funciona de principio a fin.
7. Una contraseña no representable se rechaza sin truncarla ni transformarla.
8. Una contraseña no aparece en registros ni archivos creados aparte del PDF cifrado.
9. El resultado no conserva contenido activo, adjuntos ni metadatos de los orígenes, y los formularios conservan su apariencia aplanada.
10. La aplicación advierte cuando encuentra firmas digitales que serán invalidadas.
11. Durante el proceso no se crea en disco ninguna copia combinada sin cifrar.
12. Un origen dañado o protegido produce un mensaje útil y no deja un resultado final parcial.
13. Cancelar la selección de destino no cambia ningún archivo.
14. Un error al escribir no altera un destino preexistente.
15. El ejecutable funciona en una instalación limpia de la versión de Windows definida durante el plan, sin Python instalado y sin conexión a Internet.
16. El flujo completo puede realizarse utilizando teclado, y los controles tienen etiquetas comprensibles.

## 12. Decisiones dejadas al constructor durante el plan

- Estructura exacta de módulos, clases y pruebas.
- Herramienta concreta de empaquetado y si conviene entregar un ejecutable único o una carpeta de aplicación, después de medir ambos.
- Iconografía, colores y detalles visuales, manteniendo una interfaz sobria, accesible y en español.
- Tamaño máximo recomendado y estrategia de progreso para documentos grandes, determinada mediante pruebas sin cambiar el flujo aprobado.
- Versión mínima concreta de Windows, que deberá declararse y validarse antes de cerrar el plan de distribución.

## 13. Mejoras futuras posibles

- Aceptar archivos de origen protegidos solicitando sus contraseñas.
- Perfiles de permisos definidos por la organización.
- Firma de código e instalador administrado.
- Arrastrar y soltar archivos.
- Procesamiento por lotes para producir varios resultados separados.
- Integración opcional con sistemas de correo o gestión documental.
