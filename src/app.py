import aiofiles
from cmath import log
from datetime import datetime, timedelta
import json
import requests
import time
import os
from posixpath import dirname
from this import d
from tkinter.messagebox import NO
from typing import List, Optional
from urllib.request import Request
import urllib.parse as urlparse
from urllib.parse import urlencode
from encrypt_user import encrypt_user

from fastapi import Depends, FastAPI, APIRouter, HTTPException, status, Request, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette_context import context
from starlette_context.middleware import ContextMiddleware
from starlette.types import ASGIApp

from const import make_upload_path, make_work_path, make_upload_field_path, make_api_result_field_path
from face_io import find_face

app = FastAPI(
    title='IDENTITY RUNTIME',
    descryption='IDENTITY RUNTIME',
    version='1.0.0'
)

for scheme in ['http', 'https']:
    for host in ['localhost', '127.0.0.1' ]:
        for port in [8000, 8001, 8002, 8003, 8005, 9000]:
            url = scheme + '://' + host + ':' + str(port)
            origins.append(url)


print("origins :", origins)

#
# Middleware
#

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_upload_size: int) -> None:
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == 'POST':
            if 'content-length' not in request.headers:
                return Response(status_code=status.HTTP_411_LENGTH_REQUIRED)
            content_length = int(request.headers['content-length'])
            if content_length > self.max_upload_size:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return await call_next(request)


app.add_middleware(LimitUploadSize, max_upload_size=50_000_000)  # ~50MB

router = APIRouter()


async def request_body(request: Request):
    method = str(request.method)
    if method == 'POST' or method == 'PUT' or method == 'PATCH':
        context.update(request_body=await request.json())


@app.middleware('http')
async def audit_log(request, call_next) -> Response:
    response = await call_next(request)
    response_body = b''
    # read response body
    async for chunk in response.body_iterator:
        response_body += chunk
    if 'request_body' in context:
        #logging.info('request body : {}'.format(context['request_body']))
        pass
    #logging.info('request body : {}'.format(response_body))
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )


app.add_middleware(ContextMiddleware)

app.include_router(router, dependencies=[Depends(request_body)])


###############################################################################
#
# User Authorizations
#
###############################################################################

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5 * 1000

users_db = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UsernameOldNewPassword(BaseModel):
    username: str
    old_password: str
    new_password: str


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class Command(BaseModel):
    device_id: str
    camera: int
    stamp: Optional[int]


class Status(BaseModel):
    device_id: str
    camera: int
    pictures: int


crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


def verify_password(plain_password, hashed_password):
    return crypt_context.verify(plain_password, hashed_password)


def read_user_db():
    with open('./user_db.json') as json_file:
        return json.load(json_file)


def get_password_hash(password):
    return crypt_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    with open('./user_db.json') as json_file:
        users_db = json.load(json_file)
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# 로그인
@app.post("/users/token", response_model=Token)
async def post_user_for_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    print('Request', request.client.host, request.method)
    users_db = read_user_db()
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        print('Incorrect username or password',
              request.client.host, request.method)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# 토큰 확인
@app.get("/users/token")
async def verify_token(request: Request, current_user: User = Depends(get_current_active_user)):
    print('Request', request.client.host, request.method)
    pass


# 로그아웃. 토큰 삭제
@app.delete("/users/token")
async def delete_access_token(request: Request, current_user: User = Depends(get_current_active_user)):
    pass


# 사용자 비밀번호 변경
@app.patch("/users/token", response_model=Token)
async def patch_user_password(request: Request, form_data: UsernameOldNewPassword):
    users_db = read_user_db()
    user = authenticate_user(
        users_db, form_data.username, form_data.old_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    encrypt_user(form_data.username, form_data.new_password,
                 form_data.new_password)

    users_db = read_user_db()
    user = authenticate_user(
        users_db, form_data.username, form_data.new_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/alive")
def is_station_alive(request: Request):
    return {"detail": "server is alive!"}

###############################################################################
#
# Image Analytics APIs
#
###############################################################################


@app.post("/data/{field}/{token}/upload")
async def post_data_field_token_upload(
        field: str, token: str, files: List[UploadFile] = File(..., description="Multiple files as UploadFile"),
        current_user: User = Depends(get_current_active_user)):
    data_field_path = make_upload_field_path(field, token)
    if not os.path.exists(data_field_path):
        os.makedirs(data_field_path)

    for file in files:
        bname = os.path.basename(file.filename)
        if bname.startswith('/'):
            bname = bname[1:]
        fpath = os.path.join(data_field_path, bname)

        global last_uploaded_file
        last_uploaded_file = fpath

        async with aiofiles.open(fpath, 'wb') as fp:
            while content := await file.read(1024):
                await fp.write(content)

        face_names = find_face(fpath)

    response = {
        "field": field,
        "token": token,
        "face-names": face_names
    }
    print (response)
    return response
