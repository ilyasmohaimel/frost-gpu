import cv2,numpy as np,json,pathlib
import os
p=pathlib.Path(os.environ.get('FROST_FILM_CACHE',str(pathlib.Path.home()/'.local/share/frost-gpu-film')))/'online-reference/asus-top.png';im=cv2.imread(str(p));hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);mask=((hsv[:,:,1]>58)&(hsv[:,:,2]>45)).astype(np.uint8)*255
roi=np.zeros_like(mask);roi[451:846,335:1265]=mask[451:846,335:1265];roi=cv2.morphologyEx(roi,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
contours,_=cv2.findContours(roi,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);keys=[]
for c in contours:
 x,y,w,h=cv2.boundingRect(c);area=cv2.contourArea(c)
 if 23<w<305 and 13<h<125 and area>300:
  poly=cv2.approxPolyDP(c,2.2,True)[:,0,:].tolist();keys.append({'bbox':[x,y,w,h],'area':area,'polygon':poly})
# The translucent WASD group connects in the colour mask. Trace those five outlines separately.
keys=[k for k in keys if not(k['bbox'][2]>200 and k['bbox'][3]>70)]
for x,y,w,h in [(353,656,94,50),(493,600,53,50),(450,656,54,50),(507,656,54,50),(564,656,54,50)]:
 r=4;poly=[[x+r,y],[x+w-r,y],[x+w,y+r],[x+w,y+h-r],[x+w-r,y+h],[x+r,y+h],[x,y+h-r],[x,y+r]];keys.append({'bbox':[x,y,w,h],'area':w*h,'polygon':poly})
# Pixel-space silhouettes verify the non-rectangular Enter and all other physical outlines.
occupancy=np.zeros((1176,1600),np.uint16);overlaps=0
for k in keys:
 one=np.zeros((1176,1600),np.uint8);cv2.fillPoly(one,[np.array(k['polygon'],np.int32)],1);overlaps+=int(np.count_nonzero((occupancy>0)&(one>0)));occupancy+=one
if overlaps:raise RuntimeError('Traced key silhouettes overlap: '+str(overlaps))
print('Silhouette overlap pixels:',overlaps)
keys.sort(key=lambda k:(int((k['bbox'][1]-450)/40),k['bbox'][0]));out=pathlib.Path(__file__).with_name('traced-keys.json');out.write_text(json.dumps(keys,indent=2));print('Traced keys',len(keys));print([k['bbox'] for k in keys])
