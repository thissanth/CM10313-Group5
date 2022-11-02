import Database
from Strava import StravaClient
from flask import session
from datetime import datetime, timedelta


class ActivityManager(Database.Client):
	def __init__(self, username, db):
		super().__init__(username, db)
		self.username = username
		self.db_session = Database.Client(self.username, db)
		if 'username' not in session.keys():
			raise Warning('user must be logged in')

	"""
	Pulls activities from strava after the 'strava_last_get' field in firebase
	Pushes these activities into firebase
	
	Used in get_activities to ensure the latest strava activities are always in firebase
	"""
	def push_strava_activities(self):
		# Read user from database
		user = self.db_session.get_user_dict()

		if 'strava_access_token' in user.keys():
			strava_vars = {'access_token': user['strava_access_token'],
						   'refresh_token': user['strava_refresh_token'],
						   'token_expiry': user['strava_access_expire']}

			# Start strava client
			strava_client = StravaClient(strava_vars)
			if strava_client.is_token_expired():
				strava_vars = strava_client.refresh_access_token()
				self.db_session.update({
					'strava_access_token': strava_vars['access_token'],
					'strava_refresh_token': strava_vars['refresh_token'],
					'strava_access_expire': strava_vars['token_expiry']
				})

			if 'strava_last_get' in user.keys():  # Check if strava data has been pulled before
				strava_activities = strava_client.get_activities(
					user['strava_last_get'])  # pull activities after previous latest
			else:
				strava_activities = strava_client.get_activities(None)  # first strava pull

			# activity_col = user_ref.collection('activities')
			if strava_activities:
				# Update last pull datetime
				self.db_session.update({
					'strava_last_get': datetime.strptime(strava_activities[-1]['start_date'], '%Y-%m-%dT%H:%M:%SZ')
				})
			# user['strava_last_get'] = datetime.strptime(strava_activities[-1]['start_date'], '%Y-%m-%dT%H:%M:%SZ')
			# Push activities to database
			for activity in strava_activities:
				self.db_session.set({
					'id': activity['id'],
					'name': activity['name'],
					'distance': activity['distance'],
					'time': activity['moving_time'],
					'type': activity['type'],
					'date': datetime.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
				}, 'activities', str(activity['id']))

	""" get_activities(before_date: datetime, after_date: datetime)
	returns: list of activity dictionaries
	ACTIVITIES NOT SORTED BY DATE: don't rely on activities being sorted already
	activity = {
				id: <id>,
				distance: <distance in metres>,
				name: <activity title>,
				time: <minutes>,
				date: <datetime>,
				type: <type: run, swim etc>
				}
	"""
	def get_activities(self, before_date: datetime = None, after_date: datetime = None):
		self.push_strava_activities()
		activities_obj = self.db_session.get_activities_obj(before_date, after_date)
		activities = []
		for activity in activities_obj:
			activities.append(activity.to_dict())
		return activities

	""" get_time_totals(before_date: datetime, after_date: datetime)
		returns: dict containing dates and the activity time total for that date
		e.g. time_totals = [{20220330: {<activity_data>}, {20220331: {<activity_data>}...]
		"""
	def get_time_totals(self, before_date: datetime = None, after_date: datetime = None):
		date_labels = [after_date.strftime('%Y%m%d')]
		date_iter = after_date
		while date_iter < before_date:
			date_iter += timedelta(days=1)
			date_labels.append(date_iter.strftime('%Y%m%d'))
		activities_descend = self.get_activities(before_date, after_date)
		time_totals = {date: 0 for date in date_labels}
		for activity in activities_descend:
			activity_date = activity['date'].replace(tzinfo=None)
			time_totals[activity_date.strftime('%Y%m%d')] += activity['time']
		return time_totals
