import secrets
import string
import os

def generate_api_key():
    """Generate a secure random API key."""
    length = 32
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def save_api_key_to_file(api_key, file_name="api_keys.txt"):
    """Append the generated API key to a file."""
    file_path = os.path.join(os.getcwd(), file_name)
    try:
        with open(file_path, "a") as file:
            file.write(api_key + "\n")
        print(f"API key saved to {file_path}")
    except Exception as e:
        print(f"Failed to save API key: {e}")

if __name__ == "__main__":

    api_key = generate_api_key()

    print(f"Generated API Key: {api_key}")

    save_api_key_to_file(api_key)
