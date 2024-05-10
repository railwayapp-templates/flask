from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    print(request.json)
    return '', 200

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
