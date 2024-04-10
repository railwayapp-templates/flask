from flask import request, jsonify
from pymongo import MongoClient
from bson import ObjectId,json_util
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

            # Convertir bytes a formato hexadecimal
            for key, value in colab.items():
                if isinstance(value, bytes):
                    colab[key] = value.hex()
        
        # Crear un diccionario con la clave 'Response' y la lista de colaboradores como valor
        response_data = {'Response': listColab}
        return jsonify(response_data)
    except Exception as e:
        print("Error al obtener los colaboradores:", e)
        # Si ocurre algún error, devuelve un mensaje de error interno del servidor
        return jsonify({"error": str(e), "message": "Ha ocurrido un error al obtener los colaboradores"})


def postChisme():
    try:
        data = request.get_json()
        titulo = data.get('strTitulo')
        categoria = data.get('strCategoria')
        likes = data.get('intLikes')
        dislikes = data.get('intDislikes')
        chisme = data.get('strChisme')
        usuario = data.get('strUsuario')

        categorias_permitidas = ['Amor', 'Memes', 'Preguntas', 'Confesiones', 'Avisos']

        if categoria.capitalize() in categorias_permitidas:
            nuevo_chisme = {
                'strTitulo': titulo,
                'strCategoria': categoria,
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
        else:
            return "La categoría proporcionada no es válida. Por favor, elige una de las siguientes categorías: Amor, Memes, Preguntas, Confesiones, Avisos"
    except Exception as e:
        print('Error al agregar chisme', e)
        return jsonify(ResponseMessages.message500), 500
    
    
def obtener_chismes():
    try:
        data = request.get_json()
        categoria = data.get('categoria')
        if not categoria:
            return jsonify({'error': 'No se proporcionó una categoría'}), 400

        categorias_permitidas = ['Amor', 'Avisos', 'Preguntas', 'Memes', 'Confesiones']
        if categoria not in categorias_permitidas:
            return jsonify({'error': 'Categoría no permitida'}), 400

        chismes_categoria = dbConnPost.find({'strCategoria': categoria})

        # Convertir ObjectId a cadenas en cada documento
        chismes_categoria = [serialize_doc(chisme) for chisme in chismes_categoria]

        return jsonify(chismes_categoria), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def serialize_doc(doc):
    """Convierte ObjectId a cadenas en un documento"""
    if isinstance(doc, dict):
        return {key: str(value) if isinstance(value, ObjectId) else value for key, value in doc.items()}
    return doc

def maslikes():
    try:
        # Buscar el chisme con más likes
        chisme = dbConnPost.find_one(sort=[('intLikes', -1)])

        if chisme:
            # Convertir ObjectId a string
            chisme['_id'] = str(chisme['_id'])
            # Devolver toda la información del chisme como respuesta JSON
            return jsonify(chisme), 200
        else:
            return jsonify({'error': 'No hay chismes disponibles'}), 404
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor'}), 500

    
