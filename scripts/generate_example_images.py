from PIL import Image, ImageDraw, ImageFont


def create_image(text, filename):
    width, height = 300, 200
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    # Use default font
    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, fill="black", font=font)
    img.save(filename)


if __name__ == "__main__":
    for i in range(1, 4):
        fname = f"static/img/example_image_{i}.png"
        create_image(f"example_image_{i}", fname)
