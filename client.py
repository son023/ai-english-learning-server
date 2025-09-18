# D:\STP\client.py

import requests

# URL của server Flask
# Nếu chạy trên cùng máy, dùng localhost hoặc 127.0.0.1
url = "http://127.0.0.1:5000/evaluate"

# Đường dẫn đến file audio và câu gốc
audio_file_path = "user_audio.wav"
sentence = "Hello world this is a test"

# Chuẩn bị dữ liệu để gửi đi
# 'audio' là file, 'sentence' là một trường trong form
files = {'audio': (audio_file_path, open(audio_file_path, 'rb'), 'audio/wav')}
data = {'sentence': sentence}

print(f"Sending request to {url}...")
print(f"Sentence: '{sentence}'")

# Gửi request POST
try:
    response = requests.post(url, files=files, data=data)

    # In kết quả
    if response.status_code == 200:
        print("\n✅ Success! Server Response:")
        print(response.json())
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
except requests.exceptions.ConnectionError as e:
    print("\n❌ Connection Error: Could not connect to the server.")
    print("Please make sure the server.py is running.")