import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware для аутентификации API запросов."""
    
    def __init__(self, app, secret_key: Optional[str] = None):
        super().__init__(app)
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "change-this-secret-key")
        self.exempt_paths = {"/", "/health", "/mini-app/static"}
        self.algorithm = "HS256"
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаем статические файлы и health check
        if request.url.path in self.exempt_paths or request.url.path.startswith("/mini-app/static"):
            return await call_next(request)
            
        # Проверяем JWT токен
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Отсутствует или некорректный токен авторизации для {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization token"}
            )
            
        token = auth_header.split(" ")[1]
        
        try:
            # Декодируем токен
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Добавляем информацию о пользователе в request state
            request.state.user_id = payload.get("user_id")
            request.state.user_role = payload.get("role", "user")
            request.state.token_exp = payload.get("exp")
            
            logger.info(f"Аутентификация успешна для пользователя {request.state.user_id}")
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Истекший токен для пути {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"}
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Некорректный токен для пути {request.url.path}: {e}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"}
            )
        except Exception as e:
            logger.error(f"Ошибка аутентификации для пути {request.url.path}: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication error"}
            )
            
        return await call_next(request)


def create_jwt_token(user_id: int, role: str = "user", expires_hours: int = 24) -> str:
    """Создает JWT токен для пользователя."""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow(),
        "iss": "sferatc-bot"
    }
    
    token = jwt.encode(payload, os.getenv("JWT_SECRET_KEY", "change-this-secret-key"), algorithm="HS256")
    logger.info(f"Создан JWT токен для пользователя {user_id} с ролью {role}")
    return token


def verify_jwt_token(token: str) -> Optional[dict]:
    """Проверяет и декодирует JWT токен."""
    try:
        payload = jwt.decode(
            token, 
            os.getenv("JWT_SECRET_KEY", "change-this-secret-key"), 
            algorithms=["HS256"]
        )
        return payload
    except Exception as e:
        logger.error(f"Ошибка верификации токена: {e}")
        return None