#!/usr/bin/env python3
"""
Skript pro převod PDF souborů na PNG obrázky.
Převádí všechny PDF soubory ze složky static/img/human/ na PNG soubory se stejným názvem.
"""

import os
from pathlib import Path
from pdf2image import convert_from_path

def convert_pdfs_to_png(input_dir: str, output_dir: str = None, dpi: int = 300):
    """
    Převede všechny PDF soubory v zadané složce na PNG obrázky.

    Args:
        input_dir: Cesta ke složce s PDF soubory
        output_dir: Cesta pro uložení PNG souborů (výchozí: stejná jako input_dir)
        dpi: Rozlišení pro převod (výchozí: 300 DPI)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else input_path

    if not input_path.exists():
        print(f"Chyba: Složka {input_dir} neexistuje!")
        return

    # Najít všechny PDF soubory
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"Ve složce {input_dir} nebyly nalezeny žádné PDF soubory.")
        return

    print(f"Nalezeno {len(pdf_files)} PDF souborů ke konverzi...")

    for pdf_file in pdf_files:
        try:
            print(f"Zpracovávám: {pdf_file.name}...", end=" ")

            # Převést PDF na obrázky
            images = convert_from_path(str(pdf_file), dpi=dpi)

            # Pro každou stránku v PDF
            for i, image in enumerate(images):
                # Vytvořit název výstupního souboru
                if len(images) == 1:
                    # Pokud má PDF jen jednu stránku
                    output_filename = pdf_file.stem + ".png"
                else:
                    # Pokud má PDF více stránek, přidat číslo stránky
                    output_filename = f"{pdf_file.stem}_page_{i+1}.png"

                output_file = output_path / output_filename

                # Uložit jako PNG
                image.save(str(output_file), "PNG")

            print(f"✓ Hotovo ({len(images)} stránek)")

        except Exception as e:
            print(f"✗ Chyba: {e}")

    print(f"\nKonverze dokončena! PNG soubory uloženy do: {output_path}")


if __name__ == "__main__":
    # Cesta k složce s PDF soubory
    input_directory = "static/img/human"

    # Spustit konverzi
    convert_pdfs_to_png(input_directory, dpi=300)
