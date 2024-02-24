from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from config import Config
from mysql_connection import get_connection
from mysql.connector import Error
import boto3
import openai
from datetime import datetime
import time


openai.api_key = Config.openapi_key

#GPT 대화 내용 생성 
class historyResource(Resource):

    def generate_text(self,prompt):
        response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        temperature=0.5,
        max_tokens=4000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0)
        return response.choices[0].text


    @jwt_required()
    def post(self) :
        data = request.get_json() 

        region = data['region']
        strDate = data['strDate']
        endDate = data['endDate']

        strDateTime = datetime.strptime(strDate, "%Y-%m-%d") # 여행시작 날짜  2023-09-17
        endDateTime = datetime.strptime(endDate, "%Y-%m-%d") # 여행 끝나는 날짜 2023-09-20
        
        #날짜 빼기#
        date_difference = endDateTime - strDateTime
        days_only = date_difference.days
        formatted_days = f"{days_only}"
        int_days = int(formatted_days)
        int_days = (int_days+1)
        days = str(int_days)+'일'
        print("변환된 문자열:", days)

        user_id = get_jwt_identity()

        keyward = days + '간의 ' + region + '여행 일정을 일별로 계획해줘, 저녁 일정 소개 후 [next]를 붙여줘'

        plan = self.generate_text(keyward)
        
        plan = plan.split('[next]')

        print(plan)

        # 빈 배열 공간이 나올 경우 지우기 
        if not plan[-1].strip():
            plan.pop()
      
        #공백 안들어가게 처리
        # 1일 선택시 0번째 항목 빼고 전부 제거,(1일인데 다수 기록 나오는 오류 방지용)
        i = 0
        if days == "1일":
           for i in range(len(plan)-1, 0, -1):
                plan.pop(i)
        else:
            for sentence in plan:
                plan[i] = sentence.strip()
                print(sentence)
                i = i+1

        
        try :
            #여행 기간에 따라 변경되는 쿼리.
            connection = get_connection()
            if len(plan) == 1:
                query = '''insert into history
                    (userId, region,firstDay,strDate,endDate)
                    values
                    (%s,%s, %s,%s,%s);'''
                record = (user_id,region,plan[0],strDateTime,endDateTime)

            elif len(plan) == 2:
                query = '''insert into history
                    (userId, region, firstDay,secondDay,strDate,endDate)
                    values
                    (%s, %s, %s,%s,%s,%s);'''
                record = (user_id,region,plan[0],plan[1],strDateTime,endDateTime)

            elif len(plan) == 3:
                query = '''insert into history
                    (userId, region, firstDay,secondDay,thirdDay,strDate,endDate)
                    values
                    (%s, %s, %s,%s,%s,%s,%s);'''
               
                record = (user_id,region,plan[0],plan[1],plan[2],strDateTime,endDateTime)

            elif len(plan) == 4:
                query = '''insert into history
                        (userId,region, firstDay,secondDay,thirdDay,fourthDay,strDate,endDate)
                        values
                        (%s, %s, %s,%s,%s,%s,%s,%s);'''
                record = (user_id,region,plan[0],plan[1],plan[2],plan[3],strDateTime,endDateTime)

            elif len(plan) == 5:
                query = '''insert into history
                        (userId,region, firstDay,secondDay,thirdDay,fourthDay,fifthDay,strDate,endDate)
                        values
                        (%s, %s, %s,%s,%s,%s,%s,%s,%s);'''
                record = (user_id,region,plan[0],plan[1],plan[2],plan[3],plan[4],strDateTime,endDateTime)

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

        return {"result" : "success",
            "items" : plan,
            "count" : len(plan)},200
    
#GPT 대화내역 리스트 
class historyListResource(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')
        try:
            connection = get_connection()
            query = '''select id,region,createdAt,strDate,endDate
                        from history
                        where userId = %s
                        order by createdAt desc
                        limit '''+offset+''' , '''+limit+''' ;'''
            
            record = (user_id,)
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

        # 날짜 포맷 변경 
        i = 0
        for row in result_list:
            result_list[i]['createdAt'] = row['createdAt'].isoformat().split("T")[0]
            result_list[i]['strDate'] = row['strDate'].isoformat().split("T")[0]
            result_list[i]['endDate'] = row['endDate'].isoformat().split("T")[0]
            i = i+1

        return {"result" : "success",
            "items" : result_list,
            "count" : len(result_list)},200

#GPT 대화내역 상세보기 
class historyInfoResource(Resource):
    @jwt_required()
    def get(self,history_id):

        user_id = get_jwt_identity()
       
      
        try:
            connection = get_connection()
            query = '''
                    select id, userId, region, firstDay, secondDay, thirdDay,fourthDay,fifthDay,createdAt,strDate,endDate
                    from history
                    where userId = %s and id = %s;
                    '''
            record = (user_id,history_id)
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
            result_list[i]['strDate'] = row['strDate'].isoformat()
            result_list[i]['endDate'] = row['endDate'].isoformat()
            i = i+1

        return {"result" : "success", "items" : result_list}, 200
    
   # 내 AI 기록 삭제 
    @jwt_required()
    def delete(self,history_id):
        user_id = get_jwt_identity()
        print(history_id)
        print(user_id)

        try:
            connection = get_connection()
            query = '''delete from history
                    where id = %s and userId = %s;'''
            
            record = (history_id,user_id)
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
        
    

