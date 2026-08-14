# CE3X · Datos Locales

Complemento para **CE3X v2.3** (Certificación Energética de Edificios Existentes) que rellena la pestaña de *Datos administrativos* desde un fichero JSON local, sin conexión a internet ni cuenta de usuario.

Soporta **varios perfiles** (autónomo, distintas empresas, colegiados...) accesibles directamente desde el menú, y trae un editor con altas, bajas y modificaciones.

---

## Por qué

CE3X permite instalar complementos, y el más conocido para autorrellenar los datos del certificador descarga el perfil de un servidor remoto: exige nombre de usuario, hace una petición HTTP en cada uso y falla si no hay red.

Para un dato que no cambia nunca y que es estrictamente personal, eso sobra. Este complemento hace lo mismo leyendo un JSON del disco.

| | Complemento remoto | Este |
|---|---|---|
| Origen de los datos | `GET http://…/perfilCexSinAutenticar…` | JSON local |
| Requiere cuenta | Sí | No |
| Funciona sin red | No | Sí |
| Varios perfiles | No | Sí |
| Datos personales salen del equipo | Sí | No |

---

## Instalación

### Con el instalador (recomendado)

Descarga el `.exe` de la [última release](../../releases/latest) y ejecútalo. Detecta la carpeta de CE3X leyendo el registro y copia los ficheros en `Plugins\`.

### Manual

Copia estos dos ficheros a la carpeta `Plugins` de tu instalación de CE3X (normalmente `C:\Program Files (x86)\CEXv2.3\Plugins`):

```
plugin/DatosLocales.py
plugin/datosAdministrativos.ejemplo.json
```

Si ya tenías una versión anterior, borra también `Plugins\DatosLocales.pyc`.

El fichero de ejemplo es solo una referencia del formato: tus datos reales se guardan en `%APPDATA%` (ver más abajo).

---

## Uso

Al arrancar CE3X aparece el menú **Complementos → DatosLocales**:

```
Complementos
└── DatosLocales
    ├── Autónomo              ← un clic y los datos están puestos
    ├── Estudio Ejemplo S.L.
    ├── ─────────────
    └── Editar mis datos...
```

- **Perfil** → vuelca sus datos en la pestaña *Datos administrativos* del certificado abierto.
- **Editar mis datos...** → editor de perfiles: *Nuevo*, *Duplicar*, *Borrar*, *Guardar*.

El menú se regenera solo al guardar en el editor. En el camino normal no aparece ningún diálogo de confirmación: si no hay errores, no molesta.

### Fichero de datos

Los perfiles se guardan en la carpeta de datos del usuario, que no necesita permisos de administrador:

```
%APPDATA%\CE3X-DatosLocales\datosAdministrativos.json
```

es decir, algo como `C:\Users\TuUsuario\AppData\Roaming\CE3X-DatosLocales\`.

Puedes forzar otra ruta con la variable de entorno `CE3X_DATOS_ADMIN`, útil para compartir la configuración entre equipos o tenerla en una unidad de red.

Si vienes de una versión anterior que guardaba el JSON dentro de `Plugins\` o en la carpeta del usuario, se copia automáticamente a la nueva ubicación la primera vez. El fichero antiguo se deja donde estaba.

Formato (UTF-8):

```json
{
    "perfiles": [
        {
            "alias": "Autónomo",
            "nombre": "Ana",
            "apellidos": "García López",
            "nif": "12345678Z",
            "esAutonomo": true,
            "razonSocial": "",
            "cif": "",
            "direccion": "Calle Mayor, 1",
            "provincia": "Madrid",
            "localidad": "Madrid",
            "codigoPostal": "28001",
            "telefono": "600000000",
            "email": "ana.garcia@ejemplo.es",
            "titulacion": "Arquitecto Técnico"
        }
    ]
}
```

- `alias` es solo la etiqueta del menú. Si lo dejas vacío se usa *nombre + apellidos*.
- Con `esAutonomo: true`, la razón social se rellena con el nombre completo y el CIF con el NIF.
- `provincia` debe coincidir con una de la lista de CE3X. El editor la ofrece en un desplegable poblado con las provincias reales del programa; si aun así no encaja, el complemento avisa y enumera las válidas.
- También se acepta un objeto plano sin la clave `perfiles` (un solo perfil); se migra al guardar.

### Correspondencia de campos

| Campo del JSON | Control de CE3X |
|---|---|
| `nombre` + `apellidos` | `certificadorAutor` |
| `nif` | `nifCertificadorCuadro` |
| `razonSocial` | `certificadorEmpresa` |
| `cif` | `cifCertificadorCuadro` |
| `direccion` | `direccionCertificador` |
| `provincia` | `provinciaCertificadorChoice` |
| `localidad` | `localidadCertificadorCuadro` |
| `codigoPostal` | `codigoPostalCertificadorCuadro` |
| `telefono` | `certificadorTelefono` |
| `email` | `certificadorMail` |
| `titulacion` | `titulacionHabilitanteCuadro` |

---

## Cómo funciona el sistema de complementos de CE3X

CE3X 2.3 corre sobre **Python 2.7 + wxPython 2.8** y sus módulos están compilados a `.pyd`, así que el API de complementos no está documentada. Estas son las reglas, deducidas de `wxFrame1.pyd`:

1. `wxFrame1.cogerPlugins()` lista la carpeta `Plugins`, se queda con el nombre base de cada fichero y añade la carpeta a `sys.path`.
2. `wxFrame1._init_coll_menuComplementos_Items()` importa cada módulo y llama a **`modulo.create(parent)`**, donde `parent` es la ventana principal.
3. Del objeto devuelto lee el atributo **`menuit`** y lo cuelga como submenú:
   `parent.AppendMenu(id=wx.NewId(), text=<nombre del fichero>, submenu=obj.menuit, help=...)`

O sea, el contrato mínimo es:

```python
import wx

class menuItem:
    def __init__(self, parent):
        self.parent = parent
        self.menuit = wx.Menu()
        identificador = wx.NewId()
        # wxPython 2.8: Append usa estos keywords
        self.menuit.Append(help=u"", id=identificador, kind=wx.ITEM_NORMAL, text=u"Hola")
        self.parent.Bind(wx.EVT_MENU, self.onHola, id=identificador)

    def onHola(self, event):
        wx.MessageBox(u"Hola")

def create(parent):          # <- punto de entrada obligatorio
    return menuItem(parent)
```

Detalles que cuestan un rato descubrir:

- El **título del menú es el nombre del fichero**, no una variable del módulo. `DatosLocales.py` → menú *DatosLocales*.
- La carpeta es `Plugins` con mayúscula inicial.
- Los controles del certificado cuelgan de `parent.panelDatosAdministrativos`, `parent.panelDatosGenerales`, etc.
- CE3X inyecta `_` (gettext) en los builtins, pero conviene no darlo por hecho.
- Un fallo en `create()` no tumba CE3X: lo captura, lo registra con `logging` y muestra un `MessageBox`.
- Python 2 compila el `.py` a `.pyc` en el primer import y lo invalida comparando el **mtime exacto** del fuente, no si es más reciente. Por eso el instalador borra el `.pyc` al actualizar.

---

## Desarrollo

### Pruebas

No hacen falta ni CE3X ni wxPython: la suite simula wx y los controles del panel.

```bash
python3 tests/test_plugin.py
```

Cubre el volcado con y sin `esAutonomo`, el emparejamiento de provincia ignorando mayúsculas, el CRUD completo, que guardar no cierre la ventana, que el menú se regenere sin duplicar manejadores, y la migración del formato antiguo.

El plugin está escrito para funcionar en **Python 2.7 y 3.x** a la vez. En producción lo ejecuta el Python 2.7 embebido de CE3X; la compatibilidad con 3.x es lo que permite probarlo en cualquier máquina.

### Generar el instalador

Necesitas [Inno Setup 6](https://jrsoftware.org/isdl.php).

**Windows**

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\ComplementoDatosLocales.iss
```

**Linux o macOS (con Wine)**

```bash
curl -fLO https://github.com/jrsoftware/issrc/releases/download/is-6_2_2/innosetup-6.2.2.exe
WINEPREFIX=~/.wine-inno wine innosetup-6.2.2.exe /VERYSILENT /SUPPRESSMSGBOXES
./build.sh
```

`build.sh` lanza las pruebas y deja el `.exe` en `dist/`. Usa el prefijo `~/.wine-inno` por defecto; cámbialo con la variable `WINEPREFIX`.

Para subir la versión, tócala en `plugin/DatosLocales.py` (`versionComplemento`) y en `installer/ComplementoDatosLocales.iss` (`VersionComplemento`).

### Qué hace el instalador

`DefaultDirName={code:GetDirName}` con una función Pascal que busca CE3X en:

1. `HKLM\...\Uninstall\{7139BD7B-FC0B-435F-8E79-63D7CCDA2BA8}_is1` → `Inno Setup: App Path`
2. La misma clave → `InstallLocation`
3. `C:\Program Files (x86)\CEXv2.3`

Valida que la carpeta contenga `wxFrame1.pyd` y avisa si eliges otra cosa. Deja entrada de desinstalación propia.

---

## Compatibilidad

Probado con **CE3X v2.3** sobre Windows y sobre Linux con Wine. Debería valer para cualquier 2.x que mantenga `panelDatosAdministrativos`; si algún control cambia de nombre, el complemento no peta: avisa de qué campos no ha podido aplicar.

---

## Licencia

[MIT](LICENSE).

Proyecto independiente, sin relación con el IDAE, el Ministerio ni los autores de CE3X. Los nombres de los controles se han obtenido analizando la propia aplicación con el único fin de lograr la interoperabilidad de un programa creado de forma independiente, tal y como contempla el art. 100.5 de la Ley de Propiedad Intelectual. No se distribuye aquí ningún binario de terceros.
