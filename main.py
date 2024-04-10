from flask import Flask, jsonify
from flask_cors import CORS
import os
import BackEnd.Functions.userFunctions as callMethodUser
import BackEnd.Functions.postFunctions as callMethodPost
import BackEnd.GlobalInfo.ResponseMessages as ResponseMessage

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask lalo 🚅"})
    
@app.route('/login', methods=['POST'])
def fnLogin():
    try:
        objResult = callMethodUser.login()
        return objResult
    except Exception as e:
        print("Error al hacer login:", e)
        return jsonify(ResponseMessage.message500)
    
@app.route('/chisme', methods=['GET'])
def fnGetChisme():
    try:
        objResult = callMethodPost.getChisme()
        return objResult
    except Exception as e:
        print("Error al buscar chisme:", e)
        return jsonify(ResponseMessage.message500)


@app.route('/newchisme', methods=['POST'])
def fnPostChisme():
    try:
        objResult = callMethodPost.postChisme()
        return objResult
    except Exception as e:
        print("Error al crear chisme:", e)
        return jsonify(ResponseMessage.message500)
    

@app.route('/newuser', methods=['POST'])
def fnPostUser():
    try:
        objResult = callMethodUser.postUsuario()
        return objResult
    except Exception as e:
        print("Error al crear Usuario:", e)
        return jsonify(ResponseMessage.message500)
    
@app.route('/avatar', methods=['POST'])
def fnPostAvatar():
    try:
        objResult = callMethodUser.postAvatar()
        return objResult
    except Exception as e:
        print("Error al subir imagen:", e)
        return jsonify(ResponseMessage.message500)
    
    
@app.route('/image', methods=['POST'])
def fnPostImage():
    try:
        objResult = callMethodPost.postImage()
        return objResult
    except Exception as e:
        print("Error al subir imagen:", e)
        return jsonify(ResponseMessage.message500)
    
@app.route('/<string:_id>/likes', methods=['POST'])
def fnPostLikes(_id):
    try:
        objResult = callMethodPost.postLikes(_id)
        return objResult
    except Exception as e:
        print("Error al subir imagen:", e)
        return jsonify(ResponseMessage.message500)
    
@app.route('/<string:_id>/dislikes', methods=['POST'])
def fnPostDislikes(_id):
    try:
        objResult = callMethodPost.postDislikes(_id)
        return objResult
    except Exception as e:
        print("Error al subir imagen:", e)
        return jsonify(ResponseMessage.message500)
    
    

@app.route('/obtener', methods=['GET'])
def fnGetChismes():
    try:
        objResult = callMethodPost.obtener_chismes()  # Llama a la función directamente
        return objResult
    except Exception as e:
        print("Error al obtener el chisme:", e)
        return jsonify(ResponseMessage.message500)

@app.route('/maslikes', methods=['GET'])
def fnGetmaslikes():
    try:
        objResult = callMethodPost.maslikes()  # Llama a la función directamente
        return objResult
    except Exception as e:
        print("Error al obtener el chisme:", e)
        return jsonify(ResponseMessage.message500)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))

    
