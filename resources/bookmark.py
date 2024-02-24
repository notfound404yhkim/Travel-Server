from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required #요청 받기
from flask_restful import Resource
from mysql_connection import get_connection
from mysql.connector import Error


# 좋아요, 관련 
class BookmarkResource(Resource):
    # 추가 
    @jwt_required()
    def post(self,posting_id):
        user_id = get_jwt_identity()
        print(posting_id)

        try:
            connection = get_connection()
            query = '''insert into bookmark
                        (userId, postingId)
                        values
                        (%s,%s);'''
            
            record = (user_id,posting_id)
            cursor = connection.cursor()
            cursor.execute(query,record)
            connection.commit()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return{"error" : str(e)},500
        
        return{"result" : "success" },200
        
    @jwt_required()
    def delete(self,posting_id):
        user_id = get_jwt_identity()
    
        try:
            connection = get_connection()
            query = '''delete from bookmark
                       where userId = %s and postingId = %s;'''
            
            record = (user_id,posting_id)
            cursor = connection.cursor()
            cursor.execute(query,record)
            connection.commit()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return{"error" : str(e)},500
        
        return{"result" : "success" },200
    