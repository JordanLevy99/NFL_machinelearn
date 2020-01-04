# training data for weekly and yearly projections
""" Sources:
Projections: 'http://www.fftoday.com/rankings/playerwkproj.php?Season=%s&GameWeek=%d&PosID=10&LeagueID=189999'
Actual: 'http://www.fftoday.com/stats/playerstats.php?Season=%s&GameWeek=%d&PosID=10&LeagueID=189999'
Vegas Lines: 'http://killersports.com/nfl/query?sdql=season%3D%s+and+week+%3D+%d&submit=++S+D+Q+L+%21++'
"""

from selenium import webdriver
#import json
import os.path
import os, errno
from bs4 import BeautifulSoup
import csv
import time

driver = webdriver.Chrome('/Users/jordanlevy/Downloads/chromedriver')
script_dir = os.path.dirname(__file__)

def download_file(driver, start_yr, end_yr):
    pos = {10:['QB', 12], 20:['RB', 10], 30:['WR', 10], 40:['TE', 7]}   # dictionary for pos_id relating to position name and number of features
    master_filename = 'Training_Data/{}-{}'.format(str(start_yr), str(end_yr))
    try:
        os.makedirs(master_filename)    #checks if directory already exists
    except OSError as e:
        if e.errno != errno.EEXIST: #if os cannot make this directory and the directory doesn't already exist, raise an error
            raise
    for yr in range(start_yr, end_yr+1):
        print(yr)
        for id in range(10,50,10):
            pos_name = pos[id][0]
            local_filename = 'Training_Data/{}/{}'.format(str(yr), pos[id][0])
            try:
                os.makedirs(local_filename)    #checks if directory already exists
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            for page in range(3):
                websites = {'projected':'http://www.fftoday.com/rankings/playerproj.php?&PosID={}&Season={}&LeagueID=189999&cur_page={}'.format(id, yr, page),
                            'actual':'http://www.fftoday.com/stats/playerstats.php?Season={}&GameWeek=&PosID={}&LeagueID=189999&cur_page={}'.format(yr, id, page)}
                for data in websites.keys():
                    try:
                        driver.get(websites[data]) #websites[data] is a url for the type of data (projected or actual)
                    except:
                        break
                    #url = 'http://www.fftoday.com/rankings/playerproj.php?&PosID={}&Season={}&LeagueID=189999'.format(id, yr)
                    #driver.get(url)
                    print(pos_name)
                    print('Page #',page+1)
                    #print('Got url')
                    soup = BeautifulSoup(driver.page_source, 'html5lib').find('table', {"width": "100%", "cellpadding": "2"})
                    playerdata = ','.join([data.text.strip(' ').replace(',','') for data in soup.findAll('td', {"class": "sort1"})]).replace(
                            '\xa0,\xa0', '').replace('\xa0', '').split(',')
                    playerdata = list(filter(lambda a: a != '', playerdata))
                    playerdata = [playerdata[i:i + pos[id][1]] for i in range(len(playerdata))[::pos[id][1]]]   #creates nested lists for each player's statline; length of statline changes for each position
                    for i in range(len(playerdata)):            #this nested for loop converts strings to floats when the data is a float
                        for j in range(len(playerdata[i])):
                            try:
                                playerdata[i][j] = float(playerdata[i][j])  #converts data to floats when necessary
                            except:
                                continue
                    #local_filename = os.path.join(script_dir, 'Data', str(yr), pos[id][0]+'.csv')
                    #print(local_filename)
                    file_mode = 'a'
                    master_file_mode = 'a'
                    if page == 0:
                        file_mode = 'w'
                        if yr == 2010:
                            master_file_mode = 'w'
                    with open(master_filename+'/{}_training.csv'.format(pos_name), master_file_mode, newline='') as m:
                        master_writer = csv.writer(m)
                        master_writer.writerows(playerdata)
                        with open(local_filename+'/{}_training_{}.csv'.format(pos_name,yr), file_mode, newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerows(playerdata)

                    #print((-1*(yr-end_yr+1))/(end_yr+1-yr))
                    time.sleep(2)



def main():
    driver = webdriver.Chrome('/Users/jordanlevy/Downloads/chromedriver')
    download_file(driver, 2015, 2019)
    print('All Done')
    driver.close()


main()
try:
    driver.quit()
except:
    pass
