from cx_Freeze import setup, Executable

# Opções de compilação
build_exe_options = {
    "packages": ["os", "platform", "sqlite3", "shutil", "time", "zipfile", "PyQt5", "datetime", "threading"],
    "include_files": ["backup.ui","agendar.ui", "icon.png"],  # Inclui o arquivo UI e o ícone
}


setup(
    name="Ferramenta de Backup",
    version="0.1",
    description="Aplicativo para agendar e realizar backups",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",  # Arquivo principal    
            base="Win32GUI", 
            icon="",    # Ícone .ico
            targetName="BackupApp.exe"  # Nome personalizado
        )
    ]
)

# Para gerar o executável
# python setup.py build
