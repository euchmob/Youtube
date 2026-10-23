"""Remove burned-in white caption text from frames by masking letter-shaped white blobs and inpainting."""
import cv2, numpy as np

def text_mask(img, bands):
    h, w = img.shape[:2]
    b, g, r = cv2.split(img.astype(np.int16))
    mn = np.minimum(np.minimum(b, g), r); mx = np.maximum(np.maximum(b, g), r)
    white = ((mn > 225) & (mx - mn < 25)).astype(np.uint8)
    keep = np.zeros_like(white)
    for y0, y1 in bands:
        a, z = int(y0 * h), int(y1 * h)
        keep[a:z] = white[a:z]
    n, lab, st, _ = cv2.connectedComponentsWithStats(keep, 8)
    out = np.zeros_like(keep)
    cand = [i for i in range(1, n) if st[i][3] <= 48 and st[i][2] <= 90 and st[i][4] >= 4]  # letter-sized
    cy = {i: st[i][1] + st[i][3] / 2 for i in cand}
    for i in cand:
        # real caption letters sit in a row with other letters; stray highlights in the art don't
        if sum(abs(cy[i] - cy[j]) < 14 for j in cand) >= 4:
            out[lab == i] = 1
    # join letters into words, then grow to cover the dark outline/shadow
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (31, 21)))
    out = cv2.dilate(out, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    return out * 255

def clean(img, bands):
    m = text_mask(img, bands)
    return cv2.inpaint(img, m, 9, cv2.INPAINT_TELEA), m

if __name__ == "__main__":
    import sys
    tests = [("b21", [(0.70, 0.84)]), ("r3", [(0.10, 0.25), (0.66, 0.78)]),
             ("n2", [(0.24, 0.36), (0.66, 0.78)]), ("w1", [(0.12, 0.19), (0.66, 0.78)])]
    outs = []
    for name, bands in tests:
        img = cv2.imread(f"work/{name}.png")
        c, m = clean(img, bands)
        outs.append(c)
    cv2.imwrite("work/detext_test.png", cv2.resize(np.hstack(outs), None, fx=1/3, fy=1/3))
