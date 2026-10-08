"""Mix caller-selected constant gains; no automatic balance or normalization."""
from pathlib import Path
import numpy as np
import soundfile as sf

def mix(vocal_wav, accomp_wav, out_wav, *, vocal_gain_db, accomp_gain_db):
    vocal,sr=sf.read(vocal_wav,dtype='float64',always_2d=True)
    backing,bsr=sf.read(accomp_wav,dtype='float64',always_2d=True)
    if sr!=bsr: raise ValueError('Align sample rates before mixing')
    channels=max(vocal.shape[1],backing.shape[1]);frames=max(len(vocal),len(backing))
    def expand(x):
        if x.shape[1]==1: x=np.repeat(x,channels,axis=1)
        if x.shape[1]!=channels: raise ValueError('Incompatible channel counts')
        return np.pad(x,((0,frames-len(x)),(0,0)))
    if not np.isfinite([vocal_gain_db,accomp_gain_db]).all(): raise ValueError('Finite selected gains required')
    result=expand(vocal)*10**(vocal_gain_db/20)+expand(backing)*10**(accomp_gain_db/20)
    if not np.isfinite(result).all(): raise ValueError('Non-finite audio')
    peak=float(np.max(abs(result),initial=0))
    if peak>=1: raise ValueError('Mix would clip; choose and record lower fixed gains')
    Path(out_wav).parent.mkdir(parents=True,exist_ok=True);sf.write(out_wav,result,sr,subtype='PCM_24')
    return dict(out=str(out_wav),sample_rate=sr,frames=frames,peak=peak,vocal_gain_db=vocal_gain_db,accomp_gain_db=accomp_gain_db,normalized=False)
