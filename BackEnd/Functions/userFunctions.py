from flask import jsonify, request
from pymongo import MongoClient
from bson import ObjectId
from bson.binary import Binary
from flask_cors import CORS
import BackEnd.GlobalInfo.Keys as PracticaKeys
import BackEnd.GlobalInfo.ResponseMessages as ResponseMessages


if PracticaKeys.dbconn == None:
    mongoConnect = MongoClient(PracticaKeys.strConnection)
    PracticaKeys.dbconn = mongoConnect[PracticaKeys.strDBConnection]
    
    # Aquí contrato la consulta que estaré utilizando para colaboradores
    dbConnUsers = PracticaKeys.dbconn["clUsuarios"]


def login():
    try:
        # Obtener datos del cuerpo de la solicitud (request body)
        data = request.get_json()
        username = data.get('strUsuario')
        password = data.get('strPassword')

        # Buscar usuario en la base de datos por nombre de usuario y contraseña
        user = dbConnUsers.find_one({'strUsuario': username, 'strPassword': password})

        if user:
            # Encontrado, devolver un mensaje de éxito o cualquier otro dato que desees
            return jsonify({'message': 'Inicio de sesión exitoso'})
        else:
            # Usuario no encontrado, devolver un mensaje de error o código de estado apropiado
            return jsonify({'message': 'Credenciales inválidas'}, ResponseMessages.message401)

    except Exception as e:
        print("Error en la autenticación:", e)
        return jsonify(ResponseMessages.message500)
    
def postUsuario():
    try:
        data = request.get_json()
        usuario = data.get('strUsuario')
        password = data.get('strPassword')
        
        nuevo_Usuario ={
            'strUsuario':usuario,
            'strPassword':password
        }
        
        resultado = dbConnUsers.insert_one(nuevo_Usuario)
        
        if resultado.inserted_id:
            nuevo_Usuario['_id'] = str(resultado.inserted_id)
            return jsonify(nuevo_Usuario, ResponseMessages.message200)
        else:
            return jsonify(ResponseMessages.message500)
        
    except Exception as e:
        print('Error al agregar chisme', e)
        return jsonify(ResponseMessages.message500)
    
    
    
def postAvatar():
    try:
        strUsuario = request.form['strUsuario']
        return setAvatar(strUsuario)
    except Exception as e:
        print("Error al procesar la solicitud:", e)
        return jsonify(ResponseMessages.message500)

    
def setAvatar(strUsuario):
    try:
        binImagen = request.files['imagen']
        datosImagen = binImagen.read()
    
        resultado = dbConnUsers.update_one({'strUsuario': strUsuario}, {'$set': {'binAvatar': datosImagen}})
        
        if resultado.modified_count == 1:
            return jsonify({'mensaje': 'Imagen subida correctamente'}), 200
        else:
            return jsonify({'mensaje': 'Usuario no encontrado'}), 404
    except Exception as e:
        print("Error al subir imagen:", e)
        return jsonify(ResponseMessages.message500)
    

