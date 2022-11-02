from firebase_admin import firestore


class GroupManager:
	def __init__(self, username, db):
		self.username = username
		self.db = db
		self.user_group_ref = self.db.collection('user-groups')

	def get_group_id(self):
		group_id = None
		for group in self.user_group_ref.where('users', 'array_contains', self.username).stream():
			group_id = group.to_dict()['id']
		return group_id

	def get_group_members(self):
		users = []
		for group in self.user_group_ref.where('users', 'array_contains', self.username).stream():
			users = group.to_dict()['users']
		return users

	def join_group(self, group_id):
		self.user_group_ref.document(group_id).update({'users': firestore.ArrayUnion([self.username])})

	def leave_group(self, group_id):
		print("Reached?")
		self.user_group_ref.document(group_id).update({'users': firestore.ArrayRemove([self.username])})

	def create_group(self, group_id):
		self.user_group_ref.document(group_id).set({
			'id': group_id, 'users': [self.username]})

	def group_exists(self, group_id):
		return self.user_group_ref.document(group_id).get().exists

