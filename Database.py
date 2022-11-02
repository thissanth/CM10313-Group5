from firebase_admin import credentials, firestore
import firebase_admin


class Client:
	def __init__(self, username, db):
		self.db = db
		self.username = username
		self.user_ref = self.db.collection('users').document(self.username)

	def get_user_dict(self) -> dict:
		user_obj = self.user_ref.get()
		return user_obj.to_dict()

	def update(self, data: dict, sub_collection=None, sub_document=None):
		if sub_collection:
			self.user_ref.collection(sub_collection).document(sub_document).update(data)
		else:
			self.user_ref.update(data)

	def set(self, data: dict, sub_collection=None, sub_document=None):
		if sub_collection and not self.user_ref.collection(sub_collection).document(sub_document).get().exists:
			self.user_ref.collection(sub_collection).document(sub_document).set(data)
		elif not self.user_ref.get().exists and not sub_collection:
			self.user_ref.set(data)

	def delete(self, sub_collection=None, sub_document=None):
		if sub_collection:
			self.user_ref.collection(sub_collection).document(sub_document).delete()
		else:
			self.user_ref.delete()

	def get_activities_obj(self, before_date=None, after_date=None):
		activity_col = self.user_ref.collection('activities')
		if before_date is not None:
			if after_date is None:
				raise ValueError('after_date cannot be null')
			activities_obj = activity_col.where('date', '<=', before_date).where('date', '>=', after_date).stream()
		else:
			activities_obj = activity_col.stream()
		return activities_obj

	def get(self, sub_collection=None, sub_document=None):
		if sub_collection and self.user_ref.collection(sub_collection).document(sub_document).get().exists:
			return self.user_ref.collection(sub_collection).document(sub_document).get().to_dict()
		elif self.user_ref.get().exists and not sub_collection:
			return self.user_ref.get().to_dict()
		return {}

	def get_mood_obj(self, before_date=None, after_date=None):
		mood_col = self.user_ref.collection('mood_scores')
		if before_date is not None:
			if after_date is None:
				raise ValueError('after_date cannot be null')
			mood_obj = mood_col.where('date', '<=', before_date).where('date', '>=', after_date).stream()
		else:
			mood_obj = mood_col.stream()
		return mood_obj

	def delete(self, sub_collection=None, sub_document=None):
		if sub_collection:
			self.user_ref.collection(sub_collection).document(sub_document).delete()
		else:
			self.user_ref.delete()
