from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import firebase_admin
import requests
from firebase_admin import credentials, firestore
from flask import Flask, session, render_template, request, jsonify, redirect, url_for, flash
from passlib.hash import sha256_crypt

import Activity
import Database
import Goals
import Group
import Mood
import Strava
from Forms import example_wtform, RegisterForm
from Strava import StravaClient

# Initialise Firestore DB
cred = credentials.Certificate('key.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)
app.config['SECRET_KEY'] = "secretkey"  # random secret key refreshes session variables on run
app.config['SESSION_TYPE']: 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
app.static_folder = 'static'


@app.route('/')
def home():
	if 'username' not in session.keys():
		return render_template('home.html')

	week_start_date = datetime.now().replace(hour=0, minute=0, second=0, )
	week_start_date -= timedelta(days=6)
	monday_date = datetime.now().replace(hour=0, minute=0, second=0, )
	while monday_date.strftime('%A') != 'Monday':
		monday_date -= timedelta(days=1)

	activity_manager = Activity.ActivityManager(session['username'], db)
	activities = activity_manager.get_activities(datetime.now(), week_start_date)
	activities_descend = activities[::-1]
	time_totals = activity_manager.get_time_totals(datetime.now(), week_start_date)
	goal_mng = Goals.GoalsManager(session['username'], db)
	goal_mng.update_progress(activity_manager.get_activities(datetime.now(), monday_date))

	mood_mng = Mood.MoodManager(session['username'], db)
	""" mood_scores = [{<date>:<mood_data>}, {<date>:<mood_data>}...]
	    mood.avg = -1 means no mood data for that date"""
	mood_scores = mood_mng.get_scores(datetime.now(),
									  week_start_date)

	# Graph weekday labels e.g. [Monday, Tuesday...]
	date_labels = []
	mood_date_iter = week_start_date
	for i in range(7):
		date_labels.append(mood_date_iter.strftime('%A'))
		mood_date_iter += timedelta(days=1)

	# Gets all users in database (needs to be changed to only users in user's group)
	# Gets each user's time total for the week, adds to 2d array and then sorts this
	users_manager = Group.GroupManager(session['username'], db)
	users_list = users_manager.get_group_members()
	leaderboard_totals = []
	for user in users_list:
		user_activity_manager = Activity.ActivityManager(user, db)
		user_times = user_activity_manager.get_time_totals(datetime.now(), week_start_date)
		user_time_total = round((sum(user_times.values()))/60)
		leaderboard_totals.append([user, user_time_total])
	leaderboard_totals = sorted(leaderboard_totals, key=itemgetter(1), reverse=True)

	activity_streak = 0
	mood_streak = 0
	this_year = date.today().year
	year_start_date = date(this_year, 1, 1)
	year_start = datetime.combine(year_start_date, datetime.min.time())

	activities_in_year = activity_manager.get_time_totals(datetime.now(), year_start)
	reversed_activities = reversed(activities_in_year)

	mood_in_year = mood_mng.get_scores(datetime.now(), year_start)
	reversed_moods = reversed(mood_in_year)

	for activity in list(reversed_activities)[1:]:
		if activities_in_year.get(activity) != 0:
			activity_streak += 1
		else:
			break

	for mood in list(reversed_moods)[1:]:
		if mood_in_year.get(mood) != {'avg': -1}:
			mood_streak += 1
		else:
			break

	# Show first 4 activities
	return render_template('home.html', activities=activities_descend[:4], time_totals=time_totals.values(),
						   mood_scores=mood_scores.values(), date_labels=date_labels,
						   leaderboard_totals=leaderboard_totals, activity_streak=activity_streak,
						   mood_streak=mood_streak, goals=goal_mng.get_goals())


# Strava token authorization callback
@app.route('/exchange_token')
def token_acquired():
	if request.args.get('error') is not None:
		return redirect('/')
	r = requests.post(url="https://www.strava.com/oauth/token", params={'client_id': 79215,
																		'client_secret': '4afe51ccc0065eefa872319e8e02f33b4da24d7b',
																		'code': request.args.get('code'),
																		'grant_type': 'authorization_code'})
	if Strava.is_valid_request(r):
		res = r.json()
		expires = datetime.fromtimestamp(res['expires_at'])
		db_session = Database.Client(session['username'], db)
		db_session.update({'strava_access_token': res['access_token'], 'strava_refresh_token': res['refresh_token'],
						   'strava_access_expire': expires})
	return redirect('/')


@app.route('/login', methods=['POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		password_in = request.form['passwordIn']

		if sha256_crypt.verify(password_in, password):
			session['username'] = username
			session['user_pwd'] = password
			return jsonify({'authorized': 'true'})
		else:
			return jsonify({'authorized': 'false', 'error': 'login error'})


@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST':
		user_ref = db.collection('users').document(form.username.data).get()
		if form.validate(user_ref):
			username_in = form.username.data
			password_in = sha256_crypt.hash(
				form.password.data)  # password needs to be hashed before going into database
			session["username"] = username_in
			session["user_pwd"] = password_in  # https://pythonprogramming.net/password-hashing-flask-tutorial/
			db.collection('users').document(username_in).set({"username": username_in, "password": password_in})
			return redirect('/')

		else:
			flash(form.error_message, 'warning')
			return render_template('auth/register.html', form=form, bypassLogin=1)
	else:
		if 'username' in session:
			return redirect('/')
		else:
			return render_template('auth/register.html', form=form, bypassLogin=1)


@app.route('/logout')
def logout():
	session.clear()
	return redirect(url_for('home'))


@app.route('/view_data')
def view_data():
	# get last mood input date from database
	if 'last_mood_input' not in session.keys():
		if 'username' in session.keys():
			mood_obj = db.collection('users').document(session['username']).collection('mood_scores').document(
				datetime.now().strftime('%Y%m%d'))
			if mood_obj.get().exists:
				session['last_mood_input'] = datetime.now().strftime('%Y%m%d')
	# check if mood has been entered today and prevent multiple inputs in one day
	if 'last_mood_input' in session.keys():
		if datetime.strptime(session['last_mood_input'], '%Y%m%d').date() < datetime.now().date():
			del session['last_mood_input']

	activity_manager = Activity.ActivityManager(session['username'], db)
	activities = activity_manager.get_activities()
	if activities:
		activities.sort(key=lambda activity: activity['date'])

	mood_manager = Mood.MoodManager(session['username'], db)
	mood_data = mood_manager.get_moods()
	if mood_data:
		mood_data.sort(key=lambda mood: mood['date'])

	# find the earliest data to start the graph from
	first_activity_date = activities[0]['date'].replace(tzinfo=None)
	first_mood_date = datetime.strptime(mood_data[0]['date'], '%Y%m%d')
	if activities and mood_data:
		if first_activity_date < first_mood_date:
			start = first_activity_date
			end = datetime.today() + timedelta(days=1)
		else:
			start = first_mood_date
			end = datetime.today() + timedelta(days=1)
	elif activities and not mood_data:
		start = first_activity_date
		end = datetime.today() + timedelta(days=1)
	elif mood_data and not activities:
		start = first_mood_date
		end = datetime.today() + timedelta(days=1)
	else:
		start = datetime.today() - timedelta(days=1)
		end = datetime.today() + timedelta(days=1)

	date_range = [(start + timedelta(days=x)).strftime('%Y%m%d') for x in range(0, (end - start).days)]
	# Get mood data
	avg_mood_scores = {date: -1 for date in date_range}
	focus_scores = {date: -1 for date in date_range}
	happiness_scores = {date: -1 for date in date_range}
	optimism_scores = {date: -1 for date in date_range}
	satisfaction_scores = {date: -1 for date in date_range}
	for mood in mood_data:
		mood_date = mood['date']
		avg_mood_scores[mood_date] = mood['avg']
		focus_scores[mood_date] = mood['focus']
		happiness_scores[mood_date] = mood['happiness']
		optimism_scores[mood_date] = mood['optimism']
		satisfaction_scores[mood_date] = mood['satisfaction']

	# Append activity totals
	time_totals = {date: 0 for date in date_range}
	for activity in activities:
		activity_date = activity['date'].replace(tzinfo=None).strftime('%Y%m%d')
		time_totals[activity_date] += activity['time']

	date_labels = [start + timedelta(days=x) for x in range(0, (end - start).days)]
	week_min = date_labels[-1] - timedelta(days=7)
	month_min = date_labels[-1] - relativedelta(months=1)

	goal_mng = Goals.GoalsManager(session['username'], db)
	goals = goal_mng.get_goals()
	goal_dict = {}
	goal_dict['complete_count'] = 0
	goal_dict['incomplete_count'] = 0
	for goal in goals:
		if goal['progress'] == 100:
			goal_dict['complete_count'] += 1
	goal_dict['incomplete_count'] = len(goals) - goal_dict['complete_count']
	goal_dict['goals'] = goals
	return render_template('view-data.html', activities=activities, time_totals=time_totals.values(),
						   avg_mood_scores=list(avg_mood_scores.values()), date_labels=date_labels,
						   focus_scores=list(focus_scores.values()), happiness_scores=list(happiness_scores.values()),
						   optimism_scores=list(optimism_scores.values()), goals=goal_dict,
						   satisfaction_scores=list(satisfaction_scores.values()), week_min=week_min,
						   month_min=month_min)

@app.route('/mood-submit', methods=['POST'])
def submit_mood():
	if request.method == 'POST':
		mood_mng = Mood.MoodManager(session['username'], db)
		mood_mng.write_mood(request.form)

		return "success", 201


@app.route('/weekly_goals')
def weekly_goals():
	goals_manager = Goals.GoalsManager(session['username'], db)
	goals = goals_manager.get_goals()

	return render_template('weekly-goals.html', items=goals)

@app.route('/get-goals', methods=['GET'])
def get_goals():
	goals_manager = Goals.GoalsManager(session['username'], db)
	return str(goals_manager.get_number_goals())

@app.route('/write-goal', methods=['POST'])
def write_goal():
	if request.method == 'POST':
		goals_manager = Goals.GoalsManager(session['username'], db)
		goal_return = goals_manager.push_goals(request.form)
		print(goal_return)
		return goal_return, 201

@app.route('/delete-goal', methods=['POST'])
def delete_goal():
	if request.method == 'POST':
		goals_manager = Goals.GoalsManager(session['username'], db)
		id = request.form['id']
		goals_manager.delete_goals('goals', id)
		return ""

@app.route('/rooms')
def rooms():
	return render_template('rooms.html')


@app.route('/join-group', methods=['POST'])
def join_group():
	if request.method == 'POST':
		group_mng = Group.GroupManager(session['username'], db)
		if group_mng.get_group_id() is None:
			if group_mng.group_exists(request.form['group_id']):
				group_mng.join_group(request.form['group_id'])
			else:
				group_mng.create_group(request.form['group_id'])
			return "success"
		return "fail"

@app.route('/leave-group', methods=['POST'])
def leave_group():
	if request.method == 'POST':
		group_mng = Group.GroupManager(session['username'], db)
		if group_mng.get_group_id() is not None:
			#if group_mng.group_exists(request.form['group_id']):
			group_mng.leave_group(group_mng.get_group_id())
			# else:
			# 	group_mng.create_group(request.form['group_id'])
		return "success"
		# return "fail"


if __name__ == '__main__':
	app.run()
