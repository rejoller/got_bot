
from config import mongodb_cient



class User:
    def __init__(self, user_id):
        self.client_mongo = mongodb_cient
        self.db = self.client_mongo.gpt_users
        self.users_collection = self.db.users
        self.user_id = str(user_id)

    async def create_user(self, initial_tokens=2000, role='user'):
        user_doc = await self.users_collection.find_one({'_id': self.user_id})
        if not user_doc:
            result = await self.users_collection.insert_one({
                '_id': self.user_id,
                'token_balance': initial_tokens,
                'role': role
            })
            return True
        return False

    async def get_token_balance(self):
        try:
            user_doc = await self.users_collection.find_one({'_id': self.user_id})
            if user_doc:

                return user_doc['token_balance']
            else:
                print("No user document found")
                return 0
        except Exception as e:
            print(f"Error fetching user token balance: {e}")
            return None

    async def update_token_balance(self, tokens_used):
        try:
            if not isinstance(tokens_used, (int, float)):  # Проверка типа
                raise ValueError("tokens_used must be an integer or float")
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$inc': {'token_balance': -tokens_used}},
                upsert=True
            )
            # Отладочный вывод
            print(f"Tokens updated: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error updating token balance: {e}")
            return 0

    async def set_token_balance(self, new_balance):
        try:
            if not isinstance(new_balance, (int, float)):  # Проверка типа
                raise ValueError("new_balance must be an integer or float")
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$set': {'token_balance': new_balance}},
                upsert=True
            )
            # Отладочный вывод
            print(f"Token balance set: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error setting new token balance: {e}")
            return 0

    async def increase_token_balance(self, amount):
        try:
            tokens_to_add = amount * 500
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$inc': {'token_balance': tokens_to_add}},
                upsert=True
            )
            print(
                f"Token balance increased by {tokens_to_add}: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error increasing token balance: {e}")
            return 0