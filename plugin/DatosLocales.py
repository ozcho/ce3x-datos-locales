# -*- coding: utf-8 -*-
"""
Plugin CE3X: rellena el panel de datos administrativos desde perfiles locales.

CE3X (Python 2.7 + wxPython 2.8) importa los modulos de <CEXv2.3>/Plugins/,
llama a create(parent) y cuelga del menu el wx.Menu del atributo `menuit`.

Formato del JSON:
    {"perfiles": [ {"alias": "...", "nombre": "...", ...}, ... ]}
Tambien se acepta un unico objeto plano (formato antiguo de un solo perfil).
"""

import copy
import io
import json
import logging
import os
import shutil

import wx

try:
    import __builtin__ as builtins  # Python 2 (CE3X)
except ImportError:
    import builtins

try:
    cadena = unicode  # noqa: F821
except NameError:
    cadena = str

versionComplemento = "1.1.0"

NOMBRE_JSON = "datosAdministrativos.json"
CARPETA_DATOS = "CE3X-DatosLocales"
VAR_ENTORNO = "CE3X_DATOS_ADMIN"

# campo del perfil -> etiqueta del formulario
CAMPOS = [
    ("alias", u"Alias del perfil"),
    ("nombre", u"Nombre"),
    ("apellidos", u"Apellidos"),
    ("nif", u"NIF"),
    ("razonSocial", u"Razón social"),
    ("cif", u"CIF"),
    ("direccion", u"Dirección"),
    ("provincia", u"Provincia"),
    ("localidad", u"Localidad"),
    ("codigoPostal", u"Código postal"),
    ("telefono", u"Teléfono"),
    ("email", u"Email"),
    ("titulacion", u"Titulación habilitante"),
]

# campo del perfil -> (atributo del panel de CE3X, metodo wx)
MAPEO = [
    ("nif", "nifCertificadorCuadro", "SetValue"),
    ("razonSocial", "certificadorEmpresa", "SetValue"),
    ("cif", "cifCertificadorCuadro", "SetValue"),
    ("direccion", "direccionCertificador", "SetValue"),
    ("provincia", "provinciaCertificadorChoice", "SetStringSelection"),
    ("localidad", "localidadCertificadorCuadro", "SetValue"),
    ("codigoPostal", "codigoPostalCertificadorCuadro", "SetValue"),
    ("telefono", "certificadorTelefono", "SetValue"),
    ("email", "certificadorMail", "SetValue"),
    ("titulacion", "titulacionHabilitanteCuadro", "SetValue"),
]


def _t(texto):
    """Traduccion opcional: CE3X inyecta `_` en builtins, pero puede no estar."""
    traductor = getattr(builtins, "_", None)
    return traductor(texto) if callable(traductor) else texto


def perfilVacio():
    perfil = dict((clave, u"") for clave, _etiqueta in CAMPOS)
    perfil["esAutonomo"] = True
    return perfil


def _texto(datos, clave):
    """Devuelve el valor como texto; nunca None (SetValue no lo admite)."""
    valor = datos.get(clave, u"")
    if valor is None:
        return u""
    if isinstance(valor, bytes):
        return valor.decode("utf-8", "replace")
    return cadena(valor)


def etiquetaPerfil(perfil, indice):
    if perfil.get("alias"):
        return perfil["alias"]
    nombre = (u"%s %s" % (perfil.get("nombre", u""), perfil.get("apellidos", u""))).strip()
    return nombre or (u"Perfil %d" % (indice + 1))


# --------------------------------------------------------------------------
# persistencia
# --------------------------------------------------------------------------
def directorioDatos():
    """%APPDATA%\\CE3X-DatosLocales; el HOME como respaldo si no hay APPDATA."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, CARPETA_DATOS)


def _rutasHeredadas():
    """Ubicaciones de versiones anteriores, hoy de solo lectura para el usuario."""
    return [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), NOMBRE_JSON),
        os.path.join(os.path.expanduser("~"), NOMBRE_JSON),
    ]


def _aseguraDirectorio(ruta):
    carpeta = os.path.dirname(ruta)
    if carpeta and not os.path.isdir(carpeta):
        os.makedirs(carpeta)


def rutaConfiguracion():
    """Ruta de lectura y escritura. Migra la config de versiones anteriores."""
    if os.environ.get(VAR_ENTORNO):
        return os.environ[VAR_ENTORNO]

    destino = os.path.join(directorioDatos(), NOMBRE_JSON)
    if os.path.isfile(destino):
        return destino

    for heredada in _rutasHeredadas():
        if not os.path.isfile(heredada):
            continue
        try:
            _aseguraDirectorio(destino)
            shutil.copyfile(heredada, destino)
        except (IOError, OSError):
            logging.warning("DatosLocales: no se pudo migrar %s", heredada, exc_info=True)
            return heredada
        logging.info("DatosLocales: configuracion migrada de %s a %s", heredada, destino)
        break
    return destino


def normalizarPerfiles(datos):
    """Acepta {'perfiles': [...]}, una lista, o un objeto plano (formato antiguo)."""
    if isinstance(datos, dict):
        crudos = datos["perfiles"] if "perfiles" in datos else [datos]
    elif isinstance(datos, list):
        crudos = datos
    else:
        raise ValueError("Se esperaba un objeto o una lista de perfiles.")
    if not isinstance(crudos, list):
        raise ValueError("La clave 'perfiles' debe ser una lista.")

    perfiles = []
    for crudo in crudos:
        if not isinstance(crudo, dict):
            continue
        perfil = perfilVacio()
        for clave, _etiqueta in CAMPOS:
            perfil[clave] = _texto(crudo, clave)
        perfil["esAutonomo"] = bool(crudo.get("esAutonomo"))
        perfiles.append(perfil)
    return perfiles


def cargarPerfiles(ruta):
    if not os.path.isfile(ruta):
        return []
    with io.open(ruta, "r", encoding="utf-8") as fichero:
        return normalizarPerfiles(json.load(fichero))


def guardarPerfiles(ruta, perfiles):
    texto = json.dumps({"perfiles": perfiles}, indent=4, ensure_ascii=False, sort_keys=True)
    if isinstance(texto, bytes):
        texto = texto.decode("utf-8")
    _aseguraDirectorio(ruta)
    with io.open(ruta, "w", encoding="utf-8") as fichero:
        fichero.write(texto)


# --------------------------------------------------------------------------
# volcado al panel de CE3X
# --------------------------------------------------------------------------
def construyeValores(perfil):
    """Aplica la regla de autonomo y devuelve {clave: texto} listo para volcar."""
    valores = dict((clave, _texto(perfil, clave)) for clave, _etiqueta in CAMPOS)
    valores["autor"] = (_texto(perfil, "nombre") + u" " + _texto(perfil, "apellidos")).strip()
    if perfil.get("esAutonomo"):
        valores["razonSocial"] = valores["autor"]
        valores["cif"] = valores["nif"]
    return valores


def _asignaChoice(control, texto):
    """SetStringSelection es sensible a mayusculas/acentos: reintenta sin distinguir."""
    if control.SetStringSelection(texto):
        return True
    objetivo = texto.strip().lower()
    for indice in range(control.GetCount()):
        if control.GetString(indice).strip().lower() == objetivo:
            control.SetSelection(indice)
            return True
    return False


def volcarEnPanel(panel, valores):
    """Escribe en los controles. Devuelve la lista de campos no aplicados."""
    fallos = []
    control = getattr(panel, "certificadorAutor", None)
    if control is None:
        fallos.append("certificadorAutor")
    else:
        control.SetValue(valores["autor"])

    for clave, atributo, metodo in MAPEO:
        control = getattr(panel, atributo, None)
        if control is None:
            fallos.append(atributo)
            continue
        if metodo == "SetStringSelection":
            if valores[clave] and not _asignaChoice(control, valores[clave]):
                opciones = u", ".join(control.GetString(i) for i in range(control.GetCount()))
                fallos.append(
                    u"%s: '%s' no esta en la lista.\n  Valores validos: %s" % (atributo, valores[clave], opciones)
                )
        else:
            control.SetValue(valores[clave])
    return fallos


def provinciasDisponibles(parent):
    """Provincias del propio desplegable de CE3X; si no hay panel, las de Calculos."""
    control = getattr(getattr(parent, "panelDatosAdministrativos", None), "provinciaCertificadorChoice", None)
    if control is not None:
        try:
            return [control.GetString(i) for i in range(control.GetCount())]
        except Exception:
            logging.warning("DatosLocales: no se pudo leer el desplegable de provincias", exc_info=True)
    try:
        from Calculos.listados import getListadoProvincias

        return list(getListadoProvincias())
    except Exception:
        logging.info("DatosLocales: sin listado de provincias, se usara texto libre")
        return []


# --------------------------------------------------------------------------
# interfaz
# --------------------------------------------------------------------------
class DialogoPerfiles(wx.Dialog):
    """CRUD de perfiles: lista a la izquierda, formulario a la derecha."""

    def __init__(self, parent, ruta, perfiles, provincias=None):
        wx.Dialog.__init__(
            self,
            parent,
            -1,
            _t(u"Mis datos administrativos"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.ruta = ruta
        self.perfiles = perfiles
        self.provincias = provincias or []
        self.guardado = False
        self.indice = -1
        self.controles = {}
        self._construirInterfaz()
        self._refrescarLista(0 if self.perfiles else -1)

    def _construirInterfaz(self):
        self.lista = wx.ListBox(self, -1, size=(190, 320), style=wx.LB_SINGLE)
        self.Bind(wx.EVT_LISTBOX, self.onSeleccionar, self.lista)

        botonesLista = wx.BoxSizer(wx.HORIZONTAL)
        for etiqueta, manejador in (
            (_t(u"Nuevo"), self.onNuevo),
            (_t(u"Duplicar"), self.onDuplicar),
            (_t(u"Borrar"), self.onBorrar),
        ):
            boton = wx.Button(self, -1, etiqueta)
            self.Bind(wx.EVT_BUTTON, manejador, boton)
            botonesLista.Add(boton, 1, wx.RIGHT, 3)

        izquierda = wx.BoxSizer(wx.VERTICAL)
        izquierda.Add(self.lista, 1, wx.EXPAND | wx.BOTTOM, 5)
        izquierda.Add(botonesLista, 0, wx.EXPAND)

        formulario = wx.FlexGridSizer(len(CAMPOS) + 1, 2, 4, 6)
        formulario.AddGrowableCol(1)
        for clave, etiqueta in CAMPOS:
            if clave == "provincia" and self.provincias:
                # editable ademas de desplegable: no perdemos un valor antiguo fuera de lista
                control = wx.ComboBox(self, -1, u"", choices=self.provincias, style=wx.CB_DROPDOWN, size=(230, -1))
            else:
                control = wx.TextCtrl(self, -1, u"", size=(230, -1))
            self.controles[clave] = control
            formulario.Add(wx.StaticText(self, -1, _t(etiqueta)), 0, wx.ALIGN_CENTER_VERTICAL)
            formulario.Add(control, 1, wx.EXPAND)
        self.controles["esAutonomo"] = wx.CheckBox(self, -1, _t(u"Autónomo (empresa = nombre, CIF = NIF)"))
        formulario.Add(wx.StaticText(self, -1, u""), 0)
        formulario.Add(self.controles["esAutonomo"], 0, wx.EXPAND)

        # id propio en vez de wx.ID_OK: asi el dialogo no se cierra al guardar
        self.wxID_GUARDAR = wx.NewId()
        botonGuardar = wx.Button(self, self.wxID_GUARDAR, _t(u"Guardar"))
        self.Bind(wx.EVT_BUTTON, self.onGuardar, botonGuardar)
        botonesDialogo = wx.BoxSizer(wx.HORIZONTAL)
        botonesDialogo.Add(botonGuardar, 0, wx.RIGHT, 5)
        botonesDialogo.Add(wx.Button(self, wx.ID_CANCEL, _t(u"Cerrar")), 0)

        cuerpo = wx.BoxSizer(wx.HORIZONTAL)
        cuerpo.Add(izquierda, 0, wx.EXPAND | wx.ALL, 8)
        cuerpo.Add(formulario, 1, wx.EXPAND | wx.ALL, 8)

        principal = wx.BoxSizer(wx.VERTICAL)
        principal.Add(cuerpo, 1, wx.EXPAND)
        principal.Add(botonesDialogo, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(principal)

    # -- sincronizacion lista <-> formulario --------------------------------
    def _refrescarLista(self, seleccion):
        self.lista.Set([etiquetaPerfil(p, i) for i, p in enumerate(self.perfiles)])
        self.indice = -1
        if 0 <= seleccion < len(self.perfiles):
            self.lista.SetSelection(seleccion)
            self._cargarEnFormulario(seleccion)
        else:
            self._limpiarFormulario()

    def _cargarEnFormulario(self, indice):
        perfil = self.perfiles[indice]
        for clave, _etiqueta in CAMPOS:
            self.controles[clave].SetValue(perfil.get(clave, u""))
        self.controles["esAutonomo"].SetValue(bool(perfil.get("esAutonomo")))
        self._habilitarFormulario(True)
        self.indice = indice

    def _limpiarFormulario(self):
        for clave, _etiqueta in CAMPOS:
            self.controles[clave].SetValue(u"")
        self.controles["esAutonomo"].SetValue(False)
        self._habilitarFormulario(False)

    def _habilitarFormulario(self, activo):
        for control in self.controles.values():
            control.Enable(activo)

    def _guardarFormularioEnPerfil(self):
        if not 0 <= self.indice < len(self.perfiles):
            return
        perfil = self.perfiles[self.indice]
        for clave, _etiqueta in CAMPOS:
            perfil[clave] = self.controles[clave].GetValue()
        perfil["esAutonomo"] = bool(self.controles["esAutonomo"].GetValue())

    # -- manejadores --------------------------------------------------------
    def onSeleccionar(self, event):
        self._guardarFormularioEnPerfil()
        anterior = self.indice
        if 0 <= anterior < len(self.perfiles):
            self.lista.SetString(anterior, etiquetaPerfil(self.perfiles[anterior], anterior))
        seleccion = self.lista.GetSelection()
        if 0 <= seleccion < len(self.perfiles):
            self._cargarEnFormulario(seleccion)

    def onNuevo(self, event):
        self._guardarFormularioEnPerfil()
        self.perfiles.append(perfilVacio())
        self._refrescarLista(len(self.perfiles) - 1)

    def onDuplicar(self, event):
        self._guardarFormularioEnPerfil()
        if not 0 <= self.indice < len(self.perfiles):
            return
        copia = copy.deepcopy(self.perfiles[self.indice])
        copia["alias"] = etiquetaPerfil(copia, self.indice) + _t(u" (copia)")
        self.perfiles.append(copia)
        self._refrescarLista(len(self.perfiles) - 1)

    def onBorrar(self, event):
        if not 0 <= self.indice < len(self.perfiles):
            return
        etiqueta = etiquetaPerfil(self.perfiles[self.indice], self.indice)
        respuesta = wx.MessageBox(
            _t(u"¿Borrar el perfil «%s»?") % etiqueta,
            _t(u"Confirmar"),
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if respuesta != wx.YES:
            return
        del self.perfiles[self.indice]
        self._refrescarLista(min(self.indice, len(self.perfiles) - 1))

    def onGuardar(self, event):
        self._guardarFormularioEnPerfil()
        try:
            guardarPerfiles(self.ruta, self.perfiles)
        except (IOError, OSError) as error:
            wx.MessageBox(_t(u"No se ha podido guardar %s:\n%s") % (self.ruta, error), _t(u"Aviso"))
            return
        self.guardado = True
        self._refrescarLista(self.indice)
        wx.MessageBox(
            _t(u"Cambios guardados (%d perfiles) en:\n%s") % (len(self.perfiles), self.ruta),
            _t(u"Guardado"),
        )


class menuItem:
    def __init__(self, parent):
        self.parent = parent
        self.menuit = wx.Menu()
        self.perfiles = []
        self._idsEnlazados = []
        self.recargarPerfiles()

    # -- construccion del menu ----------------------------------------------
    def _vaciarMenu(self):
        for identificador in self._idsEnlazados:
            self.parent.Unbind(wx.EVT_MENU, id=identificador)
        self._idsEnlazados = []
        for elemento in list(self.menuit.GetMenuItems()):
            self.menuit.Delete(elemento.GetId())

    def _anadeItem(self, texto, ayuda, manejador, activo=True):
        identificador = wx.NewId()
        self.menuit.Append(help=ayuda, id=identificador, kind=wx.ITEM_NORMAL, text=texto)
        if manejador is not None:
            self.parent.Bind(wx.EVT_MENU, manejador, id=identificador)
            self._idsEnlazados.append(identificador)
        if not activo:
            self.menuit.Enable(identificador, False)
        return identificador

    def _manejadorDePerfil(self, indice):
        def alPulsar(event, indice=indice):
            self.aplicarPerfil(indice)

        return alPulsar

    def reconstruirMenu(self):
        self._vaciarMenu()
        if self.perfiles:
            for indice, perfil in enumerate(self.perfiles):
                self._anadeItem(
                    etiquetaPerfil(perfil, indice),
                    _t(u"Vuelca este perfil en la pestaña de datos administrativos"),
                    self._manejadorDePerfil(indice),
                )
        else:
            self._anadeItem(_t(u"(sin perfiles configurados)"), u"", None, activo=False)
        self.menuit.AppendSeparator()
        self._anadeItem(
            _t(u"Editar mis datos..."),
            _t(u"Crear, editar o borrar perfiles de certificador"),
            self.onEditar,
        )

    def recargarPerfiles(self):
        """Relee el JSON y regenera el menu. Nunca propaga: rompería el arranque."""
        ruta = rutaConfiguracion()
        try:
            self.perfiles = cargarPerfiles(ruta)
        except Exception:
            logging.warning("DatosLocales: no se pudo leer %s", ruta, exc_info=True)
            self.perfiles = []
        self.reconstruirMenu()

    # -- acciones -----------------------------------------------------------
    def aplicarPerfil(self, indice):
        if not 0 <= indice < len(self.perfiles):
            return
        perfil = self.perfiles[indice]
        try:
            panel = self.parent.panelDatosAdministrativos
        except AttributeError:
            wx.MessageBox(_t(u"Abra o cree un certificado antes de rellenar los datos."), _t(u"Aviso"))
            return

        try:
            fallos = volcarEnPanel(panel, construyeValores(perfil))
        except Exception as error:
            logging.warning("DatosLocales: fallo al volcar los datos", exc_info=True)
            wx.MessageBox(_t(u"No se han podido volcar los datos:\n%s") % error, _t(u"Aviso"))
            return

        if fallos:
            wx.MessageBox(
                _t(u"Datos cargados, pero estos campos no se han aplicado:\n\n- %s") % u"\n- ".join(fallos),
                _t(u"Aviso"),
            )
        else:
            logging.info("DatosLocales: perfil '%s' aplicado", etiquetaPerfil(perfil, indice))

    def onEditar(self, event):
        ruta = rutaConfiguracion()
        try:
            perfiles = cargarPerfiles(ruta)
        except (ValueError, UnicodeDecodeError) as error:
            wx.MessageBox(
                _t(u"El fichero %s no es un JSON valido (UTF-8):\n%s") % (ruta, error),
                _t(u"Aviso"),
            )
            return
        except (IOError, OSError) as error:
            wx.MessageBox(_t(u"No se ha podido leer %s:\n%s") % (ruta, error), _t(u"Aviso"))
            return

        dialogo = DialogoPerfiles(self.parent, ruta, perfiles, provinciasDisponibles(self.parent))
        try:
            dialogo.ShowModal()
            guardado = dialogo.guardado
        finally:
            dialogo.Destroy()
        if guardado:
            self.recargarPerfiles()


def create(parent):
    """Punto de entrada que invoca wxFrame1._init_coll_menuComplementos_Items."""
    return menuItem(parent)


logging.warning("Complemento: DatosLocales - Version: %s", versionComplemento)
