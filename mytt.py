import numpy as np
import pandas as pd

config = [12, 26, 9]

def RD(N,D=3):
    return np.round(N,D)

def EMA(S,N):  
    return pd.Series(S).ewm(span=N, adjust=False).mean().values

def MACD(CLOSE,SHORT=config[0],LONG=config[1],M=config[2]):
    DIF = EMA(CLOSE,SHORT)-EMA(CLOSE,LONG);  
    DEA = EMA(DIF,M);      MACD=(DIF-DEA)*2
    return RD(DIF),RD(DEA),RD(MACD)
