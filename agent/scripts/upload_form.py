import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv

load_dotenv()
# Use a service account.


app = firebase_admin.initialize_app()

db = firestore.client()

import json

# Open the file and load the content
with open('scripts/form_2.json', 'r') as file:
    data = json.load(file)
# print(data)
db.collection("forms_v2").document("form_number_1").set(data)