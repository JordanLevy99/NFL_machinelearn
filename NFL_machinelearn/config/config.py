"""Configuration settings for the NFL machine learning project."""

CONFIG = {
    'POSITIONS': {
        'QB': {'id': 10, 'projected_stats': 12, 'actual_stats': 13, 'pages': 2},
        'RB': {'id': 20, 'projected_stats': 10, 'actual_stats': 12, 'pages': 3},
        'WR': {'id': 30, 'projected_stats': 10, 'actual_stats': 12, 'pages': 3},
        'TE': {'id': 40, 'projected_stats': 7, 'actual_stats': 9, 'pages': 3}
    },
    'LEAGUE_ID': '189999',  # FFToday league ID
    'BASE_URL': 'http://www.fftoday.com',
    'CHROME_DRIVER_PATH': 'drivers/chromedriver',
    'DOWNLOAD_COLUMNS': {
        'projected': {
            'QB': ['Name', 'Team', 'Bye', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds',
                   'Rush TDs', 'FPts'],
            'RB': ['Name', 'Team', 'Bye', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs',
                   'FPts'],
            'WR': ['Name', 'Team', 'Bye', 'Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs',
                   'FPts'],
            'TE': ['Name', 'Team', 'Bye', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts']
        },
        'actual': {
            'QB': ['Name', 'Team', 'GP', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'FPts'],
            'RB': ['Name', 'Team', 'GP', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts'],
            'WR': ['Name', 'Team', 'GP', 'Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs',
                   'FPts'],
            'TE': ['Name', 'Team', 'GP', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts']
        }
    },
    'DROP_COLUMNS': {
        'projected': {
            'QB': [],
            'RB': [],
            'WR': [],
            'TE': []
        },
        'actual': {
            'QB': ['FPts/G'],
            'RB': ['Target', 'FPts/G'],
            'WR': ['Target', 'FPts/G'],
            'TE': ['Target', 'FPts/G']
        }
    },
    'STAT_COLUMNS': {
        'QB': ['Name', 'Team', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds',
               'Rush TDs', 'FPts'],
        'RB': ['Name', 'Team', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs',
               'FPts'],
        'WR': ['Name', 'Team', 'Rec', 'Rec Yds', 'Rec TDs', 'Rush Att', 'Rush Yds', 'Rush TDs',
               'FPts'],
        'TE': ['Name', 'Team', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts']
    }
}
