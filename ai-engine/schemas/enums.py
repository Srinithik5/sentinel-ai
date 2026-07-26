from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    EDGE_DEVICE = "edge_device"
    IOT_DEVICE = "iot_device"


class Department(str, Enum):
    ENGINEERING = "Engineering"
    HR = "HR"
    FINANCE = "Finance"
    IT = "IT"
    OPERATIONS = "Operations"
    SECURITY = "Security"
    SALES = "Sales"


class Role(str, Enum):
    INTERN = "Intern"
    EMPLOYEE = "Employee"
    MANAGER = "Manager"
    ADMINISTRATOR = "Administrator"
    SERVICE_ACCOUNT = "Service Account"


class PrivilegeLevel(str, Enum):
    LOW = "low"
    STANDARD = "standard"
    ELEVATED = "elevated"
    ADMIN = "admin"


class AuthMethod(str, Enum):
    PASSWORD = "password"
    MFA = "mfa"
    SSO = "sso"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    BIOMETRIC = "biometric"


class LoginResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class EventLabel(str, Enum):
    NORMAL = "normal"