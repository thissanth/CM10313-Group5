import Database
from Strava import StravaClient
from flask import session
from datetime import datetime, timedelta


class GoalsManager(Database.Client):
    def __init__(self, username, db):
        super().__init__(username, db)
        self.username = username
        self.db_session = Database.Client(self.username, db)
        if 'username' not in session.keys():
            raise Warning('user must be logged in')


    def push_goals(self, data):
        data = data.to_dict()
        goal_count = len(self.get_goals())
        goal_count += 1
        goal_text = ""
        goal_text += data['value']
        if (data['goalType'] == 'distance'):
            goal_text += 'km'
        elif (data['goalType'] == 'time'):
            goal_text += ' Hours'
        elif (data['goalType'] == 'count'):
            goal_text += ' Times'

        if (data['activityType'] == 'all'):
            goal_text += ' Activity'
        elif (data['activityType'] == 'Ride'):
            goal_text += ' Cycling'
        else:
            goal_text += f" {data['activityType'].capitalize()}ing"

        goal_text += ' This Week'
        data['goalText'] = goal_text
        data['status'] = 'Todo'
        data['progress'] = 0
        self.db_session.set(data, 'goals', str(data['id']))
        return goal_text

    def get_goals(self):
        goals = []
        goal_ref = self.db.collection('users').document(session['username']).collection('goals')
        for doc in goal_ref.stream():
            goals.append(doc.to_dict())

        return goals

    def get_number_goals(self):
        goal_count = len(self.get_goals())
        goal_count += 1
        return goal_count

    def delete_goals(self, subcollection=None, subdocument=None):
        self.db_session.delete(subcollection, subdocument)
    #     FIXME: Decrement ID's on deletion

    def update_progress(self, activities):
        activity_types = ['Run', 'Walk', 'Ride', 'Swim', 'all']
        goal_types = {'time': {}, 'distance': {}, 'count': {}}
        goal_types['time'] = {i: 0 for i in activity_types}
        goal_types['distance'] = {i: 0 for i in activity_types}
        goal_types['count'] = {i: 0 for i in activity_types}
        for activity in activities:
            if activity['type'] in activity_types:
                goal_types['count'][activity['type']] += 1
                goal_types['time'][activity['type']] += round(activity['time'] / 3600, 2)
                goal_types['distance'][activity['type']] += round(activity['distance'] / 1000)
            goal_types['count']['all'] += 1
            goal_types['time']['all'] += round(activity['time'] / 3600, 2)
            goal_types['distance']['all'] += round(activity['distance'] / 1000)
        goals = self.get_goals()
        for goal in goals:
            for label in goal_types.keys():
                if goal['goalType'] == label:
                    progress = round((goal_types[label][goal['activityType']] / int(goal['value'])) * 100)
                    data = {'progress': progress}
                    if progress >= 100:
                        data['status'] = 'Complete'
                        data['progress'] = 100
                    self.db_session.update(data, 'goals', goal['id'])
