import json
from passlib.context import CryptContext

crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encrypt_user(username: str, new_password: str, new_password_again: str):
    if new_password != new_password_again:
        raise ValueError('bad password')

    user_db = {
        username: {
            "username": username,
            "hashed_password": crypt_context.hash(new_password),
            "disabled": False
        }
    }

    with open("user_db.json", "w") as json_file:
        json.dump(user_db, json_file)


if __name__ == '__main__':
    try:
        print("testing... correct password")
        encrypt_user("admin", "password2", "password2")
    except ValueError as e:
        print('exception', e)

    try:
        print("testing... bad password")
        encrypt_user("admin", "password1", "password2")
    except ValueError as e:
        print('except', e)
