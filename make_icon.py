from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# dark rounded tile (matches app theme)
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=52, fill=(30, 33, 38, 255))
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=52,
                    outline=(77, 163, 255, 255), width=6)

# play triangle = video
d.polygon([(70, 78), (70, 178), (150, 128)], fill=(77, 163, 255, 255))

# wave bars = audio
for x0, y0, x1, y1 in [(168, 96, 184, 160), (192, 76, 208, 180), (216, 104, 232, 152)]:
    d.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=(111, 182, 255, 255))

img.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                            (64, 64), (128, 128), (256, 256)])
print("icon.ico created next to this script")