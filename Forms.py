# add forms here
# lookup how to use wtforms
from wtforms import Form, StringField, SelectField, validators, BooleanField, SubmitField, PasswordField
from wtforms.fields import DateField
from wtforms.validators import ValidationError

import datetime


class example_wtform(Form):
	name = StringField('Name')
	date = DateField('Select a date')
	submit = SubmitField('Submit', id="example-submit-button")

	def validate_form(self):
		if self.date.data > datetime.date.today():
			self.errormessage = "error message for why this is invalid"
			return False
		return True


class RegisterForm(Form):
	username = StringField('Enter a username', [validators.InputRequired(), validators.Length(min=3, max=10)])
	password = PasswordField('Enter a password', [validators.InputRequired(), validators.Length(min=5, max=20),
												  validators.EqualTo('passwordRepeat', message='passwords do not match')])
	passwordRepeat = PasswordField('Repeat password')
	submit = SubmitField('Submit')

	def validate(self, user_ref):
		if user_ref.exists:
			self.error_message = "Account already exists"
			return False
		if self.password.data != self.passwordRepeat.data:
			self.error_message = "passwords do not match"
			return False
		else:
			return True
