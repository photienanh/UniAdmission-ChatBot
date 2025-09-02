from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import threading

from database import check_login
from database.schema import User
from backend.schema import AdminKaggleRequest, AdminKaggleApproval, AdminKaggleServer
from .utils import CommonResponse

router = APIRouter()

# Dependency để check admin role
async def require_admin(request: Request) -> User:
    user = await check_login(request, role="admin")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# In-memory storage (trong thực tế nên dùng database)
pending_requests = {}
approved_servers = {}
request_history = {}
blocked_servers = set()  # Danh sách server_id bị block

class AdminManager:
    @staticmethod
    def submit_request(server_id: str, request_type: str, data: dict) -> str:
        """Submit request mới từ Kaggle worker"""
        request_id = f"{request_type}_{uuid.uuid4().hex[:8]}"
        
        request_data = {
            "request_id": request_id,
            "server_id": server_id,
            "request_type": request_type,
            "data": data,
            "submitted_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "status": "pending",
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        pending_requests[request_id] = request_data
        return request_id
    
    @staticmethod
    def get_pending_requests() -> List[dict]:
        """Lấy tất cả requests đang pending"""
        requests = []
        current_time = datetime.now()
        
        for request_id, data in pending_requests.items():
            # Check if expired
            if datetime.fromisoformat(data["expires_at"]) < current_time:
                data["status"] = "expired"
            requests.append(data)
        
        return sorted(requests, key=lambda x: x["submitted_at"], reverse=True)
    
    @staticmethod
    def approve_request(request_id: str, admin_notes: str = "", admin_user: str = "") -> bool:
        """Approve một request"""
        if request_id not in pending_requests:
            return False
        
        data = pending_requests[request_id]
        data["status"] = "approved"
        data["admin_notes"] = admin_notes
        data["approved_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data["approved_by"] = admin_user
        
        # Move to history
        request_history[request_id] = data
        
        # Add to approved servers if it's a registration
        if data["request_type"] == "server_registration":
            server_info = {
                "server_id": data["server_id"],
                "approved_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "approved_by": admin_user,
                "approved_packages": data["data"].get("requested_packages", []),
                "contact_info": data["data"].get("contact_info", ""),
                "reason": data["data"].get("reason", "")
            }
            approved_servers[data["server_id"]] = server_info
        
        # Remove from pending
        del pending_requests[request_id]
        return True
    
    @staticmethod
    def reject_request(request_id: str, admin_notes: str = "", admin_user: str = "") -> bool:
        """Reject một request"""
        if request_id not in pending_requests:
            return False
        
        data = pending_requests[request_id]
        data["status"] = "rejected"
        data["admin_notes"] = admin_notes
        data["rejected_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data["rejected_by"] = admin_user
        
        # Move to history
        request_history[request_id] = data
        
        # Remove from pending
        del pending_requests[request_id]
        return True
    
    @staticmethod
    def is_server_approved(server_id: str) -> bool:
        """Check xem server đã được approve chưa"""
        result = server_id in approved_servers
        return result
    
    @staticmethod
    def is_server_blocked(server_id: str) -> bool:
        """Check xem server có bị block không"""
        return server_id in blocked_servers
    
    @staticmethod
    def remove_and_block_server(server_id: str, admin_user: str = "", reason: str = "Removed by admin") -> bool:
        """Xóa server khỏi approved list và block nó"""
        # Xóa khỏi approved servers
        removed = False
        if server_id in approved_servers:
            del approved_servers[server_id]
            removed = True
        
        # Thêm vào blocked list
        blocked_servers.add(server_id)
        
        # Log việc remove và block
        block_record = {
            "server_id": server_id,
            "action": "removed_and_blocked",
            "blocked_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "blocked_by": admin_user,
            "reason": reason
        }
        request_history[f"block_{server_id}_{int(datetime.now().timestamp())}"] = block_record
        
        return removed

    @staticmethod
    def is_package_allowed(server_id: str, package_name: str) -> bool:
        """Check xem server có được phép tải package này không"""
        if not AdminManager.is_server_approved(server_id):
            return False
        
        approved_packages = approved_servers[server_id].get("approved_packages", [])
        return package_name in approved_packages or "all" in approved_packages
    
    @staticmethod
    def get_approved_servers() -> List[dict]:
        """Lấy danh sách servers đã được approve"""
        return list(approved_servers.values())
    
    @staticmethod
    def _process_health_response(response, url: str) -> dict:
        """Helper function để xử lý health check response"""
        response_text = response.text.strip()
        
        # Thử parse JSON trước
        try:
            data = response.json()
            if data.get("status") == "ok":
                return {
                    "status": "healthy", 
                    "response_time": response.elapsed.total_seconds(),
                    "url": url,
                    "response_type": "json"
                }
        except:
            # Nếu không phải JSON, check string response
            # Case 1: Plain string "ok"
            if response_text.lower() == "ok":
                return {
                    "status": "healthy", 
                    "response_time": response.elapsed.total_seconds(),
                    "url": url,
                    "response_type": "string_ok"
                }
            
            # Case 2: String contains JSON-like data
            if ('"status":"ok"' in response_text or 
                "ok" in response_text.lower()):
                return {
                    "status": "healthy", 
                    "response_time": response.elapsed.total_seconds(),
                    "url": url,
                    "response_type": "string_contains_ok",
                    "raw_response": response_text[:100]  # First 100 chars for debug
                }
        
        return None  # Không healthy

    @staticmethod
    def check_server_health(server_id: str) -> dict:
        """Kiểm tra health của một server"""
        try:
            import requests
            
            # Tạo URL với https
            url = f"https://{server_id}/health" if not server_id.startswith("http") else f"{server_id}/health"
            
            # Headers để bypass ngrok warning và giả lập browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'ngrok-skip-browser-warning': 'true',  # Skip ngrok warning page
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Thử HTTPS trước
            try:
                response = requests.get(url, headers=headers, timeout=10, verify=False)
                if response.status_code == 200:
                    result = AdminManager._process_health_response(response, url)
                    if result:
                        return result
            except Exception as https_error:
                # Nếu HTTPS fail, thử HTTP
                http_url = url.replace("https://", "http://")
                try:
                    response = requests.get(http_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        result = AdminManager._process_health_response(response, http_url)
                        if result:
                            return result
                except Exception as http_error:
                    return {
                        "status": "unhealthy", 
                        "error": f"Both HTTPS and HTTP failed. HTTPS: {str(https_error)[:100]}, HTTP: {str(http_error)[:100]}"
                    }
                    
        except Exception as e:
            return {"status": "unhealthy", "error": f"Unexpected error: {str(e)[:100]}"}
            
        return {"status": "unhealthy", "error": "No successful response received"}
    
    @staticmethod
    def cleanup_unhealthy_servers() -> List[str]:
        """Xóa các server không healthy khỏi approved list"""
        unhealthy_servers = []
        
        for server_id in list(approved_servers.keys()):
            health = AdminManager.check_server_health(server_id)
            if health["status"] == "unhealthy":
                # Log việc xóa server
                removal_record = {
                    "server_id": server_id,
                    "action": "auto_removed_unhealthy",
                    "removed_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "reason": "Server health check failed",
                    "server_info": approved_servers[server_id]
                }
                request_history[f"auto_removal_{server_id}_{int(datetime.now().timestamp())}"] = removal_record
                
                # Xóa khỏi approved servers
                del approved_servers[server_id]
                unhealthy_servers.append(server_id)
                
        return unhealthy_servers

# Admin Dashboard APIs
@router.get("/dashboard")
async def get_admin_dashboard(admin: User = Depends(require_admin)):
    """Lấy tổng quan dashboard"""
    pending = AdminManager.get_pending_requests()
    approved = AdminManager.get_approved_servers()
    
    stats = {
        "total_pending": len([r for r in pending if r["status"] == "pending"]),
        "total_approved": len(approved),
        "total_requests": len(pending),
        "total_expired": len([r for r in pending if r["status"] == "expired"])
    }
    
    return CommonResponse(200, True, "Dashboard data retrieved", {
        "stats": stats,
        "pending_requests": pending,
        "approved_servers": approved
    })

@router.get("/requests")
async def get_pending_requests(admin: User = Depends(require_admin)):
    """Lấy danh sách requests đang pending"""
    try:
        requests = AdminManager.get_pending_requests()
        response = CommonResponse(200, True, "Pending requests retrieved", {"requests": requests})
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str, 
    approval_data: AdminKaggleApproval,
    admin: User = Depends(require_admin)
):
    """Approve một request"""
    success = AdminManager.approve_request(
        request_id, 
        approval_data.admin_notes, 
        admin.username
    )
    
    if success:
        return CommonResponse(200, True, f"Request {request_id} approved successfully")
    else:
        return CommonResponse(404, False, "Request not found")

@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: str, 
    rejection_data: AdminKaggleApproval,
    admin: User = Depends(require_admin)
):
    """Reject một request"""
    success = AdminManager.reject_request(
        request_id, 
        rejection_data.admin_notes, 
        admin.username
    )
    
    if success:
        return CommonResponse(200, True, f"Request {request_id} rejected successfully")
    else:
        return CommonResponse(404, False, "Request not found")

@router.get("/servers")
async def get_approved_servers(admin: User = Depends(require_admin)):
    """Lấy danh sách servers đã được approve"""
    servers = AdminManager.get_approved_servers()
    return CommonResponse(200, True, "Approved servers retrieved", servers)

@router.post("/servers/health-check")
async def check_all_servers_health(admin: User = Depends(require_admin)):
    """Check health của tất cả approved servers"""
    results = {}
    for server_id in approved_servers.keys():
        results[server_id] = AdminManager.check_server_health(server_id)
    
    return CommonResponse(200, True, "Health check completed", results)

@router.post("/servers/cleanup-unhealthy")
async def cleanup_unhealthy_servers(admin: User = Depends(require_admin)):
    """Xóa các server không healthy"""
    removed_servers = AdminManager.cleanup_unhealthy_servers()
    
    return CommonResponse(200, True, f"Removed {len(removed_servers)} unhealthy servers", {
        "removed_servers": removed_servers,
        "count": len(removed_servers)
    })

@router.get("/servers/{server_id}/health")
async def check_single_server_health(server_id: str, admin: User = Depends(require_admin)):
    """Check health của một server cụ thể"""
    if server_id not in approved_servers:
        return CommonResponse(404, False, "Server not found")
    
    health = AdminManager.check_server_health(server_id)
    return CommonResponse(200, True, "Health check completed", health)

@router.get("/history")
async def get_request_history(admin: User = Depends(require_admin)):
    """Lấy lịch sử các requests đã xử lý"""
    history = list(request_history.values())
    history.sort(key=lambda x: x.get("approved_at", x.get("rejected_at", "")), reverse=True)
    
    return CommonResponse(200, True, "Request history retrieved", history)

# Public APIs cho Kaggle workers
@router.post("/kaggle/request-access")
async def request_access(request_data: AdminKaggleRequest, request: Request):
    """API để Kaggle workers submit request"""
    
    # Check if server is blocked
    if AdminManager.is_server_blocked(request_data.server_id):
        return CommonResponse(403, False, "Server is blocked from accessing this system")
    
    data = {
        "requested_packages": request_data.requested_packages,
        "reason": request_data.reason,
        "contact_info": request_data.contact_info,
        "ngrok_url": getattr(request_data, 'ngrok_url', ''),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "client_ip": request.client.host if request.client else "unknown"
    }
    
    request_id = AdminManager.submit_request(
        request_data.server_id, 
        request_data.request_type, 
        data
    )
    
    return CommonResponse(200, True, "Request submitted successfully", {
        "request_id": request_id,
        "status": "pending"
    })

@router.get("/kaggle/check-status/{server_id}")
async def check_server_status(server_id: str):
    """Check trạng thái approval của server"""
    
    # Check if server is blocked first
    if AdminManager.is_server_blocked(server_id):
        return CommonResponse(403, False, "Server is blocked from accessing this system")
    
    # Kiểm tra xem server đã được approve chưa
    if AdminManager.is_server_approved(server_id):
        server_info = approved_servers[server_id]
        
        # Tìm thông tin chi tiết từ request history để lấy admin_notes
        approval_details = None
        for request_id, request_data in request_history.items():
            if (request_data.get("server_id") == server_id and 
                request_data.get("status") == "approved"):
                approval_details = request_data
                break
        
        response_data = {
            "status": "approved",
            "approved_packages": server_info.get("approved_packages", []),
            "approved_at": server_info.get("approved_at"),
            "approved_by": server_info.get("approved_by")
        }
        
        # Thêm admin_notes nếu có từ request history
        if approval_details:
            response_data["admin_notes"] = approval_details.get("admin_notes", "")
            response_data["request_id"] = request_id
        
        return CommonResponse(200, True, "Server approved", response_data)
    
    # Kiểm tra trong pending requests
    for request_id, request_data in pending_requests.items():
        if request_data.get("server_id") == server_id:
            return CommonResponse(200, True, "Request pending", {
                "status": "pending",
                "request_id": request_id,
                "contact_admin": "pvtatienanh@gmail.com",
                "message": "Your request is pending admin approval"
            })
    
    # Kiểm tra trong request history (rejected requests)
    for request_id, request_data in request_history.items():
        if request_data.get("server_id") == server_id:
            if request_data.get("status") == "rejected":
                return CommonResponse(200, True, "Server rejected", {
                    "status": "rejected",
                    "request_id": request_id,
                    "admin_notes": request_data.get("admin_notes", "No reason provided"),
                    "rejected_at": request_data.get("rejected_at"),
                    "rejected_by": request_data.get("rejected_by")
                })
    
    # Nếu không tìm thấy thông tin gì
    return CommonResponse(200, True, "Server not found", {
        "status": "not_found",
        "contact_admin": "pvtatienanh@gmail.com",
        "message": "Please submit a request for approval"
    })

@router.get("/kaggle/download/{package_name}")
async def download_package(package_name: str, server_id: str):
    """Protected endpoint để download packages"""
    if not AdminManager.is_package_allowed(server_id, package_name):
        raise HTTPException(
            status_code=403, 
            detail=f"Server {server_id} not approved to download {package_name}"
        )
    
    # Redirect to actual download endpoint
    return CommonResponse(200, True, "Package access granted", {
        "download_url": f"/script/{package_name}",
        "server_id": server_id
    })

# Background health monitoring
def start_health_monitoring():
    """Bắt đầu monitoring health của servers mỗi 10 phút"""
    def health_check_worker():
        while True:
            try:
                if len(approved_servers) > 0:  # Chỉ check khi có servers
                    AdminManager.cleanup_unhealthy_servers()
                # Nếu không có servers thì không log gì
            except Exception as e:
                pass
            
            # Chờ 10 phút (600 seconds)
            import time
            time.sleep(600)
    
    # Chạy trong background thread
    health_thread = threading.Thread(target=health_check_worker, daemon=True)
    health_thread.start()

# Khởi động health monitoring khi import module
start_health_monitoring()

# Admin endpoints để quản lý servers
@router.delete("/servers/{server_id}")
async def remove_and_block_server(server_id: str, admin: User = Depends(require_admin)):
    """Xóa server khỏi approved list và block nó vĩnh viễn"""
    success = AdminManager.remove_and_block_server(server_id, admin.username, "Permanently removed and blocked by admin")
    
    if success:
        return CommonResponse(200, True, f"Server {server_id} has been permanently removed and blocked")
    else:
        return CommonResponse(404, False, "Server not found in approved list, but has been blocked")
