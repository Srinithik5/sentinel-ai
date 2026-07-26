from __future__ import annotations

from dataclasses import dataclass

from schemas.enums import Department, PrivilegeLevel, Role


@dataclass(frozen=True)
class ResourceProfile:
    primary_resources: tuple[str, ...]
    secondary_resources: tuple[str, ...]
    command_pool: dict[str, tuple[str, ...]]


GENERIC_COMMAND_POOL: tuple[str, ...] = ("login", "view", "logout", "heartbeat")


DEPARTMENT_RESOURCES: dict[Department, ResourceProfile] = {
    Department.ENGINEERING: ResourceProfile(
        primary_resources=("Git Repository", "CI/CD Pipeline", "Kubernetes Cluster"),
        secondary_resources=("Internal Wiki", "Issue Tracker", "Artifact Registry"),
        command_pool={
            "Git Repository": (
                "git_clone",
                "git_pull",
                "git_commit",
                "git_push",
                "create_branch",
                "merge_request",
            ),
            "CI/CD Pipeline": (
                "trigger_build",
                "run_tests",
                "deploy_staging",
                "deploy_production",
                "view_pipeline_logs",
            ),
            "Kubernetes Cluster": ("kubectl_get_pods", "kubectl_apply", "kubectl_logs", "kubectl_scale"),
            "Internal Wiki": ("view_page", "edit_page", "search"),
            "Issue Tracker": ("view_ticket", "create_ticket", "update_ticket", "comment"),
            "Artifact Registry": ("push_artifact", "pull_artifact", "list_versions"),
        },
    ),
    Department.HR: ResourceProfile(
        primary_resources=("HRMS", "Employee Records"),
        secondary_resources=("Payroll System", "Benefits Portal", "Recruitment Platform"),
        command_pool={
            "HRMS": ("view_employee", "update_employee", "generate_report", "search_directory"),
            "Employee Records": ("view_record", "update_record", "export_record"),
            "Payroll System": ("view_payroll", "process_payroll", "generate_payslip"),
            "Benefits Portal": ("view_benefits", "update_enrollment"),
            "Recruitment Platform": ("view_candidate", "schedule_interview", "update_status"),
        },
    ),
    Department.FINANCE: ResourceProfile(
        primary_resources=("ERP System", "Financial Reporting"),
        secondary_resources=("Accounts Payable", "Tax System", "Budget Planning"),
        command_pool={
            "ERP System": ("view_ledger", "post_journal_entry", "reconcile_account"),
            "Financial Reporting": ("generate_report", "export_report", "view_dashboard"),
            "Accounts Payable": ("view_invoice", "approve_payment", "process_payment"),
            "Tax System": ("view_filing", "submit_filing"),
            "Budget Planning": ("view_budget", "update_forecast"),
        },
    ),
    Department.IT: ResourceProfile(
        primary_resources=("Active Directory", "Server Management Console", "VPN Gateway"),
        secondary_resources=("Ticketing System", "Network Infrastructure", "Backup System"),
        command_pool={
            "Active Directory": ("view_user", "reset_password", "update_group_membership"),
            "Server Management Console": ("ssh_connect", "restart_service", "view_logs", "check_status"),
            "VPN Gateway": ("connect", "disconnect", "view_session"),
            "Ticketing System": ("view_ticket", "create_ticket", "resolve_ticket"),
            "Network Infrastructure": ("view_topology", "update_config", "check_uptime"),
            "Backup System": ("start_backup", "verify_backup", "restore_request"),
        },
    ),
    Department.OPERATIONS: ResourceProfile(
        primary_resources=("SCADA Historian", "Building Automation Controller"),
        secondary_resources=("Facility Management System", "Inventory System", "Logistics Platform"),
        command_pool={
            "SCADA Historian": ("read_tag_value", "query_trend", "acknowledge_event"),
            "Building Automation Controller": ("read_sensor", "adjust_setpoint", "view_status"),
            "Facility Management System": ("log_maintenance", "view_schedule", "update_ticket"),
            "Inventory System": ("view_stock", "update_stock", "generate_report"),
            "Logistics Platform": ("view_shipment", "update_route", "generate_manifest"),
        },
    ),
    Department.SECURITY: ResourceProfile(
        primary_resources=("SIEM Console", "Identity & Access Management"),
        secondary_resources=("Firewall Console", "Vulnerability Scanner", "Threat Intelligence Platform"),
        command_pool={
            "SIEM Console": ("query_logs", "create_alert_rule", "acknowledge_alert", "export_findings"),
            "Identity & Access Management": ("review_access", "grant_role", "revoke_role"),
            "Firewall Console": ("view_ruleset", "update_rule", "view_traffic_log"),
            "Vulnerability Scanner": ("start_scan", "view_findings", "export_report"),
            "Threat Intelligence Platform": ("query_indicator", "view_feed", "create_report"),
        },
    ),
    Department.SALES: ResourceProfile(
        primary_resources=("CRM", "Quote System"),
        secondary_resources=("Sales Analytics", "Contract Management"),
        command_pool={
            "CRM": ("view_lead", "update_opportunity", "log_activity", "search_contacts"),
            "Quote System": ("create_quote", "update_quote", "send_quote"),
            "Sales Analytics": ("view_dashboard", "export_report"),
            "Contract Management": ("view_contract", "generate_contract", "update_status"),
        },
    ),
}


DEPARTMENT_HEADCOUNT_WEIGHTS: dict[Department, float] = {
    Department.ENGINEERING: 0.30,
    Department.SALES: 0.18,
    Department.OPERATIONS: 0.15,
    Department.IT: 0.12,
    Department.FINANCE: 0.10,
    Department.HR: 0.08,
    Department.SECURITY: 0.07,
}


ROLE_DISTRIBUTION: dict[Department, dict[Role, float]] = {
    Department.ENGINEERING: {
        Role.INTERN: 0.08,
        Role.EMPLOYEE: 0.70,
        Role.MANAGER: 0.13,
        Role.ADMINISTRATOR: 0.09,
    },
    Department.HR: {
        Role.INTERN: 0.05,
        Role.EMPLOYEE: 0.80,
        Role.MANAGER: 0.13,
        Role.ADMINISTRATOR: 0.02,
    },
    Department.FINANCE: {
        Role.INTERN: 0.05,
        Role.EMPLOYEE: 0.78,
        Role.MANAGER: 0.14,
        Role.ADMINISTRATOR: 0.03,
    },
    Department.IT: {
        Role.INTERN: 0.04,
        Role.EMPLOYEE: 0.62,
        Role.MANAGER: 0.12,
        Role.ADMINISTRATOR: 0.22,
    },
    Department.OPERATIONS: {
        Role.INTERN: 0.03,
        Role.EMPLOYEE: 0.75,
        Role.MANAGER: 0.15,
        Role.ADMINISTRATOR: 0.07,
    },
    Department.SECURITY: {
        Role.INTERN: 0.02,
        Role.EMPLOYEE: 0.58,
        Role.MANAGER: 0.15,
        Role.ADMINISTRATOR: 0.25,
    },
    Department.SALES: {
        Role.INTERN: 0.06,
        Role.EMPLOYEE: 0.76,
        Role.MANAGER: 0.16,
        Role.ADMINISTRATOR: 0.02,
    },
}


ROLE_PRIVILEGE_MAP: dict[Role, PrivilegeLevel] = {
    Role.INTERN: PrivilegeLevel.LOW,
    Role.EMPLOYEE: PrivilegeLevel.STANDARD,
    Role.MANAGER: PrivilegeLevel.ELEVATED,
    Role.ADMINISTRATOR: PrivilegeLevel.ADMIN,
    Role.SERVICE_ACCOUNT: PrivilegeLevel.ELEVATED,
}


DEPARTMENT_WORKING_HOURS: dict[Department, tuple[int, int]] = {
    Department.ENGINEERING: (9, 18),
    Department.HR: (9, 17),
    Department.FINANCE: (8, 17),
    Department.IT: (7, 19),
    Department.OPERATIONS: (0, 24),
    Department.SECURITY: (0, 24),
    Department.SALES: (8, 18),
}


DEPARTMENT_ACTIVE_DAYS: dict[Department, tuple[int, ...]] = {
    Department.OPERATIONS: (0, 1, 2, 3, 4, 5, 6),
    Department.SECURITY: (0, 1, 2, 3, 4, 5, 6),
}


@dataclass(frozen=True)
class ServiceAccountTemplate:
    purpose: str
    department: Department
    resource: str
    schedule: str  # "nightly" | "business_hours_bursts" | "continuous"


SERVICE_ACCOUNT_TEMPLATES: tuple[ServiceAccountTemplate, ...] = (
    ServiceAccountTemplate("CI/CD Pipeline Runner", Department.ENGINEERING, "CI/CD Pipeline", "business_hours_bursts"),
    ServiceAccountTemplate("Nightly Backup Job", Department.IT, "Backup System", "nightly"),
    ServiceAccountTemplate("Database Sync Service", Department.IT, "Server Management Console", "continuous"),
    ServiceAccountTemplate("ERP Batch Processor", Department.FINANCE, "ERP System", "nightly"),
    ServiceAccountTemplate("SIEM Log Forwarder", Department.SECURITY, "SIEM Console", "continuous"),
    ServiceAccountTemplate("HRMS Sync Agent", Department.HR, "HRMS", "nightly"),
)


EDGE_DEVICE_TYPES: tuple[str, ...] = (
    "Building Automation Controller",
    "Network Edge Gateway",
    "PLC Gateway",
    "Video Surveillance Node",
)

IOT_DEVICE_TYPES: tuple[str, ...] = (
    "HVAC Sensor",
    "Occupancy Sensor",
    "Environmental Monitor",
    "Access Control Reader",
    "Asset Tracking Tag",
)