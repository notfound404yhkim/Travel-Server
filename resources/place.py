from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
import boto3
from datetime import datetime
import re

#축제 또는 핫플 관련 
class placeResource(Resource):
    #축제 또는 핫플 올리기 
    @jwt_required()
    def post(self) :

        # 1 클라이언트로부터 데이터 받아온다.
        option = request.form.get('option')
        region = request.form.get('region')
        placeName = request.form.get('placeName')
        content = request.form.get('content')
        file = request.files.get('image')

        #공백 안들어가게 처리
        region = region.strip()
        placeName = placeName.strip()
       
        user_id = get_jwt_identity()

        # 2. 사진을 s3에 저장한다.
        if file is None :
            return {'error' : '파일을 업로드 하세요'}, 400
        

        # 파일명을 회사의 파일명 정책에 맞게 변경한다.
        # 파일명은 유니크 해야 한다. 

        current_time = datetime.now()

        new_file_name = current_time.isoformat().replace(':', '_') + str(user_id) + '.jpg'  

        # 유저가 올린 파일의 이름을, 
        # 새로운 파일 이름으로 변경한다. 
        file.filename = new_file_name

        s3 = boto3.client('s3',
                    aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY )

        try :
            s3.upload_fileobj(file, 
                              Config.S3_BUCKET,
                              file.filename,
                              ExtraArgs = {'ACL' : 'public-read' , 
                                           'ContentType' : 'image/jpeg'} )
        except Exception as e :
            print(e)
            return {'error' : str(e)}, 500
        
        try :
            connection = get_connection()

            if option == '0':   #핫플인경우 

                query = '''insert into place
                        (userId, `option`,region,placeName,content,imgurl)
                        values
                        (%s, %s, %s,%s,%s,%s);'''
                
                record = (user_id,option,region,placeName,content,
                        Config.S3_LOCATION+new_file_name)
                
            else :  #축제인경우 

                strDate = request.form.get('strDate')
                endDate = request.form.get('endDate')

                strDate = datetime.strptime(strDate, "%Y-%m-%d")

                print("축제 시작 날짜:", strDate)  ##날짜 형식 2023-09-15

                endDate = datetime.strptime(endDate, "%Y-%m-%d")

                print("축제 끝나는 날짜:", endDate)  ##날짜 형식 2023-09-17

                query = '''insert into place
                        (userId, `option`,region,placeName,content,imgurl,strDate,endDate)
                        values
                        (%s, %s, %s,%s,%s,%s,%s,%s);'''
                
                record = (user_id,option,region,placeName,content,
                        Config.S3_LOCATION+new_file_name,strDate,endDate)

            
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
    
    #축제 또는 핫플 이미지 가져오기 
    def get(self):
        region = request.args.get('region')
        option = request.args.get('option')
        offset = request.args.get('offset')
        limit = request.args.get('limit')

        print(option)
        try:
            connection = get_connection()

            if option == '0':
                query = '''select id,imgUrl
                            from place
                            where region = %s and place.option = 0
                            order by createdAt desc
                            limit '''+offset+''' , '''+limit+''' ;'''
                
            elif option == '1':
                query = '''select id,imgUrl
                            from place
                            where region = %s and place.option = 1
                            order by createdAt desc
                            limit '''+offset+''' , '''+limit+''' ;'''
            
            record = (region,)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query,record)

            result_list = cursor.fetchall()
            print(result_list)
        
            cursor.close()
            connection.close()

        except Error as e:
            print(Error)
            cursor.close()
            connection.close()
            return{"error" : str(e)},500 

        return {"result" : "success",
            "items" : result_list,
            "count" : len(result_list)},200
    
    
# 축제 또는 핫플 상세보기
class placeInfoResource(Resource):

    def get(self, place_id):

        option = request.args.get('option')
       
        try:
            connection = get_connection()
            if option == '0':
                query = '''
                        select `option`,region,placeName,content,imgUrl
                        from place
                        where id =%s;
                        '''
            elif option == '1':
                query = '''
                        select `option`,region,placeName,content,imgUrl,strDate,endDate
                        from place
                        where id =%s;
                        '''
                
            record = (place_id,)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, record)

            result_list = cursor.fetchall()

            cursor.close()
            connection.close()

            print(result_list)

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return{"error" : str(e)},500
        #축제인 경우만 날짜 처리 
        if option == '1':
            i = 0
            for row in result_list:
                result_list[i]['strDate'] = row['strDate'].isoformat().split("T")[0]
                result_list[i]['endDate'] = row['endDate'].isoformat().split("T")[0]
                i = i+1        
        
        return {"result" : "success", "items" : result_list}
    

#축제 또는 행사 리스트 보기     
class placeListResource(Resource):
    @jwt_required()
    def get(self):
        region = request.args.get('region')
        option = request.args.get('option')
        offset = request.args.get('offset')
        limit = request.args.get('limit')


        print(option)
        try:
            connection = get_connection()
            

            if option == '0':
                query = '''select id,region,placeName,imgUrl,content,createdAt
                            from place
                            where region = %s and place.option = 0
                            order by createdAt desc
                            limit '''+offset+''' , '''+limit+''' ;'''
                
            elif option == '1':
                query = '''select id,region,placeName,imgUrl,content,strDate,endDate,createdAt
                            from place
                            where region = %s and place.option = 1
                            order by createdAt desc
                            limit '''+offset+''' , '''+limit+''' ;'''
            
            record = (region,)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query,record)

            result_list = cursor.fetchall()
           
            print(result_list)
            
            if option == '0' :
                i = 0
                for row in result_list:
                    result_list[i]['createdAt'] = row['createdAt'].isoformat().split("T")[0]

                    i = i+1

            elif option == '1' :
                i = 0
                for row in result_list:
                    result_list[i]['createdAt'] = row['createdAt'].isoformat().split("T")[0]
                    result_list[i]['strDate'] = row['strDate'].isoformat().split("T")[0]
                    result_list[i]['endDate'] = row['endDate'].isoformat().split("T")[0]
                    i = i+1
                    
            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            
            return{"error" : str(e)}, 500


        return {"result" : "success",
            "items" : result_list,
            "count" : len(result_list)},200

