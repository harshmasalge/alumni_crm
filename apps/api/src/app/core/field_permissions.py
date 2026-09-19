from typing import Set
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Permission, RolePermission, UserRole


RESTRICTED_FIELDS = {
    "constituent": {
        "notes": ["constituents.read_internal"],
    },
    "person": {
        "gender": ["people.read_demographics"],
        "date_of_birth": ["people.read_demographics"],
        "blood_group": ["people.read_health"],
        "spouse_name": ["people.read_family"],
    },
    "alumni_profile": {
        "final_cpi": ["alumni.read_academic"],
        "jee_air": ["alumni.read_academic"],
        "gate_air": ["alumni.read_academic"],
        "jam_air": ["alumni.read_academic"],
        "csir_net_rank": ["alumni.read_academic"],
        "thesis_title": ["alumni.read_academic"],
        "thesis_defence_date": ["alumni.read_academic"],
        "thesis_supervisor_id": ["alumni.read_academic"],
        "thesis_co_supervisor_id": ["alumni.read_academic"],
    },
    "donor_profile": {
        "pan_encrypted": ["donors.read_finance"],
        "pan_last_four": ["donors.read_finance"],
        "aadhaar_encrypted": ["donors.read_finance"],
    },
    "contact_method": {
        "value": ["contacts.read_pii"],
        "normalised_value": ["contacts.read_pii"],
    },
    "address": {
        "line1": ["addresses.read_pii"],
        "line2": ["addresses.read_pii"],
        "line3": ["addresses.read_pii"],
        "postal_code": ["addresses.read_pii"],
    },
}


class FieldPermissionChecker:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._user_permissions_cache: dict[UUID, Set[str]] = {}

    async def get_user_permissions(self, user_id: UUID) -> Set[str]:
        if user_id in self._user_permissions_cache:
            return self._user_permissions_cache[user_id]

        result = await self.db.execute(
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, RolePermission.role_id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        perms = set(result.scalars().all())
        self._user_permissions_cache[user_id] = perms
        return perms

    def can_access_field(
        self,
        entity_type: str,
        field_name: str,
        user_permissions: Set[str],
        is_superuser: bool = False,
    ) -> bool:
        if is_superuser:
            return True
        if entity_type not in RESTRICTED_FIELDS:
            return True
        if field_name not in RESTRICTED_FIELDS[entity_type]:
            return True
        required_perms = RESTRICTED_FIELDS[entity_type][field_name]
        return any(p in user_permissions for p in required_perms)

    # Restricted fields that are required by the response schema cannot be
    # dropped without breaking validation; mask them instead so the shape
    # stays intact while the sensitive value is withheld.
    MASKED_FIELDS = {
        ("contact_method", "value"),
        ("contact_method", "normalised_value"),
        ("address", "line1"),
    }
    MASK = "[restricted]"

    def filter_dict(
        self,
        entity_type: str,
        data: dict,
        user_permissions: Set[str],
        is_superuser: bool = False,
    ) -> dict:
        if is_superuser:
            return data
        if entity_type not in RESTRICTED_FIELDS:
            return data
        restricted = RESTRICTED_FIELDS[entity_type]
        out: dict = {}
        for k, v in data.items():
            if k not in restricted or any(p in user_permissions for p in restricted[k]):
                out[k] = v
            elif (entity_type, k) in self.MASKED_FIELDS:
                out[k] = self.MASK
            # else: drop optional restricted fields entirely
        return out

    def filter_list(
        self,
        entity_type: str,
        items: list[dict],
        user_permissions: Set[str],
        is_superuser: bool = False,
    ) -> list[dict]:
        return [self.filter_dict(entity_type, item, user_permissions, is_superuser) for item in items]


async def get_field_checker(db: AsyncSession) -> FieldPermissionChecker:
    return FieldPermissionChecker(db)
