from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
import boto3
from datetime import datetime


#댓글 관련 
class CommentResource(Resource):
    #댓글 추가 
    @jwt_required()
    def post(self,posting_id) :
        # 1 클라이언트로부터 데이터 받아온다.
        data = request.get_json()
        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            # 1. cooment  테이블에 데이터를 넣어준다.
            query = '''insert into comment
                    (userId, postingId,content)
                    values
                    (%s, %s, %s);'''
            
            record = (user_id,posting_id,data['content'] )
            cursor = connection.cursor()
            cursor.execute(query, record)

            connection.commit()
            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500

        return {'result' : 'success'}, 200
    

    #댓글 삭제
    @jwt_required()
    def delete(self,posting_id):
        user_id = get_jwt_identity()
        comment_id = request.args.get('commentId')

        try:
            connection = get_connection()
            query = ''' delete from comment
                        where id = %s and userId =%s and postingId = %s;'''
            
            record = (comment_id, user_id,posting_id)

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

        return{"result" : "success"},200 
    

    #댓글 수정
    @jwt_required()
    def put(self,posting_id):
        data = request.get_json()
        user_id = get_jwt_identity()
        comment_id = request.args.get('commentId')
       
        try:
            connection = get_connection()
            query = ''' update comment
                        set content = %s
                        where id = %s and userId =%s and postingId = %s;'''
            
            record = (data['content'],
                      comment_id,user_id,posting_id)
            
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

        return{"result" : "success"},200 
    
