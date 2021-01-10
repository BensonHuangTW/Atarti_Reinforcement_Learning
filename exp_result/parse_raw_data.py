import os
import pandas as pd
import numpy as np

def parse_log(log_df):
    result_df = pd.DataFrame()
    result_df['step'] = log_df['step']
    result_df.set_index('step')
    tags = log_df['tag'].unique()
    for tag in tags:
        result_df[tag] = np.nan
    for index, row in log_df.iterrows():
        print("\r Convert tensorboard data into dataframe. Progress: {}/{}".format(index, len(log_df)), end='')
        result_df.loc[row['step'], row['tag']] = row['value']
    return result_df.copy()

for file_name in os.listdir("./raw"):
    raw_log_data = pd.read_csv("./raw/{}".format(file_name))
    print("procces the file:\n", file_name)
    processed_df = parse_log(raw_log_data)
    processed_df.to_csv("./processed/{}".format(file_name), index=False)