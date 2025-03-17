# services/billing_service.py
from infrastructure.billing_repository import BillingRepository
from domain.billing import Billing
from typing import Dict, Any
from datetime import datetime
from typing import Optional


class BillingService:
    def __init__(self):
        self.billing_repo = BillingRepository()

    def create_or_update_billing(self, user_id: str, plan: str, payment_date: Optional[datetime] = None, cancellation_date: Optional[datetime] = None) -> Dict[str, Any]:
        try:
            import uuid
            billing_id = str(uuid.uuid4())

            billing = Billing(
                billing_id=billing_id,
                user_id=user_id,
                plan=plan,
                status='active',
                payment_date=payment_date,
                cancellation_date=cancellation_date
            )
            print(f"Creating billing object: {billing}")  # デバッグプリント
            response = self.billing_repo.create_or_update_billing(billing)
            print(f"Billing repository response: {response}")  # デバッグプリント
            return response
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_billing(self, user_id: str, billing_id: str) -> Dict[str, Any]:
        return self.billing_repo.read_billing(user_id, billing_id)

    def update_billing(self, user_id: str, billing_id: str, plan: Optional[str] = None, status: Optional[str] = None, cancellation_date: Optional[datetime] = None) -> Dict[str, Any]:
        try:
            # 既存の billing データを取得
            billing_response = self.billing_repo.read_billing(user_id, billing_id)
            if billing_response['status'] == 'success':
                billing_data = billing_response['billing_data']
                billing = Billing(**billing_data)

                # 更新フィールドを設定
                if plan is not None:
                    billing.plan = plan
                if status is not None:
                    billing.status = status
                if cancellation_date is not None:
                    billing.cancellation_date = cancellation_date

                print(f"Updating billing object: {billing}")  # デバッグプリント
                update_response = self.billing_repo.update_billing(billing)
                print(f"Billing repository update response: {update_response}")  # デバッグプリント
                return update_response
            else:
                return billing_response
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_billing(self, user_id: str, billing_id: str) -> Dict[str, Any]:
        return self.billing_repo.delete_billing(user_id, billing_id)

    def list_billing(self, user_id: str) -> Dict[str, Any]:
        return self.billing_repo.list_billing(user_id)
