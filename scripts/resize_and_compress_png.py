#!/usr/bin/env python3
"""
Skript pro zmenšení a kompresi PNG obrázků.
Zmenší všechny PNG soubory ze složky static/img/human/ na šířku 2000px
a uloží je s příponou _small.png s optimalizovanou kompresí.
"""

import os
from pathlib import Path
from PIL import Image

def resize_and_compress_png(input_dir: str, max_width: int = 2000, quality: int = 85):
    """
    Zmenší a zkomprimuje všechny PNG soubory v zadané složce.

    Args:
        input_dir: Cesta ke složce s PNG soubory
        max_width: Maximální šířka v pixelech (výchozí: 2000)
        quality: Úroveň komprese při ukládání (výchozí: 85)
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Chyba: Složka {input_dir} neexistuje!")
        return

    # Najít všechny PNG soubory (kromě těch s _small)
    png_files = [f for f in input_path.glob("*.png") if not f.stem.endswith("_small")]

    if not png_files:
        print(f"Ve složce {input_dir} nebyly nalezeny žádné PNG soubory.")
        return

    print(f"Nalezeno {len(png_files)} PNG souborů ke zpracování...")
    print(f"Nastavení: max šířka = {max_width}px, optimalizace komprese\n")

    total_original_size = 0
    total_compressed_size = 0

    for png_file in png_files:
        try:
            # Načíst obrázek
            with Image.open(png_file) as img:
                original_size = os.path.getsize(png_file)
                total_original_size += original_size

                # Získat původní rozměry
                original_width, original_height = img.size

                print(f"Zpracovávám: {png_file.name} ({original_width}x{original_height})...", end=" ")

                # Vypočítat nové rozměry (zachovat poměr stran)
                if original_width > max_width:
                    ratio = max_width / original_width
                    new_width = max_width
                    new_height = int(original_height * ratio)

                    # Zmenšit obrázek s vysokou kvalitou
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    # Pokud je obrázek menší než max_width, nechat původní rozměry
                    new_width, new_height = original_width, original_height
                    img_resized = img

                # Vytvořit název výstupního souboru
                output_filename = png_file.stem + "_small.png"
                output_file = input_path / output_filename

                # Uložit s optimalizací
                # Pro PNG použijeme optimize=True pro lepší kompresi
                img_resized.save(
                    str(output_file),
                    "PNG",
                    optimize=True,
                    compress_level=9  # Maximální komprese (0-9)
                )

                # Získat velikost výstupního souboru
                compressed_size = os.path.getsize(output_file)
                total_compressed_size += compressed_size

                # Vypočítat úsporu
                reduction = ((original_size - compressed_size) / original_size) * 100

                print(f"✓ {new_width}x{new_height} | "
                      f"{original_size / 1024:.0f}KB → {compressed_size / 1024:.0f}KB "
                      f"({reduction:.1f}% úspora)")

        except Exception as e:
            print(f"✗ Chyba: {e}")

    # Celková statistika
    print("\n" + "="*70)
    print(f"Konverze dokončena!")
    print(f"Celková původní velikost: {total_original_size / (1024*1024):.2f} MB")
    print(f"Celková komprimovaná velikost: {total_compressed_size / (1024*1024):.2f} MB")
    total_reduction = ((total_original_size - total_compressed_size) / total_original_size) * 100
    print(f"Celková úspora: {total_reduction:.1f}%")
    print("="*70)


if __name__ == "__main__":
    # Cesta k složce s PNG soubory
    input_directory = "static/img/human"

    # Spustit zpracování
    resize_and_compress_png(input_directory, max_width=2000)
