@echo off
title Instalação Sistema Academia
color 0A

echo ====================================
echo    SISTEMA ACADEMIA - INSTALACAO
echo ====================================
echo.

echo [1/4] Verificando se Docker está instalado...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Docker não está instalado!
    echo.
    echo Por favor, instale o Docker Desktop:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [2/4] Parando containers anteriores (se existirem)...
docker-compose down >nul 2>&1

echo [3/4] Construindo e iniciando o sistema...
docker-compose up --build -d

echo [4/4] Aguardando sistema inicializar...
timeout /t 15 /nobreak >nul

echo.
echo ====================================
echo    INSTALACAO CONCLUIDA!
echo ====================================
echo.
echo O Sistema Academia está rodando em:
echo http://localhost:5000
echo.
echo Usuario inicial: admin
echo A senha será exibida no terminal do Docker
echo.
echo Para ver a senha, execute: docker-compose logs web
echo.
echo Para parar o sistema: docker-compose down
echo Para iniciar novamente: docker-compose up -d
echo.
pause