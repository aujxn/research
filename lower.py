import os
from itertools import chain
from glob import glob

for filename in os.listdir('./'):
    if filename.endswith(".csv"):
        f = open(filename, 'r')
        text = f.read()

        lines = [text.lower() for line in filename]
        with open(filename, 'w') as out:
            out.writelines(lines)
