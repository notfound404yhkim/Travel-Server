# flask 프레임워크를 이용한 ,  Restful API 서버 개발

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restful import Api
from config import Config
from resources.follow import FollowResource
from resources.like import LikeResource

from resources.bookmark import BookmarkResource
from resources.mypage import UserInfoResource, bookmarkListResource, myScheduleListResource, myScheduleResource

from resources.posting import PostingListResource, PostingResource,PostingMeResource
from resources.history import historyResource,historyListResource,historyInfoResource
from resources.place import placeResource,placeListResource,placeInfoResource
from resources.comment import CommentResource


#  로그 아웃 관련된 임포트문. 
from resources.user import UserLoginResource, UserLogoutResource, UserRegisterResource, UserSecedeResource,UserGoogleRegisterResource, jwt_blocklist


app = Flask(__name__)

api = Api(app) 

# 환경변수 셋팅

app.config.from_object(Config)
# JWT 매니저를 초기화
jwt = JWTManager(app) 

# 로그 아웃 된 토큰으로 요청하는 경우,
# 실행되지 않도록 처리하는 코드.
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header,jwt_payload):
    jti = jwt_payload['jti']
    return jti in jwt_blocklist

# API를 구분해서 실행시키는 것은,
# HTTP METHOD 와 URL의 조합 이다.

# 경로(path)와 리소스(API 코드) 를 연결한다. 

api.add_resource( UserRegisterResource ,'/user/register')
api.add_resource( UserLoginResource,'/user/login')
api.add_resource( UserLogoutResource ,'/user/logout')
api.add_resource( UserSecedeResource, "/user/secede") # 회원 탈퇴


api.add_resource( PostingListResource, '/posting') # 기록 작성, 나를 제외한 모든 회원 기록 리스트 보기 
api.add_resource( PostingResource, '/posting/<int:posting_id>') # 기록 수정, 기록 삭제, 기록 상세보기
api.add_resource( PostingMeResource, '/posting/me') # 내 기록 리스트 보기 

api.add_resource( CommentResource, '/comment/<int:posting_id>') # 댓글 추가, 삭제, 수정



api.add_resource( historyResource,'/history') # GPT 대화 내용 생성
api.add_resource( historyInfoResource,'/history/<int:history_id>') # GPT 대화 내용 상세보기 , 삭제 
api.add_resource( historyListResource,'/historylist') # GPT 대화 내용 리스트 가져오기

api.add_resource( placeResource,'/place') #축제 또는 핫플 작성,  축제 또는 핫플 이미지 가져오기 
api.add_resource( placeInfoResource,'/place/<int:place_id>') #축제 또는 핫플 상세 보기 
api.add_resource( placeListResource,'/placelist') # 축제 또는 핫플 리스트 보기  

api.add_resource( FollowResource , '/follow/<int:followee_id>') #친구 추가, 삭제 
api.add_resource( LikeResource , '/like/<int:posting_id>') # 좋아요 ,좋아요 취소 

api.add_resource( BookmarkResource , '/bookmark/<int:posting_id>') # 즐겨찾기 ,즐겨찾기 취소 
api.add_resource( UserInfoResource, "/mypage/userInfo") # 프로필 정보, 프로필 수정
api.add_resource( myScheduleListResource, "/mypage/mySchedule") # 일정 추가, 일정 리스트
api.add_resource( myScheduleResource, "/mypage/mySchedule/<int:myScheduleId>") # 일정 상세보기 , 일정 삭제 
api.add_resource( bookmarkListResource, "/mypage/bookmark") # 북마크한 글 리스트


api.add_resource( UserGoogleRegisterResource , '/user/googleRegister')

if __name__ == '__main__':
    app.run()




