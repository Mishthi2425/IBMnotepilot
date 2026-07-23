import json
import os

CHATS_DIR = os.path.join(os.getcwd(), "chats")
os.makedirs(CHATS_DIR, exist_ok=True)


def save_chat(chat_id, document_id, filename, messages):
    try:
        data = {
            "chat_id": chat_id,
            "document_id": document_id,
            "filename": filename,
            "messages": messages
        }
        with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Save chat error: {e}")


def get_chat(chat_id):
    try:
        path = os.path.join(CHATS_DIR, f"{chat_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Get chat error: {e}")
        return None


def get_all_chats():
    try:
        chats = []
        for fname in os.listdir(CHATS_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(CHATS_DIR, fname)) as f:
                    chats.append(json.load(f))
        chats.sort(key=lambda c: c.get("chat_id", ""), reverse=True)
        return chats
    except Exception as e:
        print(f"Get all chats error: {e}")
        return []


def delete_chat(chat_id):
    try:
        path = os.path.join(CHATS_DIR, f"{chat_id}.json")
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Delete chat error: {e}")


def delete_all_chats():
    try:
        for fname in os.listdir(CHATS_DIR):
            if fname.endswith(".json"):
                os.remove(os.path.join(CHATS_DIR, fname))
    except Exception as e:
        print(f"Delete all chats error: {e}")
