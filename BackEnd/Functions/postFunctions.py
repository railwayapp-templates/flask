from flask import request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from flask_cors import CORS
import BackEnd.GlobalInfo.Keys as PracticaKeys
import BackEnd.GlobalInfo.ResponseMessages as ResponseMessages

if PracticaKeys.dbconn == None:
    mongoConnect = MongoClient(PracticaKeys.strConnection)
    PracticaKeys.dbconn = mongoConnect[PracticaKeys.strDBConnection]
    
    # Definir dbConnPost fuera de cualquier función
dbConnPost = PracticaKeys.dbconn["clChisme"]
    


def getChisme():
    try:
        objFindColab = dbConnPost.find()
        listColab = list(objFindColab)
        
        for colab in listColab:
            # Convierto el ObjectId en string para que me lo acepte el programa
            colab['_id'] = str(colab['_id'])
        
        # Crear un diccionario con la clave 'Response' y la lista de colaboradores como valor
        response_data = {'Response': listColab}
        return jsonify(response_data)
    except Exception as e:
        print("error get colaboradores:", e)
        return jsonify(ResponseMessages.message500)

def postChisme():
    try:
        data = request.get_json()
        titulo = data.get('strTitulo')
        likes = data.get('intLikes')
        dislikes = data.get('intDislikes')
        chisme = data.get('strChisme')
        usuario = data.get('strUsuario')
        
        nuevo_chisme = {
            'strTitulo': titulo,
            'intLikes': likes,
            'intDislikes': dislikes,
            'strChisme': chisme,
            'strUsuario': usuario,
        }
        
        resultado = dbConnPost.insert_one(nuevo_chisme)
        
        if resultado.inserted_id:
            nuevo_chisme['_id'] = str(resultado.inserted_id)
            return jsonify(nuevo_chisme), 200
        else:
            return jsonify(ResponseMessages.message500), 500
    except Exception as e:
        print('Error al agregar chisme', e)
        return jsonify(ResponseMessages.message500), 500