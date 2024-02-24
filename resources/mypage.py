from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
import boto3
from datetime import datetime

# 내 정보 관련
class UserInfoResource(Resource) :

    # 내 정보 수정
    @jwt_required()
    def put(self) :
        
        user_id = get_jwt_identity()
        profileImg = request.files.get("image")
        name = request.form.get("name")
        
        # # 프로필 사진만 변경할 때
        if profileImg is not None and profileImg.filename != '' and name == "" :
            current_time = datetime.now()

            new_file_name = current_time.isoformat().replace(':', '_') + str(user_id) + '.jpg'  

            profileImg.filename = new_file_name

            s3 = boto3.client('s3',
                        aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY )

            try :
                s3.upload_fileobj(profileImg, 
                                Config.S3_BUCKET,
                                profileImg.filename,
                                ExtraArgs = {'ACL' : 'public-read' , 
                                            'ContentType' : 'image/jpeg'} )
            except Exception as e :
                print(e)
                return {'error' : str(e)}, 500
            
            try :
                connection = get_connection()

                query = '''
                    update user
                    set profileImg = %s
                    where id = %s;
                    '''
                record = (Config.S3_LOCATION+new_file_name, user_id)
                cursor = connection.cursor()
                cursor.execute(query, record)
                connection.commit()

                cursor.close()
                connection.close()

            except Error as e :
                print(e)
                cursor.close()
                connection.close()
                return {"error" : str(e)}, 500

            return {"result" : "success"}, 200

        # 이름만 변경할 때
        elif profileImg.filename == '' and name != "" : 
            try :
                connection = get_connection()

                query = '''
                        update user
                        set name = %s
                        where id = %s;
                        '''
                record = (name, user_id)
                cursor = connection.cursor()
                cursor.execute(query, record)
                connection.commit()

                cursor.close()
                connection.close()

            except Error as e :
                print(e)
                cursor.close()
                connection.close()
                return {"error" : str(e)}, 500

            return {"result" : "success"}, 200
        
        # 프로필 사진, 이름 둘 다 변경할 때
        if profileImg is not None and profileImg.filename != '' and name != "" :
            current_time = datetime.now()

            new_file_name = current_time.isoformat().replace(':', '_') + str(user_id) + '.jpg'   

            profileImg.filename = new_file_name

            s3 = boto3.client('s3',
                        aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY )

            try :
                s3.upload_fileobj(profileImg, 
                                Config.S3_BUCKET,
                                profileImg.filename,
                                ExtraArgs = {'ACL' : 'public-read' , 
                                            'ContentType' : 'image/jpeg'} )
            except Exception as e :
                print(e)
                return {'error' : str(e)}, 500
            
            try :
                connection = get_connection()

                query = '''
                        update user
                        set name = %s, profileImg = %s
                        where id = %s;
                        '''
                record = (name, Config.S3_LOCATION+new_file_name, user_id)
                cursor = connection.cursor()
                cursor.execute(query, record)
                connection.commit()

                cursor.close()
                connection.close()

            except Error as e :
                print(e)
                cursor.close()
                connection.close()
                return {"error" : str(e)}, 500

            return {"result" : "success"}, 200
        
    # 내 정보 불러오기
    @jwt_required()
    def get(self) :

        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''
                    select id, profileImg, name, email 
                    from user
                    where id = %s;
                    '''
            record = (user_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 500

        return {"result" : "success", "items" : result_list}, 200
    
# 내 일정 추가, 리스트
class myScheduleListResource(Resource) :
    
    # 내 일정 추가
    @jwt_required()
    def post(self) :
        user_id = get_jwt_identity()
        # place_list = request.args.getlist("place")
        # print(place_list)
        # place_list = [x for x in place_list if x.strip()]
        # place_list = [x.strip() for sublist in place_list for x in sublist.split(',') if x.strip()]
        # place_list = [item for sublist in [x.split(',') for x in place_list] for item in sublist if item.strip()]
        # # place_list = [x.rstrip(',') for x in place_list]
        #  place_list = list(filter(None, place_list))
        data = request.get_json()
        # print(place_list)
        try :
            connection = get_connection()
            query = '''
                    insert into mySchedule
                    (userId, region, strDate, endDate, content)
                    values
                    (%s, %s, %s, %s, %s);
                    '''
            record = (user_id, data["region"], data["strDate"], data["endDate"], data["content"])
            cursor = connection.cursor()
            cursor.execute(query, record)
            myScheduleId = cursor.lastrowid
            print("추가된 일정테이블 id : " + str(myScheduleId))
            for place in data["placeId"] :
                query = '''
                        select imgUrl
                        from place
                        where place.option = 0 and id = %s;
                        '''
                record = (place, )
                cursor = connection.cursor(dictionary=True)
                cursor.execute(query, record)
                imgUrl = cursor.fetchone()
                print(imgUrl)
                query = '''
                        insert into mySchedule_place
                        (myScheduleId, placeId, imgUrl)
                        values
                        (%s, %s, %s);
                        '''
                record = (myScheduleId, place, imgUrl["imgUrl"])
                cursor = connection.cursor()
                cursor.execute(query, record)
            connection.commit()
            cursor.close()
            connection.close()
        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 500
        return {"result" : "success"}, 200

    # 내 일정 리스트     
    @jwt_required()
    def get(self) :

        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''
                    select m.*, mp.imgUrl 
                    from mySchedule m
                    join mySchedule_place mp
                    on m.id = mp.myScheduleId
                    where m.userId = %s
                    group by m.id
                    order by createdAt desc; 
                    '''
            record = (user_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 500
        
        i = 0
        for row in result_list:
            result_list[i]['createdAt'] = row['createdAt'].isoformat()
            result_list[i]['strDate'] = row['strDate'].isoformat()
            result_list[i]['endDate'] = row['endDate'].isoformat()
            i = i+1
        
        return {"result" : "success", "items" : result_list, "count" : len(result_list)}, 200
    
# 내 일정 상세보기
class myScheduleResource(Resource) :
    
    @jwt_required()
    def get(self, myScheduleId) :
        try :
            connection = get_connection()
            query = '''
                    select *
                    from mySchedule
                    where id = %s;
                    '''
            record = (myScheduleId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result = cursor.fetchone()
            query = '''
                    select id,imgUrl
                    from mySchedule_place
                    where myScheduleId = %s;
                    '''
            record = (myScheduleId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            place_list = cursor.fetchall()
            cursor.close()
            connection.close()
        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 500
        result['createdAt'] = result['createdAt'].isoformat()
        result['strDate'] = result['strDate'].isoformat()
        result['endDate'] = result['endDate'].isoformat()
        return {"result" : "success", "items" : result, "place_list" : place_list}, 200
    
    # 내 일정삭제
    @jwt_required()
    def delete(self,myScheduleId):
        user_id = get_jwt_identity()
        print(myScheduleId)
        print(user_id)

        try:
            connection = get_connection()
            query = '''delete from mySchedule
                    where id = %s and userId = %s;'''
            
            record = (myScheduleId,user_id)
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
    
# 북마크한 포스팅 리스트
class bookmarkListResource(Resource) :

    @jwt_required()
    def get(self) :

        user_id = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''
                    select b.id, b.postingId, p.imgUrl, p.title, p.content, p.createdAt, u.name
                    from bookmark b
                    left join posting p
                    on b.postingId = p.id
                    left join user u 
                    on u.id = p.userId
                    where b.userId = %s
                    order by p.createdAt desc;
                    '''
            record = (user_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            cursor.close()
            connection.close()

        except Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 500
        
        i = 0
        for row in result_list:
            result_list[i]['createdAt'] = row['createdAt'].isoformat()
            i = i+1

        return {"result" : "success", "items" : result_list, "count" : len(result_list)}, 200         