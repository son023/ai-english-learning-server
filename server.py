# D:\STP\server.py

import os
from flask import Flask, request, jsonify

# Import hàm xử lý từ file của bạn
from my_whisper_app import evaluate_pronunciation_wer

app = Flask(__name__)

# Tạo thư mục uploads nếu chưa có
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/evaluate', methods=['POST'])
def evaluate_pronunciation():
    # 1. Kiểm tra xem request có file 'audio' không
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file part"}), 400
    
    file = request.files['audio']
    
    # 2. Kiểm tra xem có 'sentence' trong form data không
    if 'sentence' not in request.form:
        return jsonify({"error": "No sentence part"}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    reference_sentence = request.form['sentence']

    if file:
        # Lưu file tạm thời để xử lý
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # 3. Gọi hàm xử lý chính
        try:
            result = evaluate_pronunciation_wer(filepath, reference_sentence)
        except Exception as e:
            # Bắt lỗi nếu có vấn đề trong quá trình xử lý
            return jsonify({"error": str(e)}), 500
        finally:
            # 4. Xóa file tạm sau khi xử lý xong
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # 5. Trả về kết quả dạng JSON
        return jsonify(result)

    return jsonify({"error": "File processing failed"}), 500

if __name__ == '__main__':
    # Chạy server ở chế độ debug
    # host='0.0.0.0' để có thể truy cập từ máy khác trong cùng mạng
    app.run(host='0.0.0.0', port=5000, debug=True)