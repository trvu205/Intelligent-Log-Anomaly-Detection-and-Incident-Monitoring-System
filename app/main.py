from time import perf_counter, sleep
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.logging_config import setup_logger


app = FastAPI(
    title="Intelligent Log Monitoring - Part 1",
    description="Ứng dụng FastAPI mẫu dùng để sinh log.",
    version="1.0.0",
)

logger = setup_logger()


class LoginRequest(BaseModel):
    username: str
    password: str


class OrderRequest(BaseModel):
    product_id: int
    quantity: int


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Ghi log cho mọi HTTP request đi qua hệ thống."""

    request_id = str(uuid4())
    start_time = perf_counter()

    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        "request_started request_id=%s method=%s path=%s client_ip=%s",
        request_id,
        request.method,
        request.url.path,
        client_ip,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - start_time) * 1000

        logger.exception(
            "request_failed request_id=%s method=%s path=%s "
            "client_ip=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            client_ip,
            duration_ms,
        )
        raise

    duration_ms = (perf_counter() - start_time) * 1000

    logger.info(
        "request_finished request_id=%s method=%s path=%s "
        "status_code=%s client_ip=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        client_ip,
        duration_ms,
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def home():
    logger.info("home_page_accessed")
    return {
        "message": "Intelligent Log Monitoring System is running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    logger.info("health_check status=healthy")
    return {"status": "healthy"}


@app.post("/login")
def login(data: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    # Tài khoản giả lập để tạo log đăng nhập.
    if data.username == "admin" and data.password == "123456":
        logger.info(
            "login_success username=%s client_ip=%s",
            data.username,
            client_ip,
        )
        return {"message": "Đăng nhập thành công"}

    logger.warning(
        "login_failed username=%s client_ip=%s reason=invalid_credentials",
        data.username,
        client_ip,
    )
    raise HTTPException(
        status_code=401,
        detail="Sai tên đăng nhập hoặc mật khẩu",
    )


@app.get("/slow-api")
def slow_api():
    """Mô phỏng API phản hồi chậm."""

    sleep(3)
    logger.warning("slow_api_detected duration_ms=3000")
    return {"message": "API phản hồi sau 3 giây"}


@app.get("/database-error")
def database_error():
    """Mô phỏng lỗi kết nối cơ sở dữ liệu."""

    logger.error(
        "database_connection_failed database=monitoring_db reason=timeout"
    )
    raise HTTPException(
        status_code=500,
        detail="Không thể kết nối cơ sở dữ liệu",
    )


@app.post("/orders")
def create_order(data: OrderRequest):
    if data.quantity <= 0:
        logger.warning(
            "invalid_order product_id=%s quantity=%s",
            data.product_id,
            data.quantity,
        )
        raise HTTPException(
            status_code=400,
            detail="Số lượng sản phẩm phải lớn hơn 0",
        )

    logger.info(
        "order_created product_id=%s quantity=%s",
        data.product_id,
        data.quantity,
    )

    return {
        "message": "Tạo đơn hàng thành công",
        "product_id": data.product_id,
        "quantity": data.quantity,
    }
