import Database
from datetime import datetime, timedelta
from flask import session


class MoodManager(Database.Client):
	def __init__(self, username, db):
		super().__init__(username, db)
		self.db_session = Database.Client(username, db)
		self.username = username
		if 'username' not in session.keys():
			raise Warning('user must be logged in')
		if username == session['username']:
			if 'last_mood_input' not in session.keys():
				if self.db_session.get('mood_scores', datetime.now().strftime('%Y%m%d')):
					print(self.db_session.get('mood_scores', datetime.now().strftime('%Y%m%d')))
					session['last_mood_input'] = datetime.now().strftime('%Y%m%d')
			elif 'last_mood_input' in session.keys():
				if datetime.strptime(session['last_mood_input'], '%Y%m%d').date() < datetime.now().date():
					del session['last_mood_input']

	"""
	param 'form': data from mood data form on home 
	Takes result of data submitted to mood-submit route as form and writes to db
	"""
	def write_mood(self, form):
		date = datetime.now().strftime('%Y%m%d')
		happiness = int(form['happiness'])
		energy = int(form['energy'])
		satisfaction = int(form['satisfaction'])
		optimism = int(form['optimism'])
		focus = int(form['focus'])
		mood_score = round((happiness + energy + satisfaction + optimism + focus) / 5, 1)
		self.db_session.set({
			'date': date,
			'happiness': happiness,
			'satisfaction': satisfaction,
			'optimism': optimism,
			'focus': focus,
			'energy': energy,
			'avg': mood_score
		}, 'mood_scores', date)
		if self.username == session['username']:
			session['last_mood_input'] = date

	"""
	param 'before_date', 'after_date': datetime objects. e.g. datetime.now()
	returns list of dict containing mood data between a date range
	e.g. moods = [{<mood_20220330>}, {mood_20220327}...]
	"""
	def get_moods(self, before_date=None, after_date=None):
		moods = []
		if before_date or after_date == None:
			mood_obj = self.db_session.get_mood_obj()
		else:
			mood_obj = self.db_session.get_mood_obj(before_date.strftime('%Y%m%d'), after_date.strftime('%Y%m%d'))
		for mood in mood_obj:
			moods.append(mood.to_dict())
		return moods

	"""
	param 'before_date', 'after_date': datetime objects. e.g. datetime.now()
	returns: list of dicts-{date: {mood_data}} between a date range
	"""

	def get_scores(self, before_date=None, after_date=None):
		date_labels = [after_date.strftime('%Y%m%d')]
		mood_date_iter = after_date
		while mood_date_iter < before_date:
			mood_date_iter += timedelta(days=1)
			date_labels.append(mood_date_iter.strftime('%Y%m%d'))
		mood_scores = {date: {'avg': -1} for date in date_labels}  # -1 prevents score showing on graph
		moods = self.get_moods(before_date, after_date)
		for mood in moods:
			mood_scores[mood['date']] = mood
		return mood_scores
