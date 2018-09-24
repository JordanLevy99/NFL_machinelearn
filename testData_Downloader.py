import csv
import errno
import os
# import json #derulo
import os.path
import time

from bs4 import BeautifulSoup
from selenium import webdriver

script_dir = os.path.dirname(__file__)


def test_data_downloader(driver, yr):
    pos = {10: ['QB', 12, 13, 2], 20: ['RB', 10, 12, 3], 30: ['WR', 10, 12, 4],
           40: ['TE', 7, 9, 3]}  # dictionary for pos_id relating to position name and number of stats
    for id in range(10, 50,
                    10):  # each id represents a different position on the website; 10 is QB, 20 is RB, 30 is WR, and 40 is TE
        pos_name = pos[id][0]  # position name based on id of each position
        # pos_length = pos[id][1]     # length of position stat line
        local_filename = 'Total_Data/Test_Data/{}'.format(str(yr))
        try:
            os.makedirs(local_filename)  # checks if directory already exists
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        for page in range(pos[id][3]):  # pos[id][3] is the number of pages for each position
            url = 'http://www.fftoday.com/rankings/playerproj.php?&PosID={}&Season={}&LeagueID=189999&cur_page={}'.format(
                id, yr, page)  # only projected data is downloaded for test data since there is not actual data yet
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
            print(pos_name)
            print('Page #', page + 1)
            # print('Got url')
            soup = BeautifulSoup(driver.page_source, 'html5lib').find('table', {"width": "100%", "cellpadding": "2"})
            playerdata = ','.join(
                [data.text.strip(' ').replace(',', '') for data in soup.findAll('td', {"class": "sort1"})]).replace(
                '\xa0,\xa0', '').replace('\xa0', '').split(',')
            playerdata = list(filter(lambda a: a != '', playerdata))
            playerdata = [playerdata[i:i + pos_length] for i in
                          range(len(playerdata))[::pos_length]]  # creates nested lists for each player's statline;
            # length of statline changes for each position and whether it's actual or projected data
            for i in range(len(playerdata)):  # this nested for loop converts strings to floats when the data is a float
                playerdata[i].insert(2, int(yr))  # insert year into the third element of each players stat line
                for j in range(len(playerdata[i])):
                    try:
                        playerdata[i][j] = float(playerdata[i][j])  # converts data to floats when necessary
                    except:
                        continue
            file_mode = 'a'  # defaults file mode to append
            if page == 0:
                file_mode = 'w'
            with open(local_filename + '/{}_projected.csv'.format(pos_name), file_mode,
                      newline='') as csvfile:  # opens a file for for each year of stats
                writer = csv.writer(csvfile)
                writer.writerows(playerdata)


def main():
    driver = webdriver.Chrome('/Users/jordanlevy/Downloads/chromedriver')
    driver.get(
        'http://www.fftoday.com/oss8/users/login.php?ce=0&group=39&url=www.fftoday.com/members/%3fr=playerproj')  # Username: data_ff   Password: Benjiwalk2
    print('30 seconds to login')
    time.sleep(30)

    test_data_downloader(driver, 2018)
    print('All Done')
    driver.close()
    try:
        driver.quit()
    except:
        pass


main()
