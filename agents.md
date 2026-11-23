# Documentacion del proyecto

Este proyecto contiene dos clientes para la API de Google GenAI: un chat por
consola y una interfaz grafica Qt. Aunque el nombre original menciona Gemma 4,
el programa usa el SDK `google-genai` y el modelo indicado por
`GOOGLE_MODEL_ID`; por tanto, normalmente se conecta a un modelo Gemini
compatible con la API.

## Flujo general

1. Un script BAT entra en la carpeta del proyecto.
2. Si falta `.venv`, instala `uv` y crea el entorno virtual.
3. Activa `.venv` e instala o actualiza `google-genai`, `python-dotenv` y
     `PySide6`.
4. Ejecuta `gemini_qt_app.py`.
5. Python carga `.env`, crea un cliente GenAI y abre una conversacion.
6. Cada mensaje se envia a Google. La interfaz tambien puede subir un archivo.

El chat de consola se ejecuta aparte con `simple_google_agent.py` y no lo
llama la interfaz Qt.

## Configuracion: `.env.example` y `.env`

En `.env.example` se documentan las dos variables esperadas:

- `GOOGLE_API_KEY`: clave privada de Google. Debe copiarse a `.env` y nunca
    publicarse ni escribirse en este documento.
- `GOOGLE_MODEL_ID`: identificador del modelo que usaran ambos programas.

`.env.example` solo es una plantilla. `.env` es el archivo real que carga
`load_dotenv()`. No se debe borrar `.env` mientras se quiera ejecutar el
programa, salvo que se vaya a crear de nuevo con la clave configurada.

## `simple_google_agent.py`, linea por linea

- Linea 1: importa `os` para leer variables de entorno.
- Linea 2: importa `load_dotenv`, que lee el archivo `.env`.
- Linea 3: importa el cliente oficial `genai`.
- Lineas 5-6: carga `.env`, obtiene la clave y obtiene el modelo. Si no existe
    `GOOGLE_MODEL_ID`, usa `gemini-3.6-flash` como valor predeterminado.
- Lineas 8-9: detiene el programa con un mensaje claro si falta la clave.
- Lineas 11-12: crea el cliente autenticado y una conversacion con memoria del
    historial de mensajes.
- Linea 14: muestra instrucciones al usuario.
- Lineas 16-25: mantiene el bucle del chat. Lee una entrada, ignora entradas
    vacias, acepta `salir`, `exit` o `quit`, envia el texto a Gemini y muestra la
    respuesta.

Ejecucion:

```powershell
.\.venv\Scripts\python.exe simple_google_agent.py
```

## `gemini_qt_app.py`, linea por linea por bloques

- Linea 1: importa `os`, usado para leer la variable de entorno y extraer el
    nombre del archivo seleccionado.
- Lineas 2-3: cargan `.env` y el SDK de Google.
- Linea 4: importa `Qt` para eventos y banderas de ventana. `QPoint` aparece
    importado, pero no se usa y se puede quitar.
- Linea 5: importa `QPalette` y `QColor` para el tema de la aplicacion.
- Lineas 6-17: importan los controles Qt: ventana, layouts, campos de texto,
    botones, etiqueta, dialogo de error y selector de archivos.
- Lineas 19-25: cargan la configuracion, validan la clave, crean el cliente y
    crean una conversacion reutilizable.
- Linea 28: declara la ventana principal `GeminiChatWindow`.
- Lineas 30-40: inicializan la ventana, su tamano, el estilo sin marco, el
    arrastre manual y el estado del archivo seleccionado.
- Lineas 42-56: permiten mover la ventana sin barra de titulo arrastrando con
    el boton izquierdo del raton.
- Lineas 58-146: construyen la interfaz. Crean el marco, encabezado, titulo,
    botones minimizar/cerrar, area de salida, campo de entrada, boton de
    adjuntar, etiqueta del archivo y boton enviar; despues los ordenan mediante
    layouts.
- Lineas 148-153: conectan los botones y la tecla Enter con sus acciones y
    escriben el mensaje inicial.
- Lineas 155-164: aplican la paleta oscura global de Qt.
- Lineas 166-197: implementan `send_message`. Validan que exista texto o
    archivo, muestran el mensaje localmente, suben el archivo si existe, envian
    ambos contenidos a Gemini, muestran la respuesta y limpian el archivo. Los
    errores se muestran en la interfaz y en un cuadro de dialogo.
- Lineas 199-208: implementan `select_file`. Abren un selector, guardan la
    ruta elegida y muestran solo su nombre.
- Lineas 211-216: crean la aplicacion Qt, seleccionan el estilo Fusion, muestran
    la ventana y mantienen activo el bucle grafico.

## `run_gemini_chat.bat`

- Linea 1: evita mostrar los comandos.
- Linea 2: limita el alcance de las variables al script.
- Linea 3: cambia a la carpeta donde esta el BAT.
- Lineas 5-8: si falta `.venv`, instalan `uv` y crean el entorno virtual. La
    salida se oculta, por lo que un error de instalacion puede pasar inadvertido.
- Linea 10: activa `.venv`.
- Linea 11: instala o actualiza las tres dependencias.
- Lineas 13-14: inicia la interfaz Qt y termina el script.

## `run_gemini_qt.bat`

Hace exactamente lo mismo que `run_gemini_chat.bat`, pero sin el comentario
de la linea 13. Es un duplicado funcional. Conviene conservar solo uno.

## `run_gemini_chat_hidden.vbs`

- Linea 1: crea un objeto de Windows Script Host.
- Linea 2: lanza `run_gemini_chat.bat` con la ventana oculta y sin esperar a
    que termine.

Este archivo solo sirve para iniciar la interfaz sin mostrar una consola.
La ruta esta escrita de forma absoluta; si se mueve la carpeta, deja de
funcionar.

## `gemini_request.json`

Es un ejemplo de cuerpo JSON con un mensaje de usuario. La busqueda del
proyecto no encontro ningun codigo que lo lea, asi que actualmente no afecta
la ejecucion. Los programas usan `chat.send_message()` directamente.

## Que se puede quitar

### Seguro y sin efecto en la aplicacion

- `__pycache__/`: son archivos temporales generados por Python.
- `gemini_request.json`: se puede borrar porque ningun programa lo usa.
- `QPoint` en la linea 4 de `gemini_qt_app.py`: elimina solo ese nombre de la
    importacion, no todo el bloque `QtCore`.

Comandos PowerShell desde la carpeta del proyecto:

```powershell
Remove-Item -Recurse -Force .\__pycache__
Remove-Item .\gemini_request.json
```

Para quitar `QPoint`, deja la importacion asi:

```python
from PySide6.QtCore import Qt
```

### Duplicado opcional

Puedes borrar `run_gemini_qt.bat` y conservar `run_gemini_chat.bat`, o al
contrario. La opcion recomendada es conservar `run_gemini_chat.bat` porque es
el que usa `run_gemini_chat_hidden.vbs`.

```powershell
Remove-Item .\run_gemini_qt.bat
```

No borres `run_gemini_chat_hidden.vbs` si necesitas el arranque oculto.

### Entornos virtuales

- `.venv` es el entorno que usan los BAT y no debe borrarse si se desea iniciar
    el programa sin reinstalar.
- `.venv311` no aparece en los scripts de arranque. Si confirmas que no lo
    usas desde VS Code ni desde otro comando, puedes quitarlo para ahorrar
    espacio; al hacerlo se eliminan todas sus dependencias instaladas.

```powershell
Remove-Item -Recurse -Force .\.venv311
```

### Archivos que no conviene quitar

- `.env`: contiene la configuracion real y la clave necesaria para conectarse.
- `.env.example`: sirve como plantilla para reconstruir `.env`.
- `gemini_qt_app.py`: es la interfaz grafica que arrancan los BAT.
- `simple_google_agent.py`: es el cliente de consola independiente.
- Los dos BAT y el VBS, mientras quieras conservar sus respectivas formas de
    lanzamiento.

## Comprobacion realizada

Los dos archivos Python compilan correctamente con:

```powershell
python -m py_compile simple_google_agent.py gemini_qt_app.py
```

La comprobacion no valida la clave ni hace una llamada a Google; para eso hay
que ejecutar el cliente con un `.env` valido y conectividad a Internet.

## `asistente/` - Asistente Persistente de Escritorio (Segundo Cerebro)

El paquete `asistente/` implementa un asistente de escritorio residente en la
bandeja del sistema (System Tray) con interfaz estilo Spotlight/Raycast, atajo
global `Ctrl + Espacio`, y conexion bidireccional con Obsidian y Google Calendar.

### Modulos incluidos

- `conector_obsidian.py`: Localiza o inicializa la boveda de Obsidian
    (`Documents/ObsidianVault`), lee y crea notas diarias (`Diario/YYYY-MM-DD.md`),
    gestiona tareas con sintaxis `- [ ]` y capturas rapidas en `Capturas/`.
- `conector_calendar.py`: Gestiona la autenticacion OAuth 2.0 persistente con
    Google Calendar, consulta de eventos, creacion de citas y busqueda de huecos.
- `memoria_persistente.py`: Base de datos SQLite (`data/memoria_asistente.db`) que
    guarda hechos del usuario, historial de interacciones y registro de actividad.
- `cerebro_gemini.py`: Orquestador con Google Gemini usando Function Calling
    nativo para invocar herramientas de Obsidian, Calendar y memoria.
- `motor_proactivo.py`: Hilo en segundo plano que emite el briefing matutino y
    alertas de reuniones con 15 minutos de anticipacion.
- `interfaz_spotlight.py`: Ventana flotante moderna sin marco con tema oscuro,
    filtro nativo para el atajo global `Ctrl + Espacio`, System Tray e historial.
- `run_asistente.py`: Punto de entrada principal.
- `run_asistente.bat`: Lanzador rapido con activacion del entorno virtual.

Ejecucion:

```powershell
.\run_asistente.bat
```

