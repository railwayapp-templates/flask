from flask import Flask, request, jsonify
import dropbox
from openai import OpenAI
import os

app = Flask(__name__)
app.app_context().push()

DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

if not DROPBOX_TOKEN or not OPENAI_KEY:
    raise Exception("DROPBOX_TOKEN e OPENAI_KEY precisam estar definidos nas variáveis de ambiente.")

dbx = dropbox.Dropbox(DROPBOX_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

@app.route("/ler-arquivo", methods=["POST"])
def ler_arquivo():
    data = request.get_json()
    caminho_arquivo = data.get("caminho_arquivo")
    pergunta = data.get("pergunta")

    if not caminho_arquivo or not pergunta:
        return jsonify({"erro": "Parâmetros faltando"}), 400

    try:
        metadata, response = dbx.files_download(caminho_arquivo)
        conteudo = response.content.decode("utf-8", errors="ignore")

        resposta = client.chat.completions.create(
           model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente de consultoria de marketing."},
                {"role": "user", "content": f"Conteúdo do arquivo:\n\n{conteudo}\n\nPergunta: {pergunta}"}
            ]
        )

        return jsonify({"resposta": resposta.choices[0].message.content})

    except dropbox.exceptions.ApiError as e:
        return jsonify({"erro": f"Erro Dropbox: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    app.run()

