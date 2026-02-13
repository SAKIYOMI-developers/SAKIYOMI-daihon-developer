# infrastructure/billing_repository.py
from firebase_admin import firestore
from domain.billing import Billing
from typing import Dict, Any
from config.firebase import db  # FirebaseのFirestoreインスタンスをインポート


class BillingRepository:
    SUBCOLLECTION_NAME = 'billing'

    def create_or_update_billing(self, billing: Billing) -> Dict[str, Any]:
        try:
            billing_dict = billing.dict()
            user_id = billing.user_id
            billing_id = billing.billing_id
            db.collection('users').document(user_id).collection(self.SUBCOLLECTION_NAME).document(billing_id).set(billing_dict, merge=True)
            return {'status': 'success', 'billing_id': billing_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def read_billing(self, user_id: str, billing_id: str) -> Dict[str, Any]:
        try:
            billing_doc = db.collection('users').document(user_id).collection(self.SUBCOLLECTION_NAME).document(billing_id).get()
            if billing_doc.exists:
                return {'status': 'success', 'billing_data': billing_doc.to_dict(), 'billing_id': billing_doc.id}
            else:
                return {'status': 'error', 'message': 'Billing not found'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_billing(self, billing: Billing) -> Dict[str, Any]:
        try:
            user_id = billing.user_id
            billing_id = billing.billing_id
            billing_dict = billing.dict(exclude_unset=True)
            print(f"Updating billing with billing_id: {billing_id} for user_id: {user_id}")  # デバッグプリント
            db.collection('users').document(user_id).collection(self.SUBCOLLECTION_NAME).document(billing_id).update(billing_dict)
            return {'status': 'success', 'billing_id': billing_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_billing(self, user_id: str, billing_id: str) -> Dict[str, Any]:
        try:
            print(f"Deleting billing with billing_id: {billing_id} for user_id: {user_id}")  # デバッグプリント
            db.collection('users').document(user_id).collection(self.SUBCOLLECTION_NAME).document(billing_id).delete()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def list_billing(self, user_id: str) -> Dict[str, Any]:
        try:
            billing_docs = db.collection('users').document(user_id).collection(self.SUBCOLLECTION_NAME).stream()
            billing_list = [{'billing_id': doc.id, **doc.to_dict()} for doc in billing_docs]
            return {'status': 'success', 'billing_list': billing_list}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
