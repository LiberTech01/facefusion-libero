"""
Script para preparar una integración de Pinokio para FaceFusion.

Este script automatiza los pasos necesarios para que el repositorio funcione
como una aplicación de Pinokio sin utilizar el instalador de Pinokio.
Realiza lo siguiente:

1. Clona el repositorio oficial de FaceFusion (versión 3.2.0) en
   un subdirectorio llamado ``facefusion`` si no existe todavía.
2. Crea un entorno virtual de Python en la carpeta ``env``. Pinokio
   reconocerá esta carpeta como el entorno de ejecución predeterminado.
3. Actualiza ``pip``, ``wheel`` y ``setuptools`` dentro del entorno.
4. Ejecuta el instalador integrado de FaceFusion con la opción
   ``--onnxruntime default`` para instalar todas las dependencias.
5. Genera los archivos ``pinokio.js``, ``install.json``, ``start.json``
   y ``session.json`` en la raíz del repositorio si no existen.

Después de ejecutar este script, podrás abrir Pinokio, añadir tu
repositorio (por URL o arrastrándolo), y la aplicación aparecerá
como «Instalada». Sólo deberás pulsar **Iniciar** para arrancarla.

Uso:

```
python setup_pinokio.py
```

Requisitos:
- Python 3.8 o superior instalado.
- Git instalado para clonar el repositorio FaceFusion.

"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Ejecuta un comando en el sistema y muestra su salida.

    Args:
        cmd (list[str] | str): Comando a ejecutar. Se puede pasar como
            cadena o lista de strings. Cuando es lista se pasa tal cual a
            subprocess.run.
        cwd (str | Path | None): Directorio de trabajo donde ejecutar
            el comando.
    """
    if isinstance(cmd, str):
        cmd_to_run = cmd
    else:
        cmd_to_run = cmd
    print(f"Ejecutando: {cmd_to_run}")
    subprocess.check_call(cmd_to_run, shell=isinstance(cmd_to_run, str), cwd=cwd)


def ensure_facefusion_repo(repo_dir: Path):
    """Clona el repositorio facefusion si aún no existe.

    Args:
        repo_dir (Path): Ruta donde se clonará el repositorio.
    """
    if repo_dir.exists():
        print(f"El directorio {repo_dir} ya existe, se asume que el repositorio está clonado.")
        return
    repo_url = "https://github.com/facefusion/facefusion"
    branch = "3.2.0"
    print(f"Clonando FaceFusion {branch} en {repo_dir}…")
    run_command([
        "git",
        "clone",
        repo_url,
        str(repo_dir),
        "--branch",
        branch,
        "--single-branch",
    ])


def ensure_virtualenv(env_dir: Path):
    """Crea un entorno virtual en env_dir si no existe.

    Args:
        env_dir (Path): Directorio donde se creará el entorno virtual.
    """
    if env_dir.exists():
        print(f"El entorno virtual {env_dir} ya existe, omitiendo creación.")
        return
    print(f"Creando entorno virtual en {env_dir}…")
    run_command([sys.executable, "-m", "venv", str(env_dir)])


def install_dependencies(env_dir: Path, facefusion_dir: Path, onnxruntime: str = "default"):
    """Instala dependencias en el entorno virtual.

    Args:
        env_dir (Path): Carpeta del entorno virtual.
        facefusion_dir (Path): Carpeta del repositorio facefusion clonado.
        onnxruntime (str): Variante de onnxruntime a usar (default/cuda/rocm/directml/openvino).
    """
    # Determinar ubicaciones de pip y python dentro del entorno
    if platform.system() == "Windows":
        pip_exe = env_dir / "Scripts" / "pip.exe"
        python_exe = env_dir / "Scripts" / "python.exe"
    else:
        pip_exe = env_dir / "bin" / "pip"
        python_exe = env_dir / "bin" / "python"

    print("Actualizando pip, wheel y setuptools…")
    # Es más seguro invocar pip mediante "python -m pip" para evitar errores de modificación de pip.
    run_command([str(python_exe), "-m", "pip", "install", "-U", "pip", "wheel", "setuptools"])

    # Ejecutar instalador de FaceFusion
    installer_script = facefusion_dir / "install.py"
    print(f"Ejecutando instalador de FaceFusion {installer_script}…")
    # Pasar la opción --skip-conda para evitar que el instalador falle cuando conda no está activo.
    # Ejecutar el instalador desde el directorio de facefusion para que encuentre
    # el archivo requirements.txt correctamente. Sin especificar cwd, fallaría
    # al no encontrar requirements.txt en el directorio raíz.
    run_command([
        str(python_exe),
        str(installer_script),
        "--onnxruntime",
        onnxruntime,
        "--skip-conda",
    ], cwd=facefusion_dir)


def write_pinokio_files(repo_root: Path):
    """Escribe los archivos de configuración para Pinokio si no existen.

    Args:
        repo_root (Path): Ruta a la raíz del repositorio.
    """
    # Contenido de pinokio.js
    pinokio_js = (
        "// pinokio.js\n"
        "module.exports = {\n"
        "  version: \"2.0\",\n"
        "  title: \"FaceFusion Libero\",\n"
        "  description: \"Plataforma de manipulación de rostros\",\n"
        "  icon: \"icon.png\",\n"
        "  menu: async (kernel, info) => {\n"
        "    const installed = await info.exists(\"env\");\n"
        "    const running   = await kernel.running(__dirname, \"start.json\");\n"
        "    if (running) return [\n"
        "      { icon:\"fa-solid fa-spin fa-circle-notch\", text:\"Ejecutando\" },\n"
        "      { default:true, icon:\"fa-solid fa-terminal\", text:\"Terminal\", href:\"start.json\", params:{fullscreen:true} }\n"
        "    ];\n"
        "    if (installed) return [\n"
        "      { default:true, icon:\"fa-solid fa-power-off\", text:\"Iniciar\", href:\"start.json\", params:{run:true, fullscreen:true} },\n"
        "      { icon:\"fa-solid fa-plug\", text:\"Reinstalar\", href:\"install.json\" }\n"
        "    ];\n"
        "    return [\n"
        "      { default:true, icon:\"fa-solid fa-plug\", text:\"Instalar\", href:\"install.json\", params:{run:true, fullscreen:true} }\n"
        "    ];\n"
        "  }\n"
        "};\n"
    )

    # Contenido de install.json: notifica que las dependencias ya fueron instaladas manualmente
    install_json = {
        "run": [
            {
                "method": "notify",
                "params": {
                    "html": "<b>Dependencias instaladas manualmente.</b> La aplicación está lista para iniciar.",
                    "href": "start.json"
                }
            }
        ]
    }

    # Contenido de start.json: ejecuta facefusion.py run desde el entorno
    start_json = {
        "run": [
            {
                "method": "shell.start",
                "params": {
                    "message": "env{{path.sep}}{{os.platform()==='win32'?'\\\\Scripts':'/bin'}}{{path.sep}}python facefusion.py run"
                }
            },
            {
                "method": "browser.open",
                "params": {
                    "url": "http://127.0.0.1:7860"
                }
            }
        ]
    }

    # Contenido de session.json: fija la URL que abrirá el botón "Open WebUI"
    session_json = {"url": "http://127.0.0.1:7860"}

    files = {
        "pinokio.js": pinokio_js,
        "install.json": json.dumps(install_json, indent=2),
        "start.json": json.dumps(start_json, indent=2),
        "session.json": json.dumps(session_json, indent=2),
    }
    for filename, content in files.items():
        file_path = repo_root / filename
        if file_path.exists():
            print(f"{filename} ya existe, omitiendo su escritura.")
            continue
        print(f"Creando {filename}…")
        with open(file_path, "w", encoding="utf-8") as fp:
            fp.write(content)


def main():
    repo_root = Path(__file__).parent.resolve()
    facefusion_dir = repo_root / "facefusion"
    env_dir = repo_root / "env"

    # 1. Clonar repositorio facefusion si corresponde
    ensure_facefusion_repo(facefusion_dir)

    # 2. Crear entorno virtual
    ensure_virtualenv(env_dir)

    # 3. Instalar dependencias
    install_dependencies(env_dir, facefusion_dir)

    # 4. Crear archivos de configuración para Pinokio
    write_pinokio_files(repo_root)

    print("\n\033[92mInstalación completada.\033[0m")
    print("Ahora podés abrir Pinokio, importar este repositorio y pulsar 'Iniciar'.")


if __name__ == "__main__":
    main()