import numpy as np, wave
SR=44100; D=27.0
N=int(SR*D); out=np.zeros(N)
def add(sig,t,gain=1.0):
    i=int(t*SR); j=min(N,i+len(sig))
    if i<N: out[i:j]+=sig[:j-i]*gain
def env(n,a=.005,r=.2):
    e=np.ones(n); na=int(a*SR); e[:na]=np.linspace(0,1,na); nr=int(r*SR); e[-nr:]*=np.linspace(1,0,nr); return e
def tone(f,d,kind='sin'):
    t=np.arange(int(d*SR))/SR
    s=np.sin(2*np.pi*f*t)
    if kind=='tri': s=2/np.pi*np.arcsin(np.sin(2*np.pi*f*t))
    return s
def pop(t,f=600,g=.35):
    d=.18; tt=np.arange(int(d*SR))/SR
    fr=f*(1+1.5*np.exp(-tt*30)); s=np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-tt*18)
    add(s,t,g)
def whoosh(t,d=.6,g=.12,up=True):
    n=int(d*SR); x=np.random.randn(n)
    # simple lowpass sweep via moving average of varying width
    k=np.cumsum(x); y=np.zeros(n)
    for i,w in enumerate(np.linspace(300,20,n) if up else np.linspace(20,300,n)):
        w=int(w); y[i]=(k[i]-k[max(0,i-w)])/w if w>0 else x[i]
    y/=np.abs(y).max()+1e-9
    e=np.sin(np.linspace(0,np.pi,n))**2
    add(y*e,t,g)
def chime(t,f=880,g=.28):
    for k,m in enumerate([1,1.5,2]):
        s=tone(f*m,.5)*np.exp(-np.arange(int(.5*SR))/SR*7)
        add(s,t+k*.07,g*(.8**k))
def tick(t,g=.2):
    d=.05; tt=np.arange(int(d*SR))/SR
    add(np.random.randn(len(tt))*np.exp(-tt*120),t,g)
# --- BGM: Am F C G, 90bpm, 4 beats per chord
bpm=90; beat=60/bpm
chords=[[220,261.63,329.63],[174.61,220,261.63],[261.63,329.63,392],[196,246.94,293.66]]
bass=[110,87.31,130.81,98]
nb=int(D/beat)+1
for b in range(nb):
    t=b*beat; ci=(b//4)%4
    if b%4==0:
        for f in chords[ci]:
            s=tone(f,beat*4,'tri')*env(int(beat*4*SR),.4,.8); add(s,t,.05)
        s=tone(bass[ci],beat*4)*env(int(beat*4*SR),.05,.5); add(s,t,.12)
    # soft kick
    if b%2==0:
        tt=np.arange(int(.25*SR))/SR; fr=50+80*np.exp(-tt*25); add(np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-tt*12),t,.22)
    # hat
    for h in (.5,):
        tt=np.arange(int(.04*SR))/SR; add(np.random.randn(len(tt))*np.exp(-tt*150),t+h*beat,.04)
    # arpeggio pluck
    f=chords[ci][b%3]*2
    tt=np.arange(int(.3*SR))/SR; add(np.sin(2*np.pi*f*tt)*np.exp(-tt*9),t+.25*beat,.05)
# intro/outro fade
fade=np.ones(N); fade[:int(.3*SR)]=np.linspace(0,1,int(.3*SR)); fade[-int(1.2*SR):]=np.linspace(1,0,int(1.2*SR)); out*=fade
# --- SFX synced to video
for t,f in [(.1,300),(.6,500),(1.0,560),(1.5,700)]: pop(t,f)
whoosh(.1,.5,.1)
pop(3.4,520); whoosh(4.0,1.8,.10); pop(5.9,420,.4)
pop(7.2,560); pop(7.4,620)
for i in range(4):
    a=8.2+i*2.2; pop(a,480); chime(a+.9,[880,988,1047,1175][i])
pop(16.9,700)
pop(17.7,520); whoosh(18.0,.8,.14,up=False)
for i in range(4): tick(19.0+i*.35+.3,.2)
chime(19.6,1047); pop(20.1,500)
pop(22.2,520); pop(22.5,300,.4)
for t in (23.3,23.65): tick(t,.35)
pop(24.0,520); pop(24.6,560); pop(25.0,600)
whoosh(25.2,.5,.12); chime(25.4,1047,.35); chime(25.9,1319,.25)
out=np.tanh(out*1.6)*.8
pcm=(out*32767).astype(np.int16)
with wave.open('audio.wav','wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
