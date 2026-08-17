# app.py (Entrypoint para Streamlit Cloud)
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
desafio_dir = os.path.join(base_dir, "Desafio_4")
if not os.path.exists(desafio_dir):
    desafio_dir = os.path.join(base_dir, "Desafio 4")

if desafio_dir not in sys.path:
    sys.path.insert(0, desafio_dir)
os.chdir(desafio_dir)

with open(os.path.join(desafio_dir, "app.py"), encoding="utf-8") as app_file:
    code = compile(app_file.read(), os.path.join(desafio_dir, "app.py"), "exec")
    exec(code, globals())
