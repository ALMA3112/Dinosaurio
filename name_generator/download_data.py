"""Descarga la lista publica de nombres de dinosaurios (dataset 'Dinosaurus Island'
del curso Sequence Models de deeplearning.ai) y la guarda como data/dinos.csv.

Uso:  python name_generator/download_data.py
Requiere internet. Si falla, descargue el archivo manualmente desde la URL y
pase la ruta:  python name_generator/download_data.py --local ruta/dinos.txt
"""
import argparse
import csv
import urllib.request
from pathlib import Path

URL = ("https://raw.githubusercontent.com/ArkaSarkar19/"
       "Character-level-language-model-Dinosaurus-Island/master/dinos.txt")
OUT = Path(__file__).parent / "data" / "dinos.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="ruta a un dinos.txt ya descargado")
    args = ap.parse_args()

    if args.local:
        text = Path(args.local).read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(URL, timeout=30) as r:
            text = r.read().decode("utf-8")

    names = [line.strip() for line in text.splitlines() if line.strip()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name"])
        for n in names:
            w.writerow([n])
    print(f"{len(names)} filas guardadas en {OUT}")
    print("Nota: el archivo crudo tiene ruido (duplicados, palabras que no son nombres, "
          "nombres pegados). La limpieza se hace en el preprocesamiento (Fase 1).")


if __name__ == "__main__":
    main()
