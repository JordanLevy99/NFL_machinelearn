import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder
import scipy.stats as sci
import seaborn as sns
from sklearn.preprocessing import StandardScaler

import math
import os

pd.set_option('display.max_columns', 500)

positions = {
    'QB': ['Name', 'Team', 'Yr', 'Bye', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds',
           'Rush TDs', 'Proj FPts'],
    'RB': ['Name', 'Team', 'Yr', 'Bye', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts'],
    'WR': ['Name', 'Team', 'Yr', 'Bye', 'Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
    'TE': ['Name', 'Team', 'Yr', 'Bye', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts']}
pd.set_option('display.width', 10000)

def dataframe_creator(pos, datatype, train=True, start_yr=2010, end_yr=2019):
    '''
    Creates a pandas dataframe for specified csv file in the 2010 to 2018 database with a proper header and some minor adjustments
    '''
    if train:
        filename = 'Total_Data/{}-{}/{}_{}.csv'.format(start_yr, end_yr, pos, datatype)
    else:
        filename = 'Total_Data/Test_Data/{}/{}_projected.csv'.format(end_yr, pos)

    total_lines = []
    with open(filename, 'r') as f:
        column_names = positions[pos]
        for line in f:
            line_lst = line.split(',')
            if train == False:
                line_lst[3] = 16
            if float(line_lst[2]) < start_yr or float(line_lst[2]) > end_yr:
                continue
            for str in range(len(line_lst)):
                try:
                    line_lst[str] = float(line_lst[str])
                except ValueError:
                    line_lst[str] = line_lst[str].rstrip()
                    pass
            if 'actual' in filename:
                line_lst = line_lst[:-1]
                column_names[3] = 'GP'
                if pos == 'RB':
                    line_lst = line_lst[0:7] + line_lst[8:]
                if pos == 'WR' or pos == 'TE':
                    line_lst = line_lst[0:4] + line_lst[5:]
            total_lines.append(line_lst)
    return pd.DataFrame(total_lines, columns=column_names)

def merging_proj_with_actual(pos, start_yr=2010, end_yr=2018):
    pos_proj = dataframe_creator(pos, 'projected', True, start_yr, end_yr)
    pos_actual = dataframe_creator(pos, 'actual', True, start_yr, end_yr)

    pos_train = pos_proj.merge(pos_actual, how='inner', left_on=['Name', 'Yr'], right_on=['Name', 'Yr'])
    drop_list = [i for i in pos_train.columns if 'y' in i and i != 'Proj FPts_y']
    drop_list_bye = drop_list + ['Bye']
    print(pos_train.columns)
    try:
        pos_train = pos_train.drop(drop_list_bye, axis=1)
    except KeyError:
        pos_train = pos_train.drop(drop_list, axis=1)

    cols = pos_train.columns.tolist()
    cols2 = cols[:3]
    cols2.append(cols[-2])
    cols2 = cols2 + cols[3:-2]
    cols2.append(cols[-1])
    pos_train = pos_train[cols2]
    pos_train.columns = positions[pos] + ['Act FPts']
    return pos_train
def gp_stats_adjuster(training_data: pd.DataFrame) -> pd.DataFrame:
    """Adjust actual fantasy points based on games played and remove outliers.
    
    This function adjusts the actual FPTs so that they scale up to 16 games if a player 
    played between 13-15 games. Any player who played less than 13 games will be 
    disregarded. It also removes statistical outliers based on fantasy points.
    
    Args:
        training_data: DataFrame containing player stats with GP (games played) column
        
    Returns:
        DataFrame with adjusted fantasy points and outliers removed
    """
    # Filter for players with more than 13 games
    training_data = training_data[training_data['GP'] > 13].copy()
    
    # Scale fantasy points to 16-game season
    training_data['Act FPts'] = training_data.apply(
        lambda row: (16 / row['GP'] * row['Act FPts']), 
        axis=1
    )
    
    # Remove outliers using IQR method
    Q1 = training_data['Act FPts'].quantile(0.25)
    Q3 = training_data['Act FPts'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    training_data = training_data[
        (training_data['Act FPts'] >= lower_bound) & 
        (training_data['Act FPts'] <= upper_bound)
    ]
    
    return training_data

def standardize(data):
    mean_data = data.groupby('Yr').transform(np.mean)
    std_data = data.groupby('Yr').transform(np.std)
    scale = ((data - mean_data) / std_data).drop(['Name', 'Team', 'Yr'], axis=1).fillna(0)
    return scale

def machine_learning(training_data, testing_data, pos, year, n):
    hidden = int(95 * len(positions[pos]))
    if pos == 'TE':
        hidden *= 0.7
    mlp = MLPRegressor(hidden_layer_sizes=int(100), activation='relu', alpha=0.001, max_iter=300)
    sts = StandardScaler()
    
    drop_cols = ['Name', 'Team', 'Yr']
    train_filt = training_data.drop(drop_cols+['Proj FPts'], axis=1)
    sts.fit(train_filt)
    ml_train_data_x = sts.transform(train_filt)
    ml_train_data_y = training_data['Act FPts']
    test_filt = testing_data.drop(drop_cols, axis=1)
    print(train_filt.columns)
    print(test_filt.columns)
    ml_test_data = pd.DataFrame(data=sts.transform(test_filt), columns=test_filt.columns)

    mlp.fit(ml_train_data_x, ml_train_data_y)
    ml_predictions = mlp.predict(ml_test_data)
    playernames = testing_data.loc[:, 'Name'].values
    predicted = test_filt['Proj FPts'].values

    pd.set_option('display.max_rows', 1000)
    players = pd.DataFrame(np.column_stack([playernames, predicted, ml_predictions]),
                           columns=['Player', 'Projection', 'My Computed Score'])
    
    if not os.path.exists(f'ML_projections/{year}'):
        os.makedirs(f'ML_projections/{year}')
    filename = f'ML_projections/{year}/{pos}_{year}_{n}.csv'
    players.to_csv(filename, index=False)
    return players

def data_vis(training_data, testing_data, pos):
    pos_stats = {
        'QB': ['Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
        'RB': ['Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts'],
        'WR': ['Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
        'TE': ['Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts']}

if __name__ == '__main__':
    for n in range(26):
        for position in positions.keys():
            start_yr = 2018
            end_yr = 2023
            training_data = gp_stats_adjuster(merging_proj_with_actual(position, start_yr, end_yr))
            testing_data = dataframe_creator(position, 'projected', False, start_yr=start_yr, end_yr=end_yr)
            machine_learning(training_data, testing_data, position, end_yr, n)
