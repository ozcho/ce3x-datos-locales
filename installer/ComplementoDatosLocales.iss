; Instalador del complemento "Datos Locales" para CE3X.
; Compilar con Inno Setup 6 (o 5.5+):  ISCC.exe installer\ComplementoDatosLocales.iss

#define NombreComplemento "Complemento Datos Locales"
#define VersionComplemento "1.1.0"
#define CarpetaPlugins "Plugins"

[Setup]
AppId={{B7A1C4E2-5D3F-4A88-9C10-2E6F0B9D7A34}
AppName={#NombreComplemento}
AppVersion={#VersionComplemento}
AppVerName={#NombreComplemento} {#VersionComplemento}
VersionInfoVersion={#VersionComplemento}
DefaultDirName={code:GetDirName}
DefaultGroupName=CEXv2.3
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
  CLAVE_CE3X = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{7139BD7B-FC0B-435F-8E79-63D7CCDA2BA8}_is1';

// wxFrame1.pyd contiene cogerPlugins(): si esta, es una instalacion de CE3X.
function EsCarpetaCE3X(Ruta: String): Boolean;
begin
  Result := (Ruta <> '') and FileExists(AddBackslash(Ruta) + 'wxFrame1.pyd');
end;

function BuscaCE3X(): String;
var
  Ruta: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, CLAVE_CE3X, 'Inno Setup: App Path', Ruta) and EsCarpetaCE3X(Ruta) then
  begin
    Result := RemoveBackslash(Ruta);
    Exit;
  end;
  if RegQueryStringValue(HKLM, CLAVE_CE3X, 'InstallLocation', Ruta) and EsCarpetaCE3X(Ruta) then
  begin
    Result := RemoveBackslash(Ruta);
    Exit;
  end;
  Ruta := ExpandConstant('{pf32}\CEXv2.3');
  if EsCarpetaCE3X(Ruta) then
    Result := Ruta;
end;

function GetDirName(Param: String): String;
begin
  Result := BuscaCE3X();
  if Result = '' then
    Result := ExpandConstant('{pf32}\CEXv2.3');
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
