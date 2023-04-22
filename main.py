from flask import Flask, request, jsonify
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

app = Flask(__name__)
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# url = ('https://elements.envato.com/pt-br/barbecue-monster-indie-rock-flyer-U2JELAV')

@app.route('/pegar', methods=['POST'])
def pegar():
  url = request.json['url']
  navegador = webdriver.Chrome(options=options)
  navegador.get(url)
  site = BeautifulSoup(navegador.page_source, 'html.parser')
  titulo = site.find("meta", property='og:title').get('content')
  imagem = site.find("meta", property='og:image').get('content')
  return jsonify({
              'titulo': titulo,
              'imagem': imagem,
  })
app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
