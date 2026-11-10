import sys, numpy as np
from PIL import Image
from ftlab import *
def line(font, text, pos, mode='gray', H=16, base=12, W=None, xfuns=None):
    W = W or int(sum(font.metrics(c)[1] for c in text)) + 6
    cv = np.zeros((H, W, 3) if mode=='rgb' else (H, W))
    for i,(c,p) in enumerate(zip(text,pos)):
        whole = int(np.floor(p)); s = (p-whole)*64
        f = (xfuns[i] if xfuns else (lambda xs, s=s: xs + s))
        r = font.render(c, f, mode)
        if r is None: continue
        a,l,t = r; a=a/255.0
        y0=base-t; x0=2+whole+l
        sl = cv[y0:y0+a.shape[0], x0:x0+a.shape[1]]
        np.maximum(sl, a, out=sl)
    return cv
if __name__=='__main__':
    f=Font(REG,11)
    for t in ['Contrast:']:
        print([ (c,f.metrics(c)) for c in t])
        p=wine_positions(f,t); print(p)
        print(ideal_positions(f,t))
        for mode in ['gray','rgb']:
            px=to_pixels(line(f,t,p,mode),mode)
            Image.fromarray(px.astype(np.uint8)).resize((px.shape[1]*12,px.shape[0]*12),Image.NEAREST).save(f'q_{mode}.png')
