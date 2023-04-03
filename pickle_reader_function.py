import gzip
import pickle
import pandas as pd
import numpy as np
import csv
    
def read_pickle_file(file):
    with gzip.open(file, 'rb') as f:
        eco = pd.read_pickle(f)
    return eco
