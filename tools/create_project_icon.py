"""Draw the original geometric project badge without game artwork."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
out = root / "assets"
out.mkdir(exist_ok=True)
s = 3
image = Image.new("RGB", (400*s, 400*s), "#101923")
draw = ImageDraw.Draw(image)
def box(coords, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(tuple(v*s for v in coords), radius=radius*s,
                           fill=fill, outline=outline, width=width*s)
def polygon(points, fill):
    draw.polygon([(x*s,y*s) for x,y in points], fill=fill)
box((22,22,378,378),40,"#172431","#ad8546",3)
box((108,64,318,292),19,"#1c3544","#617e8b",5)
box((73,99,283,327),19,"#263f4b","#e3b868",6)
polygon([(121,153),(147,137),(166,159),(190,159),(209,137),(235,153),
         (253,198),(224,211),(214,191),(214,274),(142,274),(142,191),(132,211),(103,198)],"#72d7bf")
draw.line([(178*s,167*s),(178*s,256*s)],fill="#284f50",width=5*s)
box((235,268,345,344),14,"#172431","#e3b868",5)
draw.line([(256*s,306*s),(275*s,323*s),(326*s,285*s)],fill="#f4d18a",width=8*s)
image.resize((400,400),Image.Resampling.LANCZOS).save(out/"project-icon.png")
print(out/"project-icon.png")
