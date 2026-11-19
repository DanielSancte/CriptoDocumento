# Licencias de terceros

Este inventario corresponde específicamente a la distribución Windows x64
generada por `scripts/build.ps1` con `requirements.lock`. Se contrastaron el
contenido de PyInstaller, los metadatos instalados, las versiones informadas en
ejecución y los avisos que pikepdf incluye dentro del artefacto.

Los avisos completos aportados por pikepdf están en:

`_internal/pikepdf-10.18.2.dist-info/licenses/`

Las versiones indicadas como **incluida** no tienen un identificador de versión
independiente verificable en este artefacto. No se les atribuye una versión por
inferencia.

## Componentes Python y Qt

| Componente redistribuido | Versión comprobada | Licencia | Fuente de licencia o versión |
| --- | ---: | --- | --- |
| CPython y biblioteca estándar | 3.12.2 x64 | Python Software Foundation License Version 2 (PSF-2.0) y avisos de terceros de CPython | [Historia y licencia de Python 3.12](https://docs.python.org/3.12/license.html) |
| PySide6 / Qt for Python | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Licencias de Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html) |
| PySide6-Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [PySide6-Essentials](https://pypi.org/project/PySide6-Essentials/6.12.0/) |
| PySide6-Addons | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [PySide6-Addons](https://pypi.org/project/PySide6-Addons/6.12.0/) |
| PySide6-Pdf / Qt PDF | 6.12.0.140 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [PySide6-Pdf](https://pypi.org/project/PySide6-Pdf/6.12.0.140/) |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Shiboken](https://doc.qt.io/qtforpython-6/shiboken6/) |
| pikepdf | 10.18.2 | MPL-2.0 | Aviso incluido `pikepdf-10.18.2.dist-info/licenses/LICENSE.txt` y [pikepdf](https://github.com/pikepdf/pikepdf) |
| Pillow | 13.0.0 | MIT-CMU | [Pillow LICENSE 13.0.0](https://github.com/python-pillow/Pillow/blob/13.0.0/LICENSE) |
| lxml | 6.1.3 | BSD-3-Clause, más los avisos de recursos y bibliotecas enlazadas detallados más abajo | [lxml licenses](https://github.com/lxml/lxml/tree/lxml-6.1.3/doc/licenses) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [Licencias de packaging](https://github.com/pypa/packaging/tree/26.3/LICENSES) |
| typing-extensions | 4.16.0 | PSF-2.0 | [typing_extensions LICENSE](https://github.com/python/typing_extensions/blob/4.16.0/LICENSE) |
| Bootloader de PyInstaller | 6.22.3 | GPL-2.0-or-later con excepción especial para distribuir las aplicaciones resultantes | [Licencia de PyInstaller](https://pyinstaller.org/en/stable/license.html) |

La distribución contiene módulos Qt 6.12 de Core, Gui, Widgets, Network,
OpenGL, PDF, QML, Quick, SVG y Virtual Keyboard, además de plugins de plataforma
(`qwindows`, `qoffscreen`, `qminimal`, `qdirect2d`), formatos de imagen, TLS,
estilo, iconos y entrada. También contiene `opengl32sw.dll`, suministrado por
la distribución binaria de Qt. Esos binarios se consideran parte del conjunto
Qt 6.12; cuando un componente de terceros interno no expone una versión propia,
este inventario no inventa una. Los avisos autoritativos por módulo están en
[Licencias usadas en Qt](https://doc.qt.io/qt-6/licenses-used-in-qt.html) y en
[Qt Third-Party Code](https://code.qt.io/cgit/qt/qtdoc.git/tree/src/legalese/3rdparty-code.md).

Qt se redistribuye como bibliotecas dinámicas, sin modificación. Este documento
no sustituye las obligaciones aplicables de LGPL/GPL ni los avisos de terceros
de Qt.

## Proveedor PDF: pikepdf y su wheel de Windows

La fuente primaria de esta sección es el aviso incluido
`third-party-licenses/README.md` de pikepdf 10.18.2. Ese aviso explica qué
componentes están presentes en el wheel de Windows y cómo se enlazan.

| Componente | Versión comprobada | Forma incluida | Licencia | Aviso incluido |
| --- | ---: | --- | --- | --- |
| qpdf | 12.4.2 | `pikepdf.libs/qpdf30-*.dll`; versión informada por `pikepdf.__libqpdf_version__` | Apache-2.0 | `qpdf.txt` |
| libjpeg-turbo usado por qpdf | Incluida; el wheel de Windows no declara una versión independiente | Enlace estático dentro de `qpdf30-*.dll` | IJG + BSD-3-Clause + Zlib | `libjpeg-turbo.txt` y `libjpeg-turbo-README.ijg.txt` |
| OpenSSL usado por qpdf | Incluida; no expuesta de forma independiente | Enlace estático dentro de `qpdf30-*.dll` como backend criptográfico de qpdf | Apache-2.0 | `openssl.txt` |
| zlib usado por qpdf | Incluida; no expuesta de forma independiente | Enlace estático dentro de `qpdf30-*.dll` | Zlib | `zlib.txt` |
| Microsoft Visual C++ Standard Library usada por qpdf | 14.51.36247.0 | `pikepdf.libs/msvcp140-*.dll` | Microsoft Visual Studio 2022 Runtime Terms | `microsoft-visual-cpp-runtime.txt` |

El aviso incluido menciona OpenSSL 3.6.0 y zlib 1.3.1 como ejemplos de una
versión anterior de pikepdf y advierte que no garantizan el contenido de otro
wheel. Por eso esta tabla no los presenta como versiones comprobadas de los
objetos enlazados en pikepdf 10.18.2. Estas copias estáticas tampoco deben
confundirse con las copias que acompañan a CPython o Pillow descritas más
abajo.

### Datos PDF/A incluidos por pikepdf

| Datos o código de origen | Versión | Licencia | Aviso incluido |
| --- | ---: | --- | --- |
| Perfil sRGB ICC de `icc-profiles-free` (`sRGB.icc`) | Incluida; sin versión independiente declarada | Zlib | `sRGB-icc-profile.txt` |
| Reglas de perfiles de validación veraPDF (`verapdf_rules.json`) | Incluida; convertida de XML a JSON por pikepdf | CC-BY-4.0 | `CC-BY-4.0-veraPDF.txt` |
| Tabla Latin encoding derivada de pdfminer.six (`_latin_enc.py`) | Incluida; sin versión independiente declarada | MIT | `pdfminer.six.txt` |

Los JSON de esquemas, disposiciones y propiedades XMP del paquete PDF/A son
parte de pikepdf 10.18.2. Cuando contienen material de terceros, los avisos
anteriores son los que el propio wheel declara para esta distribución.

Los archivos `GPL-3.0.txt` y `GCC-exception-3.1.txt` también aparecen en el
directorio de avisos porque el mismo conjunto de metadatos cubre wheels de
otras plataformas. El aviso de pikepdf los limita al runtime GCC de
musllinux; no existe ese runtime en este artefacto Windows y no se declara
como componente redistribuido aquí.

## Códecs y bibliotecas nativas del wheel de Pillow

La extensión de Pillow incluida por PyInstaller contiene `_imaging`,
`_imagingcms`, `_webp` y `_avif`. La versión y licencia de cada biblioteca de
su wheel se tomaron del `LICENSE` de Pillow 13.0.0 y de
`PIL.features` en el entorno fijado.

| Componente incluido por Pillow | Versión | Licencia declarada por el aviso de Pillow |
| --- | ---: | --- |
| Brotli | 1.2.0 | MIT |
| FreeType | 2.14.3 | FreeType License (FTL) OR GPL-2.0-only; partes auxiliares según el mismo aviso |
| HarfBuzz | 14.5.0 | Old MIT |
| Little CMS (lcms2) | 2.19.1 | MIT |
| libavif | 1.4.2 | BSD-2-Clause, más avisos de los archivos de terceros enumerados en su sección del `LICENSE` de Pillow |
| libjpeg-turbo | 3.2.0 | IJG + BSD-3-Clause + Zlib |
| libpng | 1.6.58 | PNG Reference Library License 2.0 |
| libwebp | 1.6.0 | BSD-3-Clause |
| OpenJPEG | 2.5.4 | BSD-2-Clause |
| LibTIFF | 4.7.2 | Licencia LibTIFF (BSD-like) y avisos incorporados indicados por Pillow |
| liblzma / XZ Utils | 5.8.4 | 0BSD para `liblzma`; el aviso consolidado enumera otras licencias para archivos de XZ no necesariamente enlazados |
| zlib-ng | 2.3.3 (`1.3.1.zlib-ng` en modo compatible zlib) | Zlib |

La extensión `_imagingtk` también está presente, pero el artefacto no copia
DLL de Tcl/Tk; por ello no se declara un runtime Tcl/Tk redistribuido.

## Bibliotecas incorporadas por lxml

El aviso `LICENSES.txt` del wheel oficial de lxml indica que sus wheels
binarios incorporan zlib, iconv, libxml2, libxslt y libexslt.

| Componente | Versión comprobada | Licencia |
| --- | ---: | --- |
| libxml2 | 2.11.9 | MIT |
| libxslt | 1.1.45 | MIT |
| libexslt | Incluida; versión independiente no expuesta | MIT |
| zlib enlazada por lxml | Incluida; versión independiente no expuesta | Zlib |
| iconv enlazada por lxml | Incluida; versión independiente no expuesta | LGPL-2.1 |

lxml también distribuye recursos RelaxNG/XSL de ISO Schematron. El inventario
PyInstaller confirma esos archivos bajo `_internal/lxml/isoschematron/`; sus
autores y condiciones por archivo están descritos en
[LICENSES.txt de lxml 6.1.3](https://github.com/lxml/lxml/blob/lxml-6.1.3/LICENSES.txt).

## Dependencias nativas del runtime CPython

| Componente | Versión comprobada | Evidencia en el artefacto | Licencia o términos |
| --- | ---: | --- | --- |
| OpenSSL de CPython | 3.0.13 | `libcrypto-3.dll`, `libssl-3.dll`, `_ssl.pyd`, `_hashlib.pyd` | Apache-2.0; [avisos de CPython 3.12](https://docs.python.org/3.12/license.html#openssl) |
| Expat | 2.5.0 | `pyexpat.pyd`, `_elementtree.pyd`; versión informada por `pyexpat.EXPAT_VERSION` | MIT; [avisos de CPython 3.12](https://docs.python.org/3.12/license.html#expat) |
| libffi | Incluida; `libffi-8.dll` no expone versión de producto | `libffi-8.dll`, `_ctypes.pyd` | MIT; [libffi LICENSE](https://github.com/libffi/libffi/blob/master/LICENSE) |
| bzip2 | Incluida por el build de CPython; versión independiente no expuesta | `_bz2.pyd` | Licencia permisiva bzip2; [avisos de CPython 3.12](https://docs.python.org/3.12/license.html#bzip2) |
| liblzma / XZ usada por CPython | Incluida por el build de CPython; versión independiente no expuesta | `_lzma.pyd` | Términos de XZ Utils indicados por los avisos de CPython; [licencia de Python 3.12](https://docs.python.org/3.12/license.html) |
| Unicode Character Database | 15.0.0 | `unicodedata.pyd`; versión informada por `unicodedata.unidata_version` | Unicode License v3; [Unicode Data Files and Software License](https://www.unicode.org/license.txt) |

## Microsoft Visual C++ Runtime

El artefacto contiene copias distintas porque los wheels fueron compilados con
toolsets diferentes. Se conservaron sus ubicaciones originales; no se afirma
que sean una única versión.

| Proveedor dentro del artefacto | Archivos | Versión de archivo | Términos |
| --- | --- | ---: | --- |
| CPython 3.12.2 | `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` | 14.38.33126.1 | Microsoft Visual C++ Runtime |
| PySide6 / shiboken6 | `MSVCP140.dll`, `MSVCP140_1.dll`, `MSVCP140_2.dll`, `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` en sus carpetas | 14.44.35211.0 | Microsoft Visual C++ Runtime |
| pikepdf/qpdf | `pikepdf.libs/msvcp140-*.dll` | 14.51.36247.0 | Microsoft Visual C++ Runtime; aviso incluido de pikepdf |

Términos oficiales: [Microsoft Visual C++ Runtime 2015-2022](https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/) y
[redistribución de archivos Visual C++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files).

## Exclusiones verificadas

- pytest, pytest-qt, setuptools, pip y los módulos Python de PyInstaller son
  herramientas de build/prueba y no se redistribuyen. Solo queda el bootloader
  de PyInstaller dentro de `ProtectorPDF.exe`.
- PySide6-WebEngine no se empaqueta.
- No se incluye instalador, firma digital ni cliente de red propio.

Este inventario técnico no es asesoría jurídica. Los textos y enlaces de los
titulares son la fuente autoritativa de sus términos.
