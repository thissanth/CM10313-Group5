import datetime
import requests
from datetime import datetime, timedelta
from urllib.error import HTTPError
import pytz

def is_valid_request(r):
	if r.status_code == 200 or r.status_code == 201:
		return True
	elif 400 < r.status_code < 405:
		print(f"invalid request {r.status_code}")
		return False
	elif r.status_code == 429:
		print(f"invalid request {r.status_code}")
		return False
	elif r.status_code == 500:
		print(f"invalid request {r.status_code}")
		return False
	else:
		print(f"invalid request {r.status_code}")
		return False


class StravaClient:
	def __init__(self, strava_variables):
		self.access_token = strava_variables['access_token']
		self.refresh_token = strava_variables['refresh_token']
		self.token_expiry = strava_variables['token_expiry']
		self.headers = {"Authorization": f"Bearer {self.access_token}"}
		self.EPOCH = datetime.utcfromtimestamp(0)
		self.EPOCH = pytz.utc.localize(self.EPOCH)

	def is_token_expired(self):
		return self.token_expiry.replace(tzinfo=None) < datetime.now()

	def refresh_access_token(self):
		r = requests.post("https://www.strava.com/api/v3/oauth/token", params={
			'client_id': 79215,
			'client_secret': '4afe51ccc0065eefa872319e8e02f33b4da24d7b',
			'grant_type': 'refresh_token',
			'refresh_token': self.refresh_token
		})
		if is_valid_request(r):
			res = r.json()
			expires = datetime.fromtimestamp(res['expires_at'])
			self.access_token = res['access_token']
			self.refresh_token = res['refresh_token']
			self.token_expiry = expires
			return {'access_token': self.access_token, 'refresh_token': self.refresh_token,
					'token_expiry': expires}

	def get_activities(self, after_date):
		if after_date is not None:
			after_date_epoch = (after_date - self.EPOCH).total_seconds()
			params = {'after': after_date_epoch}
		else:
			params = {}
		activities_page = ['Not empty']
		page_number = 1
		activities = []
		while activities_page:
			params['page'] = page_number
			r = requests.get("https://www.strava.com/api/v3/athlete/activities",
							 headers={"Authorization": f"Bearer {self.access_token}"},
							 params=params)
			if not is_valid_request(r):
				break
			activities_page = r.json()
			activities += activities_page
			page_number += 1
		return activities
	# TODO: Refresh activities. Compares strava to database in case of mismatch or deletion
