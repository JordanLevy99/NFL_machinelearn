import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder
import scipy.stats as sci
import seaborn as sns
from sklearn.preprocessing import StandardScaler



import math
#import csv
#import os.path
#import os, errno

positions = {'QB':['Name', 'Team', 'Yr', 'Bye', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
             'RB':['Name', 'Team', 'Yr', 'Bye', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts'],
             'WR':['Name', 'Team', 'Yr', 'Bye', 'Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
             'TE':['Name', 'Team', 'Yr', 'Bye', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts']}
pd.set_option('display.width', 10000)


def dataframe_creator(pos, datatype, train = True, start_yr = 2010, end_yr = 2018):
    '''
    Creates a pandas dataframe for specified csv file in the 2010 to 2018 database with a proper header and some minor adjustments
    '''
    if train:
        filename = 'Total_Data/2010-2018/{}_{}.csv'.format(pos, datatype)    # the filename of the specified position plus actual vs projected data
    else:
        filename = 'Total_Data/Test_Data/{}/{}_projected.csv'.format(start_yr, pos)    # the filename of the specified position with projected data for the current year

    total_lines = []  # the outer list to be appended to
    with open(filename, 'r') as f:  # opens specified file as f
        column_names = positions[pos]   # used to name columns for the specified file
        for line in f:  # iterates through each line of file f
            line_lst = line.split(',')  # splits each line into a list
            #print(line_lst)
            if train == False:  # if using testing data, set games played to 16
                line_lst[3] = 16
            if float(line_lst[2]) < start_yr or float(line_lst[2]) > end_yr:
                continue
            for str in range(len(line_lst)):    # iterates through each item in the list
                try:
                    line_lst[str] = float(line_lst[str])    # if the string can be converted to a float, convert it into a float
                except ValueError:  # if the string produces a ValueError when converting to float...
                    line_lst[str] = line_lst[str].rstrip()  # strip the string of any special characters e.g. '\n' and continue
                    pass
            if 'actual' in filename:    # if the file is actual data...
                line_lst = line_lst[:-1]    # get rid of the last item in the list as it contains FPPG which is not needed
#                if pos == 'QB' or pos == 'RB':  # if the position is either QB or RB...
                column_names[3] = 'GP' # change the column name from Bye to GP to accurately represent what they are in the original data
                if pos == 'RB':
                    #print(line_lst)
                    line_lst = line_lst[0:7]+line_lst[8:]   # Gets rid of receiving targets from actual data, an unnecessary statistic
                if pos == 'WR' or pos == 'TE':
                    #print(line_lst)
                    line_lst = line_lst[0:4]+line_lst[5:]   # Gets rid of receiving targets from actual data, an unnecessary statistic
                #if pos == 'TE':
                 #   line_lst = line_lst[0:4]+line_lst[5:]   # Gets rid of receiving targets from actual data, an unnecessary statistic



            #print(line_lst)
            total_lines.append(line_lst)    # append updated line/list to parent list
        #with open('placeholder.csv', 'w') as f2:
        #   print(f.)
    #print(pd.DataFrame(total_lines, columns= positions[pos]))   # convert parent list to pandas data frame and print
    return pd.DataFrame(total_lines, columns= column_names) # returns a pandas dataframe with the proper columns as given by the positions dictionary @ line __


def merging_proj_with_actual(pos, start_yr = 2010, end_yr = 2018):
    pos_proj = dataframe_creator(pos, 'projected', True, start_yr, end_yr)
    pos_actual = dataframe_creator(pos, 'actual', True, start_yr, end_yr)


    pos_train = pos_proj.merge(pos_actual,how='inner', left_on=['Name', 'Yr'],right_on=['Name','Yr'])
    drop_list = ['Bye']+[i for i in pos_train.columns if 'y' in i and i != 'Proj FPts_y']
    #gp = qb_train.pop('GP')
    #print(gp.values)
    pos_train = pos_train.drop(drop_list, axis=1)#.insert(2, column='GP', value=gp)
    cols = pos_train.columns.tolist()    # this turns the columns of the training data into a list, so that I could rearrange the order of the columns
                                        # print training data here to see what I changed
    cols2 = cols[:3]
    cols2.append(cols[-2])
    #print(cols[3:-2])
    cols2 = cols2+cols[3:-2]
    cols2.append(cols[-1])
    pos_train = pos_train[cols2]
    pos_train.columns = positions[pos]+['Act FPts']
    #print(pos_train)
    return pos_train


def gp_stats_adjuster(training_data):

    '''
    In this function I will adjust the actual FPTs so that they scale up to 16 games if a player played between 13-15 games.
    Any player who played less than 13 games will be disregarded in the final dataset.  Additionaly, all outliers (players
    whose actual FPPts are 1.5 * the IQR of the absolute error between actual and projected FPPTs) will be scrubbed.
    '''
    training_data = training_data[(training_data['GP'] > 13)]

    training_data['Act FPts'] = training_data.apply(lambda row: (16 / row['GP'] * row['Act FPts']), axis=1)
    #outlier_limit = 2 * abs(training_data['Act FPts']-training_data['Proj FPts']).values.std()
    absolute_error = abs(training_data['Act FPts']-training_data['Proj FPts'])
    first_quadrant = absolute_error.quantile(.25, interpolation = 'midpoint')
    third_quadrant = absolute_error.quantile(.75, interpolation = 'midpoint')
    iqr = third_quadrant - first_quadrant
    outlier_limit = 1.5 * iqr
    #print(outlier_limit)
    #print(training_data[(absolute_error >= outlier_limit)])
    training_data = training_data[(absolute_error <= outlier_limit)]   # this scrubs the data of outlier performances
    #print(training_data)
    return training_data

def machine_learning(training_data, testing_data, pos, year):
    random = len(positions[pos])
    hidden = int(95*len(positions[pos]))
    if pos == 'TE':
        hidden *= 0.7
    mlp = MLPRegressor(hidden_layer_sizes=int(hidden), activation= 'relu', alpha = 0.001, max_iter= int(hidden/3.5),
                       random_state= random)  # can change regression model, look on scikit learn site... eg. linear_model.Ridge(alpha = .5) after import
    scaler = StandardScaler()
    ml_train_data_x = training_data.loc[:, 'Yr':'Proj FPts'].values
    ml_train_data_y = training_data.loc[:, 'Act FPts'].values
    ml_test_data = testing_data.loc[:, 'Yr': 'Proj FPts'].values


    #ml_train_data_x = scaler.fit_transform(ml_train_data_x)
    #ml_test_data = scaler.transform(ml_test_data)

    #print(ml_test_data)
    mlp.fit(ml_train_data_x, ml_train_data_y)
    ml_predictions = mlp.predict(ml_test_data)
    playernames = testing_data.loc[:, 'Name'].values
    predicted = testing_data.loc[:, 'Proj FPts'].values

    '''pos_stats = {'QB':'Pass Yds', 'RB':'Rush Yds', 'WR':'Rec Yds', 'TE':'Rec Yds'}

    plt.scatter(training_data.loc[:, pos_stats[pos]], training_data.loc[:,'Act FPts'])
    plt.xlabel('Rush Yards')
    plt.ylabel('Actual FPts')
    plt.show()'''
    # err1, err2 = actual - predicted , actual - a#, predicted - actual
    # av1, av2 = tuple(np.mean(x) for x in [err1,err2])#,err3])#tuple([(np.sum(np.vectorize(lambda x: x**(2))(err))/len(a))**(1/2) for err in [err1,err2,err3]])
    # std1, std2 = np.std(err1), np.std(err2)
    # print([x.shape for x in [playernames,predicted,a]])
    pd.set_option('display.max_rows', 1000)
    players = pd.DataFrame(np.column_stack([playernames, predicted, ml_predictions]),
                           columns=['Player', 'Projection', 'My Computed Score'])
    print(players)
    filename = 'ML_projections/{}_{}.csv'.format(pos, year)
    players.to_csv(filename)
    global i

    plt.figure(i)
    plt.xlabel('Projected Scores')
    plt.ylabel('Computed Scores')
    plt.scatter(players['Projection'],players['My Computed Score'])
    plt.show()
    i+=1
    return players

def data_vis(training_data, testing_data, pos):

    pos_stats = {'QB':['Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
                 'RB':['Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts'],
                 'WR':['Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
                 'TE':['Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts']}
    #plt.scatter(np.arange((len(training_data.loc[:, pos_stats[pos]].values.tolist()))), training_data.loc[:,'Act FPts'])
    #plt.xlabel('Players')
    #plt.ylabel('Actual FPts')
    #plt.show()
    #for i in range(len(pos_stats[pos])):
    #    print(sci.skewtest(training_data.loc[:,pos_stats[pos][i]].values.tolist()))
        #plt.figure(i)
        #sns.distplot(training_data.loc[:,pos_stats[pos][i]], bins= 30, label=pos_stats[pos][i])
        #plt.figure(i+1)
        #sns.distplot(np.vectorize(math.log)(training_data.loc[:,pos_stats[pos][i]].values.tolist()), bins= 30, label=pos_stats[pos][i])
        #plt.show()


    #sns.distplot(training_data.loc[:,'Act FPts'].values.tolist(), bins= 20)
    #plt.figure(2)
    #b = sns.distplot(training_data.loc[:,'Act FPts'], bins= 20)

i=1
def main():
    for position in positions.keys():   # runs through the functions once per each position
        #np.random.seed(len(positions[position]))
        training_data = gp_stats_adjuster(merging_proj_with_actual(position, 2013, 2018))
        testing_data = dataframe_creator(position, 'projected', False, 2018)
        #print('Training Data for {}'.format(position))
        #print(training_data)
        #print(training_data.loc[:, 'Yr':'Proj FPts'].values)

        #print('Testing Data for {}'.format(position))
        #print(testing_data)
        #print(training_data.loc[:, 4:15].values)
        #print(training_data)
        machine_learning(training_data, testing_data, position, 2018)
        #data_vis(training_data, testing_data, position)
main()
