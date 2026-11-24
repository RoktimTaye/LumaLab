from pathlib import Path
from PIL import Image, ImageDraw
p=Path(__file__).parent
files=sorted(p.glob('page-*.png'),key=lambda x:int(x.stem.split('-')[-1]))
thumb_w,thumb_h=220,330
cols=4
rows=(len(files)+cols-1)//cols
out=Image.new('RGB',(cols*thumb_w,rows*(thumb_h+25)),'#ddd')
d=ImageDraw.Draw(out)
for i,f in enumerate(files):
    im=Image.open(f).convert('RGB')
    im.thumbnail((thumb_w-10,thumb_h-10))
    x=(i%cols)*thumb_w+(thumb_w-im.width)//2
    y=(i//cols)*(thumb_h+25)
    out.paste(im,(x,y))
    d.text(((i%cols)*thumb_w+8,y+thumb_h),str(i+1),fill='black')
out.save(p/'contact.png')
