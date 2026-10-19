; Instalador del complemento "Datos Locales" para CE3X.
; Compilar con Inno Setup 6 (o 5.5+):  ISCC.exe installer\ComplementoDatosLocales.iss

#define NombreComplemento "Complemento Datos Locales"
#define VersionComplemento "1.2.0"
#define CarpetaPlugins "Plugins"

[Setup]
AppId={{B7A1C4E2-5D3F-4A88-9C10-2E6F0B9D7A34}
AppName={#NombreComplemento}
AppVersion={#VersionComplemento}
AppVerName={#NombreComplemento} {#VersionComplemento}
VersionInfoVersion={#VersionComplemento}
DefaultDirName={code:GetDirName}
; En una actualizacion no reutilizamos la carpeta anterior: puede ser una
; version de CE3X ya desinstalada. Siempre se vuelve a detectar.
UsePreviousAppDir=no
DefaultGroupName={#NombreComplemento}
DisableProgramGroupPage=yes
DisableWelcomePage=no
DirExistsWarning=no
AppendDefaultDirName=no
OutputDir=..\dist
OutputBaseFilename=setupComplementoDatosLocales-{#VersionComplemento}
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=
UninstallDisplayName={#NombreComplemento} {#VersionComplemento}

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\plugin\DatosLocales.py"; DestDir: "{app}\{#CarpetaPlugins}"; Flags: ignoreversion
Source: "..\plugin\datosAdministrativos.ejemplo.json"; DestDir: "{app}\{#CarpetaPlugins}"; Flags: ignoreversion

; El .pyc cachea el codigo antiguo: se borra para forzar la recompilacion.
[InstallDelete]
Type: files; Name: "{app}\{#CarpetaPlugins}\DatosLocales.pyc"

[UninstallDelete]
Type: files; Name: "{app}\{#CarpetaPlugins}\DatosLocales.pyc"

[Code]
const
  CLAVE_DESINSTALAR = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';
  COMANDO_ABRIR_CEX = 'ArchivoCEX\shell\open\command';

var
  CarpetaDetectada: String;
  DeteccionHecha: Boolean;

// wxFrame1.pyd implementa cogerPlugins(); Plugins es la carpeta de destino.
function EsCarpetaCE3X(Ruta: String): Boolean;
var
  Base: String;
begin
  Result := False;
  if Ruta = '' then
    Exit;
  Base := AddBackslash(Ruta);
  Result := FileExists(Base + 'wxFrame1.pyd') or DirExists(Base + 'Plugins');
end;

function NormalizaCarpeta(Ruta: String): String;
begin
  Result := '';
  Ruta := RemoveQuotes(Trim(Ruta));
  if EsCarpetaCE3X(Ruta) then
    Result := RemoveBackslash(Ruta);
end;

// La asociacion de los .cex apunta al CE3X realmente activo, sea cual sea su version.
function CarpetaDesdeAsociacion(): String;
var
  Comando: String;
  Posicion: Integer;
begin
  Result := '';
  if not RegQueryStringValue(HKCR, COMANDO_ABRIR_CEX, '', Comando) then
    Exit;
  Comando := Trim(Comando);
  if Copy(Comando, 1, 1) = '"' then
  begin
    Delete(Comando, 1, 1);
    Posicion := Pos('"', Comando);
  end
  else
    Posicion := Pos(' ', Comando);
  if Posicion > 0 then
    Comando := Copy(Comando, 1, Posicion - 1);
  Result := NormalizaCarpeta(ExtractFileDir(Comando));
end;

function CarpetaDesdeDesinstalador(Raiz: Integer): String;
var
  Claves: TArrayOfString;
  Indice: Integer;
  Clave, Nombre, Ruta: String;
begin
  Result := '';
  if not RegGetSubkeyNames(Raiz, CLAVE_DESINSTALAR, Claves) then
    Exit;
  for Indice := 0 to GetArrayLength(Claves) - 1 do
  begin
    Clave := CLAVE_DESINSTALAR + '\' + Claves[Indice];
    if not RegQueryStringValue(Raiz, Clave, 'DisplayName', Nombre) then
      Continue;
    if Pos('CE3X', Uppercase(Nombre)) = 0 then
      if Pos('CEX', Uppercase(Nombre)) = 0 then
        Continue;
    if RegQueryStringValue(Raiz, Clave, 'Inno Setup: App Path', Ruta) then
    begin
      Result := NormalizaCarpeta(Ruta);
      if Result <> '' then
        Exit;
    end;
    if RegQueryStringValue(Raiz, Clave, 'InstallLocation', Ruta) then
    begin
      Result := NormalizaCarpeta(Ruta);
      if Result <> '' then
        Exit;
    end;
  end;
end;

// Ultimo recurso: carpetas tipo CEXv2.3, CEXv2.4... Se queda con la mayor.
function CarpetaEnProgramFiles(Base: String): String;
var
  Busqueda: TFindRec;
  Candidata, Mejor, MejorNombre: String;
begin
  Mejor := '';
  MejorNombre := '';
  if FindFirst(AddBackslash(Base) + 'CE*', Busqueda) then
  try
    repeat
      if (Busqueda.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
      begin
        Candidata := NormalizaCarpeta(AddBackslash(Base) + Busqueda.Name);
        if (Candidata <> '') and (Uppercase(Busqueda.Name) > MejorNombre) then
        begin
          Mejor := Candidata;
          MejorNombre := Uppercase(Busqueda.Name);
        end;
      end;
    until not FindNext(Busqueda);
  finally
    FindClose(Busqueda);
  end;
  Result := Mejor;
end;

function BuscaCE3X(): String;
begin
  if not DeteccionHecha then
  begin
    DeteccionHecha := True;
    CarpetaDetectada := CarpetaDesdeAsociacion();
    if CarpetaDetectada = '' then
      CarpetaDetectada := CarpetaDesdeDesinstalador(HKLM);
    if (CarpetaDetectada = '') and IsWin64 then
      CarpetaDetectada := CarpetaDesdeDesinstalador(HKLM64);
    if CarpetaDetectada = '' then
      CarpetaDetectada := CarpetaDesdeDesinstalador(HKCU);
    if CarpetaDetectada = '' then
      CarpetaDetectada := CarpetaEnProgramFiles(ExpandConstant('{pf32}'));
    if CarpetaDetectada = '' then
      CarpetaDetectada := CarpetaEnProgramFiles(ExpandConstant('{pf}'));
  end;
  Result := CarpetaDetectada;
end;

function GetDirName(Param: String): String;
begin
  Result := BuscaCE3X();
  if Result = '' then
    Result := ExpandConstant('{pf32}\CEX');
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if BuscaCE3X() = '' then
    Result := MsgBox('No se ha encontrado ninguna instalacion de CE3X.' + #13#10#13#10 +
                     'Puede continuar e indicar la carpeta manualmente.' + #13#10 +
                     'Continuar?', mbConfirmation, MB_YESNO) = IDYES;
end;

function NextButtonClick(IdPagina: Integer): Boolean;
begin
  Result := True;
  if IdPagina = wpSelectDir then
    if not EsCarpetaCE3X(WizardDirValue) then
      Result := MsgBox('La carpeta indicada no parece una instalacion de CE3X' + #13#10 +
                       '(no se encuentra wxFrame1.pyd).' + #13#10#13#10 +
                       'Instalar de todos modos?', mbConfirmation, MB_YESNO) = IDYES;
end;
