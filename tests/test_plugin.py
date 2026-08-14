# -*- coding: utf-8 -*-
"""Prueba del plugin con un wx y un panel de CE3X simulados."""
import json
import os
import shutil
import sys
import tempfile
import types

# --- doble de wxPython 2.8 --------------------------------------------------
wx = types.ModuleType("wx")
for _nombre, _valor in [
    ("ITEM_NORMAL", 0),
    ("EVT_MENU", "EVT_MENU"),
    ("EVT_BUTTON", "EVT_BUTTON"),
    ("EVT_LISTBOX", "EVT_LISTBOX"),
    ("ID_OK", 5100),
    ("ID_CANCEL", 5101),
    ("YES", 2),
    ("NO", 8),
    ("YES_NO", 10),
    ("ICON_QUESTION", 16),
    ("LB_SINGLE", 0),
    ("HORIZONTAL", 4),
    ("VERTICAL", 8),
    ("EXPAND", 8192),
    ("ALL", 15),
    ("RIGHT", 8),
    ("BOTTOM", 128),
    ("ALIGN_RIGHT", 512),
    ("ALIGN_CENTER_VERTICAL", 2048),
    ("CB_DROPDOWN", 4),
    ("DEFAULT_DIALOG_STYLE", 536877056),
    ("RESIZE_BORDER", 64),
]:
    setattr(wx, _nombre, _valor)

wx.avisos = []
wx.respuestaMessageBox = wx.YES
_ids = [1000]


def _NewId():
    _ids[0] += 1
    return _ids[0]


def _MessageBox(texto, titulo=u"", estilo=0):
    wx.avisos.append((titulo, texto))
    return wx.respuestaMessageBox


wx.NewId = _NewId
wx.MessageBox = _MessageBox


class _MenuItem(object):
    def __init__(self, identificador, texto):
        self.identificador = identificador
        self.texto = texto
        self.activo = True

    def GetId(self):
        return self.identificador


class _Menu(object):
    def __init__(self):
        self.elementos = []

    def Append(self, help=None, id=None, kind=None, text=None):
        self.elementos.append(_MenuItem(id, text))

    def AppendSeparator(self):
        self.elementos.append(_MenuItem(-1, "---"))

    def GetMenuItems(self):
        return list(self.elementos)

    def Delete(self, identificador):
        self.elementos = [e for e in self.elementos if e.identificador != identificador]

    def Enable(self, identificador, activo):
        for elemento in self.elementos:
            if elemento.identificador == identificador:
                elemento.activo = activo

    @property
    def items(self):
        return [e.texto for e in self.elementos]


class _Sizer(object):
    def __init__(self, *args, **kwargs):
        pass

    def Add(self, *args, **kwargs):
        pass

    def AddGrowableCol(self, *args, **kwargs):
        pass


class _Ventana(object):
    def __init__(self, *args, **kwargs):
        self.activo = True

    def Enable(self, activo=True):
        self.activo = activo


class _TextCtrl(_Ventana):
    def __init__(self, parent=None, id=None, value=u"", size=None, style=0):
        _Ventana.__init__(self)
        self.valor = value

    def SetValue(self, v):
        self.valor = v

    def GetValue(self):
        return self.valor


class _CheckBox(_TextCtrl):
    def __init__(self, parent=None, id=None, label=u"", **kwargs):
        _TextCtrl.__init__(self, value=False)


class _ComboBox(_TextCtrl):
    def __init__(self, parent=None, id=None, value=u"", choices=None, style=0, size=None):
        _TextCtrl.__init__(self, value=value)
        self.choices = list(choices or [])


class _ListBox(_Ventana):
    def __init__(self, parent=None, id=None, size=None, style=0):
        _Ventana.__init__(self)
        self.items = []
        self.seleccion = -1

    def Set(self, items):
        self.items = list(items)
        self.seleccion = -1

    def SetString(self, i, s):
        self.items[i] = s

    def SetSelection(self, i):
        self.seleccion = i

    def GetSelection(self):
        return self.seleccion


class _Dialog(_Ventana):
    def __init__(self, parent=None, id=None, title=u"", style=0):
        _Ventana.__init__(self)
        self.parent = parent
        self.codigoSalida = None

    def Bind(self, evento, manejador, origen=None):
        pass

    def SetSizerAndFit(self, sizer):
        pass

    def EndModal(self, codigo):
        self.codigoSalida = codigo

    def ShowModal(self):
        return wx.ID_OK

    def Destroy(self):
        pass


wx.Menu = _Menu
wx.BoxSizer = _Sizer
wx.FlexGridSizer = _Sizer
wx.TextCtrl = _TextCtrl
wx.CheckBox = _CheckBox
wx.ComboBox = _ComboBox
wx.StaticText = _Ventana
wx.Button = _Ventana
wx.ListBox = _ListBox
wx.Dialog = _Dialog
sys.modules["wx"] = wx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "plugin"))
import DatosLocales  # noqa: E402


# --- doble de los controles de CE3X -----------------------------------------
class Choice(object):
    def __init__(self, opciones):
        self.opciones = opciones
        self.seleccion = -1

    def SetStringSelection(self, s):
        if s in self.opciones:
            self.seleccion = self.opciones.index(s)
            return True
        return False

    def GetCount(self):
        return len(self.opciones)

    def GetString(self, i):
        return self.opciones[i]

    def SetSelection(self, i):
        self.seleccion = i

    def valorActual(self):
        return self.opciones[self.seleccion] if self.seleccion >= 0 else None


class PanelDatosAdministrativos(object):
    def __init__(self):
        for nombre in (
            "certificadorAutor",
            "nifCertificadorCuadro",
            "certificadorEmpresa",
            "cifCertificadorCuadro",
            "direccionCertificador",
            "localidadCertificadorCuadro",
            "codigoPostalCertificadorCuadro",
            "certificadorTelefono",
            "certificadorMail",
            "titulacionHabilitanteCuadro",
        ):
            setattr(self, nombre, _TextCtrl())
        self.provinciaCertificadorChoice = Choice([u"A Coruña", u"Madrid", u"Sevilla"])


class Ventana(object):
    def __init__(self):
        self.panelDatosAdministrativos = PanelDatosAdministrativos()
        self.binds = []

    def Bind(self, evento, manejador, id=None):
        self.binds.append((evento, manejador, id))

    def Unbind(self, evento, id=None):
        self.binds = [b for b in self.binds if b[2] != id]

    def pulsaMenu(self, identificador):
        for evento, manejador, identificadorEnlazado in self.binds:
            if identificadorEnlazado == identificador:
                manejador(None)
                return True
        return False


# --- datos de prueba --------------------------------------------------------
PERFILES = {
    "perfiles": [
        {
            "alias": u"Autónomo",
            "nombre": u"Ana",
            "apellidos": u"García López",
            "nif": u"12345678Z",
            "esAutonomo": True,
            "razonSocial": u"",
            "cif": u"",
            "direccion": u"Calle Mayor, 1",
            "provincia": u"Madrid",
            "localidad": u"Madrid",
            "codigoPostal": u"28001",
            "telefono": u"600000000",
            "email": u"ana.garcia@ejemplo.es",
            "titulacion": u"Arquitecto Técnico",
        },
        {
            "alias": u"Estudio SL",
            "nombre": u"Ana",
            "apellidos": u"García López",
            "nif": u"12345678Z",
            "esAutonomo": False,
            "razonSocial": u"Estudio Ejemplo S.L.",
            "cif": u"B12345678",
            "direccion": u"Av. Andalucía, 5",
            "provincia": u"sevilla",
            "localidad": u"Sevilla",
            "codigoPostal": u"41001",
            "telefono": u"955000000",
            "email": u"info@estudio.es",
            "titulacion": u"Arquitecto",
        },
    ]
}


def escribeConfig(directorio, contenido):
    ruta = os.path.join(directorio, "datosAdministrativos.json")
    with open(ruta, "w") as fichero:
        json.dump(contenido, fichero)
    os.environ["CE3X_DATOS_ADMIN"] = ruta
    return ruta


# --- pruebas ----------------------------------------------------------------
def pruebaMenu(ventana):
    plugin = DatosLocales.create(ventana)
    assert plugin.menuit is not None, "CE3X lee el atributo menuit de create()"
    assert plugin.menuit.items == [u"Autónomo", u"Estudio SL", "---", u"Editar mis datos..."], plugin.menuit.items
    print("menu:", plugin.menuit.items)
    return plugin


def pruebaVolcadoDesdeMenu(plugin, ventana):
    panel = ventana.panelDatosAdministrativos
    idEstudio = plugin.menuit.elementos[1].GetId()
    idAutonomo = plugin.menuit.elementos[0].GetId()

    wx.avisos = []
    assert ventana.pulsaMenu(idEstudio), "el item de menu debe estar enlazado"
    assert panel.certificadorAutor.valor == u"Ana García López"
    assert panel.certificadorEmpresa.valor == u"Estudio Ejemplo S.L.", "no autonomo -> razon social propia"
    assert panel.cifCertificadorCuadro.valor == u"B12345678"
    assert panel.provinciaCertificadorChoice.valorActual() == u"Sevilla", "match sin distinguir mayusculas"
    assert wx.avisos == [], "sin errores no debe salir ningun MessageBox"
    print("volcado directo desde el menu ('Estudio SL'): OK")

    ventana.pulsaMenu(idAutonomo)
    assert panel.certificadorEmpresa.valor == u"Ana García López", "autonomo -> empresa = autor"
    assert panel.cifCertificadorCuadro.valor == u"12345678Z", "autonomo -> cif = nif"
    print("volcado directo desde el menu ('Autónomo'): OK")


def pruebaProvincias(ventana):
    provincias = DatosLocales.provinciasDisponibles(ventana)
    assert provincias == [u"A Coruña", u"Madrid", u"Sevilla"], provincias
    dialogo = DatosLocales.DialogoPerfiles(ventana, "/tmp/x.json", [], provincias)
    combo = dialogo.controles["provincia"]
    assert isinstance(combo, _ComboBox), "provincia debe ser desplegable"
    assert combo.choices == provincias
    assert isinstance(dialogo.controles["localidad"], _TextCtrl)
    print("desplegable de provincias: OK")


def pruebaGuardarNoCierra(ventana, ruta):
    dialogo = DatosLocales.DialogoPerfiles(ventana, ruta, DatosLocales.cargarPerfiles(ruta), [])
    dialogo.controles["alias"].SetValue(u"Renombrado")
    wx.avisos = []
    dialogo.onGuardar(None)

    assert dialogo.codigoSalida is None, "guardar no debe cerrar el dialogo"
    assert dialogo.guardado is True
    assert len(wx.avisos) == 1 and wx.avisos[0][0] == u"Guardado", wx.avisos
    assert dialogo.lista.items[0] == u"Renombrado", "la lista se refresca tras guardar"
    assert DatosLocales.cargarPerfiles(ruta)[0]["alias"] == u"Renombrado"
    print("guardar sin cerrar + confirmacion: OK")


def pruebaMenuSeRefresca(ventana, ruta):
    plugin = DatosLocales.create(ventana)
    assert plugin.menuit.items[0] == u"Renombrado"

    perfiles = DatosLocales.cargarPerfiles(ruta)
    perfiles.append(dict(PERFILES["perfiles"][0], alias=u"Nuevo desde fuera"))
    DatosLocales.guardarPerfiles(ruta, perfiles)
    plugin.recargarPerfiles()

    assert plugin.menuit.items == [
        u"Renombrado",
        u"Estudio SL",
        u"Nuevo desde fuera",
        "---",
        u"Editar mis datos...",
    ], plugin.menuit.items
    assert ventana.pulsaMenu(plugin.menuit.elementos[2].GetId()), "el item nuevo queda enlazado"
    identificadores = [b[2] for b in ventana.binds]
    assert len(identificadores) == len(set(identificadores)), "no deben quedar enlaces duplicados"
    print("menu refrescado tras modificar la lista: OK")


def pruebaSinPerfiles(directorio):
    ruta = escribeConfig(directorio, {"perfiles": []})
    ventana = Ventana()
    plugin = DatosLocales.create(ventana)
    assert plugin.menuit.items == [u"(sin perfiles configurados)", "---", u"Editar mis datos..."]
    assert plugin.menuit.elementos[0].activo is False, "el aviso de lista vacia va deshabilitado"
    print("menu sin perfiles: OK")


def pruebaCrud(ventana, ruta):
    dialogo = DatosLocales.DialogoPerfiles(ventana, ruta, DatosLocales.cargarPerfiles(ruta), [])
    assert dialogo.indice == 0
    assert dialogo.lista.items == [u"Autónomo", u"Estudio SL"]

    dialogo.onNuevo(None)
    assert len(dialogo.perfiles) == 3 and dialogo.indice == 2
    dialogo.controles["alias"].SetValue(u"Tercero")
    dialogo.controles["nombre"].SetValue(u"Luis")
    print("nuevo: OK")

    dialogo.onDuplicar(None)
    assert len(dialogo.perfiles) == 4
    assert dialogo.perfiles[3]["alias"] == u"Tercero (copia)"
    assert dialogo.perfiles[3]["nombre"] == u"Luis", "duplicar toma el formulario en curso"
    print("duplicar: OK")

    wx.respuestaMessageBox = wx.NO
    dialogo.onBorrar(None)
    assert len(dialogo.perfiles) == 4, "responder NO no debe borrar"
    wx.respuestaMessageBox = wx.YES
    dialogo.onBorrar(None)
    assert len(dialogo.perfiles) == 3 and dialogo.indice == 2
    print("borrar: OK")

    dialogo.onGuardar(None)
    guardados = DatosLocales.cargarPerfiles(ruta)
    assert [p["alias"] for p in guardados] == [u"Autónomo", u"Estudio SL", u"Tercero"]
    assert guardados[2]["nombre"] == u"Luis"
    print("guardar: OK")


def pruebaFormatoAntiguo(directorio):
    ruta = escribeConfig(directorio, dict(PERFILES["perfiles"][0]))
    perfiles = DatosLocales.cargarPerfiles(ruta)
    assert len(perfiles) == 1 and perfiles[0]["alias"] == u"Autónomo"
    print("migracion formato antiguo: OK")


def main():
    directorio = tempfile.mkdtemp()
    try:
        ruta = escribeConfig(directorio, PERFILES)
        ventana = Ventana()
        plugin = pruebaMenu(ventana)
        pruebaVolcadoDesdeMenu(plugin, ventana)
        pruebaProvincias(ventana)
        pruebaCrud(ventana, escribeConfig(directorio, PERFILES))
        pruebaGuardarNoCierra(Ventana(), escribeConfig(directorio, PERFILES))
        pruebaMenuSeRefresca(Ventana(), ruta)
        pruebaSinPerfiles(directorio)
        pruebaFormatoAntiguo(directorio)
        print("\nOK")
    finally:
        shutil.rmtree(directorio)


if __name__ == "__main__":
    main()
