from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
import boto3
from datetime import datetime

# 기록 관련
class PostingListResource(Resource):

    def detect_labels(self, photo, bucket):

        client = boto3.client('rekognition',
                              'ap-northeast-2',
                              aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY)

        response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}},
        MaxLabels=5,
        # Uncomment to use image properties and filtration settings
        #Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"],
        #Settings={"GeneralLabels": {"LabelInclusionFilters":["Cat"]},
        # "ImageProperties": {"MaxDominantColors":10}} 
        )

        print('Detected labels for ' + photo)
        print()

        label_list = [] 
        for label in response['Labels']:
            print("Label: " + label['Name']) 
            print("Confidence: " + str(label['Confidence']))
            if label['Confidence'] >= 90: #Confidence 가 90 이상인것만 출력하도록 .
                label_list.append(label['Name'])
            

        return label_list
    
    # 기록 작성
    @jwt_required()
    def post(self) :

        # 1 클라이언트로부터 데이터 받아온다.
        file = request.files.get('image')
        title = request.form.get('title')
        content = request.form.get('content')
        
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
        
        # rekogintion 서비스를 이용해서
        # object detection 하여, 태그 이름을 가져온다.

        tag_list = self.detect_labels(new_file_name, Config.S3_BUCKET)

        print(tag_list)

        # DB의 posting 테이블에 데이터를 넣어야 하고,
        # tag_name 테이블과 tag 테이블에도 데이터를
        # 넣어줘야 한다.

        try :
            connection = get_connection()

            # 1. posting 테이블에 데이터를 넣어준다.
            query = '''insert into posting
                    (userId, imgUrl,title,content)
                    values
                    (%s, %s, %s,%s);'''
            record = (user_id, 
                      Config.S3_LOCATION+new_file_name,title,
                      content)
            cursor = connection.cursor()
            cursor.execute(query, record)

            posting_id = cursor.lastrowid

            # 2. tag_name 테이블 처리를 해준다.
            #    리코그니션을 이용해서 받아온 label이,
            #    tag_name테이블에 이미 존재하면, 
            #    그 아이디만 가져오고,
            #    그렇지 않으면, 테이블에 인서트 한후에
            #    그 아이디를 가져온다. 

            for tag in tag_list :
                tag = tag.lower()
                query = '''select *
                        from tag_name
                        where name = %s;'''
                record = (tag , )
                
                cursor = connection.cursor(dictionary=True)
                cursor.execute(query, record)

                result_list = cursor.fetchall()

                # 태그가 이미 테이블에 있으면, 아이디만 가져오고
                if len(result_list) != 0 :
                    tag_name_id = result_list[0]['id']
                else :
                    # 태그가 테이블에 없으면, insert 한다.
                    query = '''insert into tag_name
                            (name)
                            values
                            (%s);'''
                    record = (tag, )
                    cursor = connection.cursor()
                    cursor.execute(query, record)

                    tag_name_id = cursor.lastrowid

                # 3. 위의 태그네임 아이디와, 포스팅 아이디를
                #    이용해서, tag 테이블에 데이터를 넣어준다.   
                    
                query = '''insert into tag
                        (postingId, tagNameId)
                        values
                        (%s, %s);'''
                record = (posting_id, tag_name_id)

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

    # 나를 제외한 모든 회원 기록 리스트 보기 (좋아요 순)
    @jwt_required()
    def get(self):

        user_id = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')

        try:
            connection = get_connection()
            query = '''
                    select p.id, p.userId, u.name, p.imgUrl, p.title, p.content, p.createdAt, count(l.id) as likeCnt
                    from posting p
                    left join likes l
                    on p.id = l.postingId
                    left join user u
                    on p.userId = u.id
                    where p.userId != %s
                    group by p.id
                    order by likeCnt desc
                    limit ''' + offset + ''' , ''' + limit + ''';
                    '''
            
            record = (user_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()
            # print(result_list)

            cursor.close()
            connection.close()

        except Error as e:
            print(Error)
            cursor.close()
            connection.close()
            return{"error" : str(e)},500 

        # 날짜 포맷 변경 
        i = 0
        for row in result_list:
            result_list[i]['createdAt'] = row['createdAt'].isoformat()
            i = i+1

        return {"result" : "success", "items" : result_list, "count" : len(result_list)}, 200
    
# 기록 관련
class PostingResource(Resource):

    # 기록 삭제
    @jwt_required()
    def delete(self,posting_id):
        user_id = get_jwt_identity()
        try:
            connection = get_connection()
            query = ''' delete from posting
                        where id =%s and userId =%s;'''
            
            record = (posting_id, user_id)

            print(user_id)
            
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
    
    #기록 수정
    @jwt_required()
    def put(self,posting_id):
        data = request.get_json()
        user_id = get_jwt_identity()
       
        try:
            connection = get_connection()
            query = ''' update posting
                        set title = %s,
                        content = %s
                        where id = %s and userId = %s;'''
            
            record = (data['title'],data['content'],
                      posting_id,user_id)
            
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
    
    # 기록 상세보기
    @jwt_required()
    def get(self, posting_id):
        user_id = get_jwt_identity()

        try:
            connection = get_connection()

            query = '''
                    select p.id postId, u.name, p.title, p.imgUrl, p.content,
                    u.id userId, u.name, p.createdAt, p.updatedAt, count(distinct l.id) as likeCnt, if(l2.id is null, 0,1) as isLike, 
                    count(distinct b.id) as bookmarkCnt, if(b2.id is null, 0, 1) as isBookmark
                    from posting p
                    join user u 
                    on p.userId = u.id
                    left join likes l 
                    on p.id = l.postingId
                    left join likes l2
                    on p.id = l2.postingId and l2.userId = %s
                    left join bookmark b
                    on p.id = b.postingId
                    left join bookmark b2
                    on p.id = b2.postingId and b2.userId = %s
                    where p.id = %s;
                    '''
            record = (user_id, user_id, posting_id)
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, record)

            result_list = cursor.fetchall()

            # if result_list[0]['postId'] == None:
            #     return {'error' : '데이터 없음'},400
            
            post = result_list[0]

            query = '''select concat('# ',name) as tag
                        from tag t
                        join tag_name tn
                        on t.tagNameId = tn.id
                        where t.postingId = %s;'''
            
            record = (posting_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query,record)

            result_list = cursor.fetchall()
            print(result_list)

            tag = []
            for tag_dict in result_list:
                tag.append(tag_dict['tag'])

            query = '''
                    select c.id commentId, c.postingId as postid, u.id, u.name, u.profileImg, c.content, c.createdAt
                    from comment c
                    left join user u
                    on c.userId = u.Id
                    where c.postingId = %s;
                    '''    
            record = (posting_id, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            comment_list = cursor.fetchall()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)},500
    
        post['createdAt'] = post['createdAt'].isoformat()
        post['updatedAt'] = post['updatedAt'].isoformat()

        i = 0
        for row in comment_list:
            comment_list[i]['createdAt'] = row['createdAt'].isoformat()
            i = i+1

        return {"result" : "success", "items" : post, "tag" : tag, "comments" : comment_list }, 200

# 내 기록 리스트 보기(최신날짜 순)
class PostingMeResource(Resource):

    @jwt_required()
    def get(self):

        user_id = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')

        try:
            connection = get_connection()
            query = '''
                    select p.id, p.userId, u.name, p.imgUrl, p.title, p.content, p.createdAt
                    from posting p
                    left join user u
                    on p.userId = u.id
                    where userId = %s
                    order by createdAt desc
                    limit '''+ offset + ''' , ''' + limit + ''';
                    '''
            record = (user_id,)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query,record)

            result_list = cursor.fetchall()
           
            # print(result_list)
            
            cursor.close()
            connection.close()

        except Error as e:
            print(Error)
            cursor.close()
            connection.close()
            return{"error" : str(e)},500 

        # 날짜 포맷 변경 
        i = 0
        for row in result_list:
            result_list[i]['createdAt'] = row['createdAt'].isoformat()
            i = i+1

        return {"result" : "success", "items" : result_list, "count" : len(result_list)}, 200