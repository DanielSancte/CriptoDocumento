# Licencias de terceros

Este inventario corresponde a la distribución Windows x64 concreta generada
por `scripts/build.ps1` con `requirements.lock`. Se contrastaron el TOC de
PyInstaller, los archivos finales, los metadatos de los wheels, las versiones
informadas en ejecución y los avisos que acompañan a las dependencias.

Cuando una biblioteca está enlazada dentro de otro binario y este no expone
una versión propia, se indica **incluida; versión no declarada por separado**.
No se infieren versiones desde otro wheel o desde el equipo de desarrollo.

Los avisos completos que el wheel de pikepdf sí incorpora al artefacto están
en `_internal/pikepdf-10.18.2.dist-info/licenses/`.

## Componentes Python y Qt redistribuidos

| Componente | Versión comprobada | Licencia o expresión declarada | Fuente autoritativa o upstream |
| --- | ---: | --- | --- |
| CPython y biblioteca estándar | 3.12.2 x64 | Python Software Foundation License Version 2 (PSF-2.0), con los avisos de terceros de CPython | [Historia y licencia de Python 3.12](https://docs.python.org/3.12/license.html) |
| PySide6 / Qt for Python y PySide6-Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Licencias de Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html) |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Shiboken](https://doc.qt.io/qtforpython-6/shiboken6/) |
| pikepdf | 10.18.2 | MPL-2.0 | Aviso incluido `pikepdf-10.18.2.dist-info/licenses/LICENSE.txt` y [fuente de pikepdf](https://github.com/pikepdf/pikepdf) |
| Pillow | 13.0.0 | MIT-CMU | [LICENSE de Pillow 13.0.0](https://github.com/python-pillow/Pillow/blob/13.0.0/LICENSE) |
| lxml | 6.1.3 | BSD-3-Clause, más las bibliotecas y recursos detallados abajo | [Licencias de lxml 6.1.3](https://github.com/lxml/lxml/tree/lxml-6.1.3/doc/licenses) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [Licencias de packaging 26.3](https://github.com/pypa/packaging/tree/26.3/LICENSES) |
| typing-extensions | 4.16.0 | PSF-2.0 | [LICENSE de typing_extensions 4.16.0](https://github.com/python/typing_extensions/blob/4.16.0/LICENSE) |
| Bootloader de PyInstaller | 6.22.3 | GPL-2.0-or-later con la excepción especial de PyInstaller para distribuir las aplicaciones resultantes | [Licencia de PyInstaller](https://pyinstaller.org/en/stable/license.html) |

El artefacto contiene únicamente los módulos Qt 6.12 `Core`, `Gui`, `Network`,
`Svg` y `Widgets`, sus bindings, traducciones y estos grupos de plugins:
plataforma (`qwindows`, `qoffscreen`, `qminimal`, `qdirect2d`), formatos de
imagen, TLS, información de red, estilo, iconos y entrada genérica. Son
bibliotecas dinámicas Qt sin modificación.

### Código de terceros incorporado en los módulos Qt presentes

La tabla siguiente se limita a los módulos y plugins que aparecen en el
artefacto final. Los nombres, versiones y etiquetas de licencia provienen de
la página oficial [Third-Party Code Used in Qt 6.12](https://doc.qt.io/qt-6/licenses-used-in-qt.html),
de [Qt Core 6.12](https://doc.qt.io/qt-6/qtcore-index.html),
[Qt GUI 6.12](https://doc.qt.io/qt-6/qtgui-index.html) y
[Qt Image Formats](https://doc.qt.io/qt-6/qtimageformats-index.html). Las
etiquetas «dominio público» se conservan tal como las publica Qt; no se les
asigna una expresión SPDX inventada.

| Módulo / componente incorporado | Versión atribuida por Qt 6.12 | Licencia o estado publicado por Qt |
| --- | ---: | --- |
| Qt Core — Apache Tika MimeType Definitions | `c29724782854bb5a319f4a1940d0828a58ace3f9` | Apache-2.0 |
| Qt Core — BLAKE2 reference implementation | `ed1974ea83433eba7b2d95c5dcd9ac33cb847913` | CC0-1.0 OR Apache-2.0 |
| Qt Core — zlib | 1.3.2 | Zlib |
| Qt Core — Easing Equations de Robert Penner | Incluida; versión no declarada por separado | BSD-3-Clause |
| Qt Core — rutinas de conversión binario/decimal (Ryu) | 3.4.0 | BSD-3-Clause |
| Qt Core — MD4 | Incluida; versión no declarada por separado | Dominio público según la atribución de Qt |
| Qt Core — MD5 | Incluida; versión no declarada por separado | Dominio público según la atribución de Qt |
| Qt Core — PCRE2 | 10.48 | BSD-3-Clause con la excepción de paquetes binarios de PCRE2 |
| Qt Core — SLJIT de PCRE2 | 10.48 | BSD-2-Clause |
| Qt Core — SHA-1 | Incluida; versión no declarada por separado | Dominio público según la atribución de Qt |
| Qt Core — SHA-3 Keccak | 3.2 | CC0-1.0 |
| Qt Core — SHA-3 `brg_endian` | 1.0.0 | BSD-2-Clause |
| Qt Core — SHA-384/SHA-512 | Incluida; versión no declarada por separado | BSD-3-Clause |
| Qt Core — SipHash | Incluida; versión no declarada por separado | CC0-1.0 |
| Qt Core — TinyCBOR | 7.0 | MIT |
| Qt Core — Unicode Character Database | Incluida; versión no declarada por el binario | Unicode Data Files and Software License (2016) |
| Qt Core — Unicode CLDR | v48.2 | Unicode License v3 |
| Qt Core — `tl::expected` | `41d3e1f48d682992a2230b2a715bca38b848b269` | CC0-1.0 |
| Qt GUI — Adobe Glyph List For New Fonts | 1.7 | BSD-3-Clause |
| Qt GUI — rasterizador antialiasing de FreeType 2 | Incluida; versión no declarada por separado | FreeType License (FTL) OR GPL-2.0-only |
| Qt GUI — D3D12 Memory Allocator | v3.1.0 | MIT |
| Qt GUI — generador mipmap para D3D12 | `0aa79bad78992da0b6a8279ddb9002c1753cb849` | MIT |
| Qt GUI — DejaVu Fonts | 2.37 | Bitstream Vera Font License |
| Qt GUI — Emoji Segmenter | 0.4.0 | Apache-2.0 |
| Qt GUI — FreeType 2 y soporte BDF/PCF/zlib | 2.14.3 | FTL OR GPL-2.0-only; MIT para BDF; MIT y variante MIT Open Group para PCF; Zlib para la parte zlib |
| Qt GUI — HarfBuzz-NG | 14.5.0 | MIT (variante histórica publicada por Qt) |
| Qt GUI / plugin `qjpeg` — libjpeg-turbo | 3.2.0 | IJG License AND BSD-3-Clause, según la atribución del binario Qt |
| Qt GUI — libpng | 1.6.58 | Libpng License AND PNG Reference Library License 2.0 |
| Qt GUI — MD4C | Incluida; el binario no declara una versión independiente | MIT |
| Qt GUI — cabeceras OpenGL ES 2 | Revision 27673 | MIT |
| Qt GUI — cabeceras OpenGL | Revision 27684 | MIT |
| Qt GUI — Pixman | 0.17.12 | MIT |
| Qt GUI — Smooth Scaling Algorithm | Incluida; versión no declarada por separado | BSD-2-Clause AND Imlib2 License |
| Qt GUI — Vulkan API Registry | 1.4.308 | Apache-2.0 OR MIT |
| Qt GUI — Vulkan Memory Allocator | 3.3.0 | MIT |
| Qt GUI — WebGradients | Incluida; versión no declarada por separado | MIT |
| Qt GUI — Wintab API | Incluida; versión no declarada por separado | LCS-Telegraphics License |
| Qt GUI — perfil de color sRGB ICC | Incluida; versión no declarada por separado | International Color Consortium License |
| Qt Image Formats / plugin `qtiff` — LibTIFF | 4.7.2 | Libtiff License |
| Qt Image Formats / plugin `qwebp` — libwebp | 1.6.0 | BSD-3-Clause |
| Qt Network — Public Suffix List | `2026-05-14_08-35-31_UTC` | MPL-2.0 |
| Qt Network — libpsl | `664f3dc85259ec65e30248a61fa1c45b7b0e4c3f` | BSD-3-Clause |

Qt Network aporta `qopensslbackend.dll`, que carga OpenSSL dinámicamente; no
hay otra copia de OpenSSL incorporada estáticamente en ese plugin. Las DLL
`libcrypto-3.dll` y `libssl-3.dll` presentes son las de CPython y se registran
en su propia sección. `Qt6Core.dll` importa `icuuc.dll` del sistema operativo,
pero el artefacto no redistribuye una DLL ni datos ICU.

## Proveedor PDF: pikepdf y el wheel de qpdf

La fuente primaria de esta sección es el aviso incluido
`third-party-licenses/README.md` de pikepdf 10.18.2.

| Componente | Versión comprobada | Forma incluida | Licencia | Aviso incluido |
| --- | ---: | --- | --- | --- |
| qpdf | 12.4.2 | `pikepdf.libs/qpdf30-*.dll`; versión informada por `pikepdf.__libqpdf_version__` | Apache-2.0 | `qpdf.txt` |
| libjpeg-turbo usado por qpdf | Incluida; versión no declarada por separado | Enlace estático dentro de `qpdf30-*.dll` | IJG + BSD-3-Clause + Zlib | `libjpeg-turbo.txt` y `libjpeg-turbo-README.ijg.txt` |
| OpenSSL usado por qpdf | Incluida; versión no declarada por separado | Enlace estático dentro de `qpdf30-*.dll` | Apache-2.0 | `openssl.txt` |
| zlib usado por qpdf | Incluida; versión no declarada por separado | Enlace estático dentro de `qpdf30-*.dll` | Zlib | `zlib.txt` |
| Microsoft Visual C++ Standard Library usada por qpdf | 14.51.36247.0 | `pikepdf.libs/msvcp140-*.dll` | Microsoft Visual Studio 2022 Runtime Terms | `microsoft-visual-cpp-runtime.txt` |

El aviso menciona OpenSSL 3.6.0 y zlib 1.3.1 únicamente como ejemplos de una
versión anterior y advierte que no garantizan el contenido de otro wheel. Por
eso no se atribuyen esas versiones a pikepdf 10.18.2.

### Código y datos PDF/A incluidos por pikepdf

| Componente | Versión | Licencia | Aviso incluido o fuente |
| --- | ---: | --- | --- |
| Perfil sRGB ICC de `icc-profiles-free` (`sRGB.icc`) | Incluida; versión no declarada por separado | Zlib | `sRGB-icc-profile.txt` |
| Reglas veraPDF (`verapdf_rules.json`) | Incluida; convertida por pikepdf de XML a JSON | CC-BY-4.0 | `CC-BY-4.0-veraPDF.txt` |
| Tabla Latin encoding derivada de pdfminer.six (`_latin_enc.py`) | Incluida; versión no declarada por separado | MIT | `pdfminer.six.txt` |
| Esquemas, disposiciones y propiedades XMP de pikepdf PDF/A | 10.18.2 | MPL-2.0 salvo los datos atribuidos en las filas anteriores | `LICENSE.txt` de pikepdf |

`GPL-3.0.txt` y `GCC-exception-3.1.txt` aparecen en los avisos porque el mismo
metadato cubre wheels de otras plataformas. El README de pikepdf los limita al
runtime GCC de musllinux; ese runtime no existe en este artefacto Windows.

## Códecs nativos del wheel de Pillow

PyInstaller incluye `_imaging`, `_imagingcms`, `_webp`, `_avif` e
`_imagingtk`. Las versiones se comprobaron con `PIL.features` y con los
encabezados del `LICENSE` de Pillow 13.0.0 instalado por el lock.

| Componente incorporado por Pillow | Versión | Licencia declarada en el aviso upstream de Pillow |
| --- | ---: | --- |
| Brotli | 1.2.0 | MIT |
| FreeType | 2.14.3 | FTL OR GPL-2.0-only, con las partes auxiliares indicadas por el mismo aviso |
| HarfBuzz | 14.5.0 | Old MIT |
| Little CMS (lcms2) | 2.19.1 | MIT |
| libavif | 1.4.2 | BSD-2-Clause, más los avisos por archivo de dav1d, IJG, gdk-pixbuf, Apache-2.0 y libyuv incluidos en su sección del `LICENSE` |
| libjpeg-turbo | 3.2.0 | IJG + BSD-3-Clause + Zlib |
| libpng | 1.6.58 | PNG Reference Library License 2.0 |
| libwebp | 1.6.0 | BSD-3-Clause |
| OpenJPEG | 2.5.4 | BSD-2-Clause |
| LibTIFF | 4.7.2 | Libtiff License y avisos incorporados indicados por Pillow |
| liblzma / XZ Utils | 5.8.4 | 0BSD para `liblzma`; el aviso enumera otras licencias para otros archivos de XZ |
| zlib-ng | 2.3.3 (`1.3.1.zlib-ng` en modo compatible) | Zlib |

`PIL.features` informa Tcl/Tk 8.6 al inspeccionar el entorno de build, pero la
distribución final no contiene DLL de Tcl/Tk; `_imagingtk` por sí solo no
redistribuye ese runtime.

## lxml: bibliotecas y recursos incorporados

El `LICENSES.txt` de lxml 6.1.3 declara que el wheel binario incorpora estas
bibliotecas. Las versiones que el runtime no expone se mantienen sin inferir.

| Componente | Versión comprobada | Licencia declarada por lxml |
| --- | ---: | --- |
| libxml2 | 2.11.9 | MIT |
| libxslt | 1.1.45 | MIT |
| libexslt | Incluida; versión no declarada por separado | MIT |
| zlib enlazada por lxml | Incluida; versión no declarada por separado | Zlib |
| iconv enlazada por lxml | Incluida; versión no declarada por separado | LGPL-2.1, tal como la declara el aviso de lxml |

Los recursos Schematron que sí quedan bajo
`_internal/lxml/isoschematron/resources/` son:

| Recurso | Versión | Licencia / aviso |
| --- | ---: | --- |
| `rng/iso-schematron.rng` | Revisión incluida por lxml 6.1.3 | Aviso permisivo propio de ISO/IEC 2015 embebido en el archivo; exige conservar el aviso y marcar las modificaciones |
| `iso_abstract_expand.xsl` | Revisión incluida por lxml 6.1.3 | MIT, texto embebido en el archivo |
| `iso_dsdl_include.xsl` | Revisión incluida por lxml 6.1.3 | Zlib, texto embebido en el archivo |
| `iso_schematron_message.xsl` | Revisión incluida por lxml 6.1.3 | Zlib, texto embebido en el archivo |
| `iso_schematron_skeleton_for_xslt1.xsl` | Revisión incluida por lxml 6.1.3 | Zlib, texto embebido en el archivo |
| `iso_svrl_for_xslt1.xsl` | Revisión incluida por lxml 6.1.3 | Zlib, texto embebido en el archivo |
| `readme.txt` | Revisión incluida por lxml 6.1.3 | Documento descriptivo del mismo conjunto Schematron; no declara código ni licencia independiente |

Los dos recursos que `LICENSES.txt` de lxml identifica expresamente como
**sin licencia**, `RNG2Schtrn.xsl` y `XSD2Schtrn.xsl`, no son necesarios para
el flujo de pikepdf y se excluyen durante `Analysis`; la prueba del paquete
exige que no aparezcan.

## Dependencias nativas del runtime CPython

| Componente | Versión comprobada | Evidencia en el artefacto | Licencia o términos |
| --- | ---: | --- | --- |
| libmpdec | 2.5.1 | `_decimal.pyd`; versión informada por `decimal.__libmpdec_version__` | BSD-2-Clause; [aviso de libmpdec en CPython 3.12](https://docs.python.org/3.12/license.html#libmpdec) |
| OpenSSL de CPython | 3.0.13 | `libcrypto-3.dll`, `libssl-3.dll`, `_ssl.pyd`, `_hashlib.pyd` | Apache-2.0; [aviso de OpenSSL en CPython](https://docs.python.org/3.12/license.html#openssl) |
| Expat | 2.5.0 | `pyexpat.pyd`, `_elementtree.pyd`; `pyexpat.EXPAT_VERSION` | MIT; [aviso de Expat en CPython](https://docs.python.org/3.12/license.html#expat) |
| libffi | Incluida; versión de producto no declarada | `libffi-8.dll`, `_ctypes.pyd` | MIT; [LICENSE upstream de libffi](https://github.com/libffi/libffi/blob/master/LICENSE) |
| bzip2 | Incluida; versión no declarada por separado | `_bz2.pyd` | Licencia permisiva bzip2; [aviso de bzip2 en CPython](https://docs.python.org/3.12/license.html#bzip2) |
| liblzma / XZ de CPython | Incluida; versión no declarada por separado | `_lzma.pyd` | Términos de XZ Utils publicados en [avisos de CPython 3.12](https://docs.python.org/3.12/license.html) |
| Unicode Character Database de CPython | 15.0.0 | `unicodedata.pyd`; `unicodedata.unidata_version` | Unicode License v3; [Unicode Data Files and Software License](https://www.unicode.org/license.txt) |

## Microsoft Visual C++ Runtime

Los wheels se compilaron con toolsets distintos; no se presenta estas copias
como una sola versión.

| Proveedor | Archivos | Versión de archivo | Términos |
| --- | --- | ---: | --- |
| CPython 3.12.2 | `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` | 14.38.33126.1 | Microsoft Visual C++ Runtime |
| PySide6 / shiboken6 | `MSVCP140.dll`, `MSVCP140_1.dll`, `MSVCP140_2.dll`, `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` en sus carpetas | 14.44.35211.0 | Microsoft Visual C++ Runtime |
| pikepdf/qpdf | `pikepdf.libs/msvcp140-*.dll` | 14.51.36247.0 | Microsoft Visual C++ Runtime; aviso incluido de pikepdf |

Fuentes oficiales: [Microsoft Visual C++ Runtime 2015-2022](https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/)
y [redistribución de archivos Visual C++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files).

## Exclusiones comprobadas

- Qt PDF/PdfWidgets y con ellos PDFium, Chromium y las demás cargas de Qt PDF
  no se empaquetan. Tampoco se incluyen Qt Virtual Keyboard, QML, Quick, Qt
  OpenGL ni `opengl32sw.dll` (Mesa software OpenGL).
- PySide6-Addons, PySide6-Pdf y PySide6-WebEngine están instalados únicamente
  en el entorno fijado por el metapaquete PySide6, pero ninguno de sus módulos
  se redistribuye en el artefacto final.
- `RNG2Schtrn.xsl` y `XSD2Schtrn.xsl`, identificados por lxml como sin
  licencia, están ausentes.
- pytest, pytest-qt, setuptools, pip y los módulos Python de PyInstaller son
  herramientas de build/prueba y no se redistribuyen; solo queda el bootloader
  de PyInstaller dentro de `ProtectorPDF.exe`.
- No se incluye instalador, firma digital ni cliente de red propio.

Este inventario técnico no es asesoría jurídica. Los textos y enlaces de los
titulares son la fuente autoritativa de sus términos.
