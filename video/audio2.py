import numpy as np, wave, json, sys
src,outwav=sys.argv[1],sys.argv[2]
J=json.load(open(src)); D=J['D']; EV=J['events']
SR=44100; N=int(SR*D); out=np.zeros(N)
rng=np.random.default_rng(1)
def add(sig,t,gain=1.0):
    i=int(t*SR); j=min(N,i+len(sig))
    if 0<=i<N: out[i:j]+=sig[:j-i]*gain
def env(n,a=.005,r=.2):
    e=np.ones(n); na=int(a*SR); e[:na]=np.linspace(0,1,na); nr=int(r*SR); e[-nr:]*=np.linspace(1,0,nr); return e
def tone(f,d,kind='sin'):
    t=np.arange(int(d*SR))/SR
    return 2/np.pi*np.arcsin(np.sin(2*np.pi*f*t)) if kind=='tri' else np.sin(2*np.pi*f*t)
def pop(t,f=600,g=.35):
    tt=np.arange(int(.18*SR))/SR
    fr=f*(1+1.5*np.exp(-tt*30)); add(np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-tt*18),t,g)
def whoosh(t,d=.6,g=.12,up=True):
    n=int(d*SR); x=rng.standard_normal(n); k=np.cumsum(x); y=np.zeros(n)
    ws=np.linspace(300,20,n) if up else np.linspace(20,300,n)
    for i,w in enumerate(ws.astype(int)):
        y[i]=(k[i]-k[max(0,i-w)])/w if w>0 else x[i]
    y/=np.abs(y).max()+1e-9; add(y*np.sin(np.linspace(0,np.pi,n))**2,t,g)
def chime(t,f=880,g=.28):
    for k,m in enumerate([1,1.5,2]):
        s=tone(f*m,.5)*np.exp(-np.arange(int(.5*SR))/SR*7); add(s,t+k*.07,g*(.8**k))
def tick(t,g=.2):
    tt=np.arange(int(.05*SR))/SR; add(rng.standard_normal(len(tt))*np.exp(-tt*120),t,g)
def warn(t,g=.3):
    tt=np.arange(int(.25*SR))/SR; add(np.sin(2*np.pi*330*tt)*np.exp(-tt*10)*np.sign(np.sin(2*np.pi*14*tt)+1.5),t,g*.8)
bpm=90; beat=60/bpm
chords=[[220,261.63,329.63],[174.61,220,261.63],[261.63,329.63,392],[196,246.94,293.66]]
bass=[110,87.31,130.81,98]
for b in range(int(D/beat)+1):
    t=b*beat; ci=(b//4)%4
    if b%4==0:
        for f in chords[ci]: add(tone(f,beat*4,'tri')*env(int(beat*4*SR),.4,.8),t,.05)
        add(tone(bass[ci],beat*4)*env(int(beat*4*SR),.05,.5),t,.12)
    if b%2==0:
        tt=np.arange(int(.25*SR))/SR; fr=50+80*np.exp(-tt*25); add(np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-tt*12),t,.22)
    tt=np.arange(int(.04*SR))/SR; add(rng.standard_normal(len(tt))*np.exp(-tt*150),t+.5*beat,.04)
    f=chords[ci][b%3]*2; tt=np.arange(int(.3*SR))/SR; add(np.sin(2*np.pi*f*tt)*np.exp(-tt*9),t+.25*beat,.05)
fade=np.ones(N); fade[:int(.3*SR)]=np.linspace(0,1,int(.3*SR)); fade[-int(1.2*SR):]=np.linspace(1,0,int(1.2*SR)); out*=fade
for e in EV:
    t=e['t']; k=e['type']
    if k=='pop': pop(t,e.get('f',600),e.get('g',.35))
    elif k=='whoosh': whoosh(t,e.get('d',.6),e.get('g',.12),e.get('up',True))
    elif k=='chime': chime(t,e.get('f',880),e.get('g',.28))
    elif k=='tick': tick(t,e.get('g',.2))
    elif k=='warn': warn(t)
out=np.tanh(out*1.6)*.8
pcm=(out*32767).astype(np.int16)
with wave.open(outwav,'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
