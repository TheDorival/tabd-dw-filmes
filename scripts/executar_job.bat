@echo off
rem =====================================================================
rem Roda o job jb_carga_dw_filmes.kjb pelo Kitchen e grava o log em logs\.
rem Uso:   scripts\executar_job.bat [nome_do_log]
rem Exige: PDI_HOME (pasta data-integration) e PENTAHO_JAVA_HOME (Java 11).
rem =====================================================================
setlocal

if "%PDI_HOME%"=="" (
  echo Defina PDI_HOME com a pasta data-integration do Pentaho 9.4.
  exit /b 1
)
if "%PENTAHO_JAVA_HOME%"=="" (
  echo Defina PENTAHO_JAVA_HOME com a pasta do Java 11.
  exit /b 1
)

set "PROJETO=%~dp0.."
for %%I in ("%PROJETO%") do set "PROJETO=%%~fI"

set "NOME_LOG=%~1"
if "%NOME_LOG%"=="" (
  for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "NOME_LOG=execucao_%%T"
)
set "ARQ_LOG=%PROJETO%\logs\%NOME_LOG%.log"

rem Os .bat do Pentaho chamam outros .bat da propria pasta (call Spoon.bat).
set "NoDefaultCurrentDirectoryInExePath="

echo Rodando o job... log em %ARQ_LOG%
call "%PDI_HOME%\Kitchen.bat" -file="%PROJETO%\etl\jb_carga_dw_filmes.kjb" -level=Basic > "%ARQ_LOG%" 2>&1
set "RESULTADO=%ERRORLEVEL%"

if "%RESULTADO%"=="0" (
  echo Carga concluida com sucesso.
) else (
  echo A carga falhou ^(codigo %RESULTADO%^). Veja o log.
)
endlocal & exit /b %RESULTADO%
