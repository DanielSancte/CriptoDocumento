# Licencias de terceros

Esta lista corresponde a los componentes de ejecución incluidos por `packaging/pdf-protector.spec` en la distribución `onedir`. Las herramientas que solo ejecutan pruebas o análisis no se redistribuyen, salvo el bootloader indicado de PyInstaller.

| Componente | Versión | Licencia | Enlace oficial |
| --- | ---: | --- | --- |
| CPython | 3.12.2 | Python Software Foundation License Version 2 (PSF-2.0) | [Licencias de Python](https://docs.python.org/3.12/license.html) |
| PySide6 / Qt for Python | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Licencias de Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html) |
| PySide6-Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Qt for Python](https://doc.qt.io/qtforpython-6/) |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Shiboken](https://doc.qt.io/qtforpython-6/shiboken6/) |
| pikepdf | 10.18.2 | MPL-2.0 | [pikepdf](https://pikepdf.readthedocs.io/) |
| qpdf (biblioteca nativa incluida por pikepdf) | 12.4.2 | Apache-2.0 | [Licencia de qpdf](https://qpdf.readthedocs.io/en/stable/license.html) |
| Pillow | 13.0.0 | MIT-CMU | [Pillow](https://python-pillow.github.io/) |
| lxml | 6.1.3 | BSD-3-Clause | [lxml](https://lxml.de/) |
| libxml2 (integrada en lxml) | 2.11.9 | MIT | [libxml2](https://gitlab.gnome.org/GNOME/libxml2/-/blob/master/Copyright) |
| libxslt (integrada en lxml) | 1.1.45 | MIT | [libxslt](https://gitlab.gnome.org/GNOME/libxslt/-/blob/master/Copyright) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [Python Packaging](https://packaging.pypa.io/) |
| typing-extensions | 4.16.0 | PSF-2.0 | [typing_extensions](https://github.com/python/typing_extensions) |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later con excepción especial para distribuir aplicaciones resultantes | [Licencia de PyInstaller](https://pyinstaller.org/en/stable/license.html) |
| Microsoft Visual C++ Runtime | 14.51.36247.0 | Microsoft Software License Terms | [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) |

Pillow incorpora bibliotecas de códecs bajo sus licencias respectivas; su archivo de licencia oficial recopila los avisos aplicables: [Pillow LICENSE](https://github.com/python-pillow/Pillow/blob/13.0.0/LICENSE).

Qt se redistribuye como bibliotecas dinámicas para conservar las condiciones de la LGPL. La distribución debe mantener disponibles estos avisos y las condiciones de licencia correspondientes. Este documento es un inventario técnico, no asesoría jurídica.
