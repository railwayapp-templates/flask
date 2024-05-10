from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def webhook():
    print(request.json)
    return '', 200

@app.route('/', methods=['GET'])
def hello_world():
    return jsonify({"Hello": "Hello World"})

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
