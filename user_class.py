
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


    async def get_msg_count(self):
        try:
            user_doc = await self.users_collection.find_one({'_id': self.user_id})
            if user_doc:
                msg_count = user_doc.get('msg_before_reset', 0)
                print(f"User document found: {user_doc}, msg_before_reset: {msg_count}")
                return msg_count
            else:
                print("No user document found")
                return 0
        except Exception as e:
            print(f"Error msg_before_reset: {e}")
            return None

    async def update_msg_count(self, msg_count):
        try:
            if not isinstance(msg_count, int):  # Проверка типа
                raise ValueError("msg_count must be an integer")
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$set': {'msg_before_reset': msg_count}},
                upsert=True
            )
            # Отладочный вывод
            print(f"msg_before_reset updated: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error updating msg_before_reset: {e}")
            return 0