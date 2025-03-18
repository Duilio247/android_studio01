import os
import cx_Oracle
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración de conexión a Oracle
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
dsn = os.getenv("DB_DSN")

# Función para obtener una conexión a la base de datos
def get_db_connection():
    connection = cx_Oracle.connect(user=user, password=password, dsn=dsn)
    return connection

# Función para ejecutar consultas
def execute_query(query, params=None, fetchone=False):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if query.strip().upper().startswith("SELECT"):
            if fetchone:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
            
            # Convertir a lista de diccionarios
            columns = [col[0] for col in cursor.description]
            if fetchone:
                if result:
                    return dict(zip(columns, result))
                return None
            else:
                return [dict(zip(columns, row)) for row in result]
        else:
            connection.commit()
            return {"affected_rows": cursor.rowcount}
    finally:
        cursor.close()
        connection.close()

# Ruta principal
@app.route('/', methods=['GET'])
def home():
    return "mensaje API con Oracle funcionando correctamente"

# Ejemplo de endpoint para obtener datos de una tabla
@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    try:
        usuarios = execute_query("SELECT * FROM usuarios")
        return jsonify({"usuarios": usuarios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ejemplo de endpoint para obtener un usuario específico
@app.route('/api/usuarios/<int:usuario_id>', methods=['GET'])
def get_usuario(usuario_id):
    try:
        usuario = execute_query("SELECT * FROM usuarios WHERE id = :id", {"id": usuario_id}, fetchone=True)
        if usuario:
            return jsonify({"usuario": usuario})
        return jsonify({"mensaje": "Usuario no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ejemplo de endpoint para crear un nuevo usuario
@app.route('/api/usuarios', methods=['POST'])
def create_usuario():
    try:
        if not request.json or 'nombre' not in request.json or 'email' not in request.json:
            return jsonify({"mensaje": "Datos incompletos"}), 400
        
        query = """
        INSERT INTO usuarios (nombre, email) 
        VALUES (:nombre, :email) 
        RETURNING id INTO :id
        """
        
        # Para Oracle, necesitamos manejar el retorno del ID de manera especial
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Crear variable de salida para el ID
        id_var = cursor.var(cx_Oracle.NUMBER)
        
        # Ejecutar la inserción
        cursor.execute(query, {
            "nombre": request.json['nombre'],
            "email": request.json['email'],
            "id": id_var
        })
        
        # Confirmar la transacción
        connection.commit()
        
        # Obtener el ID generado
        nuevo_id = id_var.getvalue()
        
        # Cerrar recursos
        cursor.close()
        connection.close()
        
        # Devolver el usuario creado
        nuevo_usuario = {
            "id": nuevo_id,
            "nombre": request.json['nombre'],
            "email": request.json['email']
        }
        
        return jsonify({"usuario": nuevo_usuario}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ejemplo de endpoint para actualizar un usuario
@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
def update_usuario(usuario_id):
    try:
        if not request.json:
            return jsonify({"mensaje": "Sin datos para actualizar"}), 400
            
        # Verificar si el usuario existe
        usuario = execute_query("SELECT * FROM usuarios WHERE id = :id", {"id": usuario_id}, fetchone=True)
        if not usuario:
            return jsonify({"mensaje": "Usuario no encontrado"}), 404
            
        # Construir la consulta de actualización dinámicamente
        update_fields = []
        params = {"id": usuario_id}
        
        if 'nombre' in request.json:
            update_fields.append("nombre = :nombre")
            params["nombre"] = request.json['nombre']
            
        if 'email' in request.json:
            update_fields.append("email = :email")
            params["email"] = request.json['email']
            
        if not update_fields:
            return jsonify({"mensaje": "Sin campos válidos para actualizar"}), 400
            
        query = f"UPDATE usuarios SET {', '.join(update_fields)} WHERE id = :id"
        execute_query(query, params)
        
        # Obtener el usuario actualizado
        usuario_actualizado = execute_query("SELECT * FROM usuarios WHERE id = :id", {"id": usuario_id}, fetchone=True)
        return jsonify({"usuario": usuario_actualizado})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ejemplo de endpoint para eliminar un usuario
@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
def delete_usuario(usuario_id):
    try:
        # Verificar si el usuario existe
        usuario = execute_query("SELECT * FROM usuarios WHERE id = :id", {"id": usuario_id}, fetchone=True)
        if not usuario:
            return jsonify({"mensaje": "Usuario no encontrado"}), 404
            
        execute_query("DELETE FROM usuarios WHERE id = :id", {"id": usuario_id})
        return jsonify({"mensaje": "Usuario eliminado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)