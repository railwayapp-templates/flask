from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def webhook():
    print(request.json)
    return '', 200

@app.route('/hi', methods=['GET'])
def hello_world():
    print("Hello, World!")
    return jsonify({"Hello": "Hello World"})

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
