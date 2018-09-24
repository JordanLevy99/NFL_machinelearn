import csv
import os.path
import pandas as pd

positions = {'QB':['Name', 'Team', 'Yr', 'Bye', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
             'RB':['Name', 'Team', 'Yr', 'Bye', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec Tgts', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts'],
             'WR':['Name', 'Team', 'Yr', 'Rec Tgts', 'Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Proj FPts'],
             'TE':['Name', 'Team', 'Yr', 'Rec Tgts', 'Rec', 'Rec Yds', 'Rec TDs', 'Proj FPts']}
pd.set_option('display.width', 10000)

def dataframe_creator(pos, datatype, end_yr, start_yr = 2010):
    '''
    Creates a pandas dataframe for specified csv file in the 2010 to 2018 database with a proper header and some minor adjustments
    '''
    filename = 'Total_Data/2010-2018/{}_{}.csv'.format(pos, datatype)    # the filename of the specified position plus actual vs projected data
    total_lines = []  # the outer list to be appended to
    with open(filename, 'r') as f:  # opens specified file as f
        column_names = positions[pos]   # used to name columns for the specified file
        for line in f:  # iterates through each line of file f
            line_lst = line.split(',')  # splits each line into a list
            #print(line_lst)
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
                if pos == 'QB' or pos == 'RB':  # if the position is either QB or RB...
                    column_names[3] = 'GP' # change the column name from Bye to GP to accurately represent what they are in the original data
            #print(line_lst)
            total_lines.append(line_lst)    # append updated line/list to parent list
        #with open('placeholder.csv', 'w') as f2:
        #   print(f.)
    #print(pd.DataFrame(total_lines, columns= positions[pos]))   # convert parent list to pandas data frame and print
    return pd.DataFrame(total_lines, columns= column_names) # returns a pandas dataframe with the proper columns as given by the positions dictionary @ line __


def merging_proj_with_actual(pos, end_yr, start_yr = 2010):
    pos_proj = dataframe_creator(pos, 'projected', end_yr, start_yr)
    pos_actual = dataframe_creator(pos, 'actual', end_yr, start_yr)


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
    pos_train.columns = positions['QB']+['Act FPts']
    print(pos_train)
    return pos_train


def gp_stats_adjuster(training_data):

    '''
    In this function I will adjust the actual FPTs so that they scale up to 16 games if a player played between 13-15 games.
    Any player who played less than 13 games will be disregarded in the final dataset
    '''
    training_data = training_data[(training_data['GP'] > 13)]
    training_data['Act FPts'] = training_data.apply(lambda row: (16 / row['GP'] * row['Act FPts']), axis=1)
    print(training_data)
    return training_data

gp_stats_adjuster(merging_proj_with_actual('QB', 2017))
