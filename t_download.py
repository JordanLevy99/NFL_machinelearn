# training data for weekly and yearly projections
""" Sources:
Projections: 'http://www.fftoday.com/rankings/playerwkproj.php?Season=%s&GameWeek=%d&PosID=10&LeagueID=189999'
Actual: 'http://www.fftoday.com/stats/playerstats.php?Season=%s&GameWeek=%d&PosID=10&LeagueID=189999'
Vegas Lines: 'http://killersports.com/nfl/query?sdql=season%3D%s+and+week+%3D+%d&submit=++S+D+Q+L+%21++'
"""

from selenium import webdriver
# import json #derulo
import os.path
import os, errno
from bs4 import BeautifulSoup
import csv
import pandas as pd
import time

### TODO
# Add a start and end year so this will work over multiple years

# driver = webdriver.Chrome('/Users/jordanlevy/Downloads/chromedriver')
script_dir = os.path.dirname(__file__)


def download_file(driver, start_yr, end_yr):
    pos = {10: ['QB', 12, 13, 2], 20: ['RB', 10, 12, 3], 30: ['WR', 10, 12, 3],
           40: ['TE', 7, 9, 3]}  # dictionary for pos_id relating to position name and number of stats
    # this number changes based on whether it is actual stats or projected stats, and QB requires less pages than the other three positions
    master_filename = 'Total_Data/{}-{}'.format(str(start_yr), str(end_yr))
    try:
        os.makedirs(master_filename)  # checks if directory already exists
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    for yr in range(start_yr, end_yr + 1):  # starting from start_yr and ending at end_yr + 1
        print(yr)
        for id in range(10, 50,
                        10):  # each id represents a different position on the website; 10 is QB, 20 is RB, 30 is WR, and 40 is TE
            pos_name = pos[id][0]  # position name based on id of each position
            # pos_length = pos[id][1]     # length of position stat line
            local_filename = 'Data/{}/{}'.format(str(yr), pos[id][0])
            try:
                os.makedirs(local_filename)  # checks if directory already exists
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            for page in range(pos[id][3]):  # pos[id][3] is the number of pages for each position
                websites = {
                    'http://www.fftoday.com/rankings/playerproj.php?&PosID={}&Season={}&LeagueID=189999&cur_page={}'.format(
                        id, yr, page): 'projected',
                    'http://www.fftoday.com/stats/playerstats.php?Season={}&GameWeek=&PosID={}&LeagueID=189999&cur_page={}'.format(
                        yr, id, page): 'actual'}
                for url in websites.keys():
                    if websites[url] == 'actual':  # if scraping actual data
                        pos_length = pos[id][
                            2]  # length of position stat line (this changes based on actual or projected stats)
                    else:
                        pos_length = pos[id][1]
                    # url = 'http://www.fftoday.com/stats/playerstats.php?Season={}&GameWeek=&PosID={}&LeagueID=189999&cur_page={}'.format(yr, id, page)
                    # time.sleep(5)
                    url_got = False
                    while not url_got:
                        try:
                            driver.get(url)
                            url_got = True
                        except:
                            print('Reloading...')
                            pass

                    # url = 'http://www.fftoday.com/rankings/playerproj.php?&PosID={}&Season={}&LeagueID=189999'.format(id, yr)
                    # driver.get(url)
                    print(pos_name, websites[url])
                    print('Page #', page + 1)
                    # print('Got url')
                    soup = BeautifulSoup(driver.page_source, 'html5lib').find('table',
                                                                              {"width": "100%", "cellpadding": "2"})
                    player_df = pd.read_html(str(soup))[0] # .find('table', {'class':'tableclmhdr'})))

                    player_df.to_csv(f'{master_filename}/pd_{pos_name}_{websites[url]}_{yr}.csv', index=False)
                    #print(player_df)
                    #print(soup)
                    '''
                    playerdata = ','.join([data.text.strip(' ').replace(',', '') for data in
                                           soup.findAll('td', {"class": "sort1"})]).replace(
                        '\xa0,\xa0', '').replace('\xa0', '').split(',')
                    playerdata = list(filter(lambda a: a != '', playerdata))
                    playerdata = [playerdata[i:i + pos_length] for i in range(len(playerdata))[
                                                                        ::pos_length]]  # creates nested lists for each player's statline;
                    # length of statline changes for each position and whether it's actual or projected data

                    for i in range(len(
                            playerdata)):  # this nested for loop converts strings to floats when the data is a float
                        playerdata[i].insert(2, int(yr))  # insert year into the third element of each players stat line
                        for j in range(len(playerdata[i])):
                            try:
                                if websites[url] == 'actual':  # if scraping actual data

                                    if j == 0:  # fixes number of rank being shown before name:
                                        # check http://www.fftoday.com/stats/playerstats.php?Season=2010&GameWeek=&PosID=10&LeagueID=18999 for example

                                        # playerdata[i][j] = playerdata[i][j][3:].strip(' ')
                                        playerdata[i][j] = ''.join(
                                            [i for i in playerdata[i][j] if not i.isdigit()]).strip('.').strip(
                                            ' ')  # strips digits and extra spaces from player name
                                        # print(playerdata[i][j])
                                playerdata[i][j] = float(playerdata[i][j])  # converts data to floats when necessary
                            except:
                                continue
                    # local_filename = os.path.join(script_dir, 'Data', str(yr), pos[id][0]+'.csv')
                    # print(local_filename)
                    file_mode = 'a'  # defaults file mode to append
                    master_file_mode = 'a'  # defaults master_file mode to append
                    if page == 0:
                        file_mode = 'w'
                        if yr == start_yr:
                            master_file_mode = 'w'
                    with open(master_filename + '/{}_{}.csv'.format(pos_name, websites[url]), master_file_mode,
                              newline='') as m:  # open a master_file that will contain all projected and actual stats
                        #print(playerdata)
                        master_writer = csv.writer(m)
                        master_writer.writerows(playerdata)
                    with open(local_filename + '/{}_{}_{}.csv'.format(pos_name, websites[url], yr), file_mode,
                              newline='') as csvfile:  # opens a file for for each year of stats
                        writer = csv.writer(csvfile)
                        writer.writerows(playerdata)

                    # print((-1*(yr-end_yr+1))/(end_yr+1-yr))
                    # time.sleep(5)
                    '''

driver = webdriver.Chrome('/Users/jordanlevy/Downloads/chromedriver')


def main():
    driver = webdriver.Chrome('/Users/jordanlevy/Downloads/chromedriver')
    driver.get('http://www.fftoday.com/oss8/users/login.php?ce=0&group=39&url=www.fftoday.com/members/%3fr=playerproj')
    # print('30 seconds to login')
    input('Press enter to continue')
    # time.sleep(30)
    ### TODO Change the following two lines each year
    start_yr = 2014
    end_yr = 2020
    download_file(driver, start_yr, end_yr)
    print('All Done')
    driver.close()
    try:
        driver.quit()
    except:
        pass


main()
