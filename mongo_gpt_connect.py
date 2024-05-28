
from datetime import datetime
from zoneinfo import ZoneInfo
from config import mongodb_cient





db = mongodb_cient.gpt_users
gpt_users_collection = db.users


async def log_message_interaction(user_id, username, first_name, user_input, gpt_response, user_input_tokens, assistant_response_tokens, total_tokens_used, new_balance):
    message_time = datetime.now().astimezone(
        ZoneInfo("Asia/Krasnoyarsk")).strftime("%Y-%m-%d %H:%M:%S")
    client = mongodb_cient

    db = client.gpt_users

    messages_collection = db.messages
    new_message = {
        "user_input": user_input,
        "gpt_response": gpt_response,
        "user_input_tokens": user_input_tokens,
        "assistant_response_tokens": assistant_response_tokens,
        "total_tokens_used": total_tokens_used,
        "new_balance": new_balance,
        "timestamp": message_time
    }
    # Проверка на существование документа пользователя
    document = await messages_collection.find_one({"user_id": user_id})
    if document is None:
        # Создание нового документа, если он не найден
        document = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "interactions": [new_message]
        }
        await messages_collection.insert_one(document)
    else:
        # Добавление нового сообщения в массив существующего документа
        await messages_collection.update_one(
            {"_id": document['_id']},
            {"$push": {"interactions": new_message}},
            upsert=True
        )
    print("Interaction logged successfully.")
