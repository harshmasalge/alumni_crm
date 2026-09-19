const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'iitgn_crm_token';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — requests just go unauthenticated */
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_superuser: boolean;
  roles: string[];
  permissions: string[];
}

export const api = {
  auth: {
    async login(email: string, password: string): Promise<{ access_token: string }> {
      const body = new URLSearchParams();
      body.set('username', email);
      body.set('password', password);
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
      }
      const data = (await res.json()) as { access_token: string };
      setToken(data.access_token);
      return data;
    },
    logout() {
      setToken(null);
    },
    me: () => request<AuthUser>('/auth/me'),
  },
  constituents: {
    search: (params: { q?: string; roll_no?: string; kind?: string; status?: string; page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params.q) sp.set('q', params.q);
      if (params.roll_no) sp.set('roll_no', params.roll_no);
      if (params.kind) sp.set('kind', params.kind);
      if (params.status) sp.set('status', params.status);
      if (params.page) sp.set('page', String(params.page));
      if (params.page_size) sp.set('page_size', String(params.page_size));
      return request<{ items: Constituent[]; total: number; page: number; page_size: number; total_pages: number }>(
        `/constituents?${sp.toString()}`
      );
    },

    getStaleCount: (thresholdDays = 365) =>
      request<{ count: number; threshold_days: number }>(`/constituents/stale-profiles-count?threshold_days=${thresholdDays}`),

    getStaleProfiles: (params: { threshold_days?: number; page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params.threshold_days) sp.set('threshold_days', String(params.threshold_days));
      if (params.page) sp.set('page', String(params.page));
      if (params.page_size) sp.set('page_size', String(params.page_size));
      return request<{ items: Constituent[]; total: number; page: number; page_size: number; total_pages: number }>(
        `/constituents/stale-profiles?${sp.toString()}`
      );
    },

    getProfile360: (id: string) =>
      request<Profile360>(`/constituents/${id}/profile`),

    searchOrganisations: (params: { q: string; page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      sp.set('q', params.q);
      if (params.page) sp.set('page', String(params.page));
      if (params.page_size) sp.set('page_size', String(params.page_size));
      return request<{ items: OrganisationSearchResult[]; total: number; page: number; page_size: number; total_pages: number }>(
        `/constituents/organisations/search?${sp.toString()}`
      );
    },

    addEducation: (constituentId: string, payload: {
      education_stage: string;
      qualification: string;
      institution_name: string;
      board_or_university?: string;
      field_of_study?: string;
      start_year?: number;
      completion_year?: number;
      grade_or_cgpa?: string;
      remarks?: string;
    }) =>
      request<EducationRecord>(`/constituents/${constituentId}/education`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    updateConstituent: (constituentId: string, payload: { display_name?: string; status?: string; notes?: string | null }) =>
      request<Constituent>(`/constituents/${constituentId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),

    updatePerson: (constituentId: string, payload: {
      first_name?: string; full_name?: string; gender?: string;
      date_of_birth?: string; blood_group?: string; spouse_name?: string;
    }) =>
      request<Person>(`/constituents/${constituentId}/person`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),

    updateAlumniProfile: (constituentId: string, payload: {
      iitgn_email?: string; year_of_graduation?: number; final_cpi?: number;
      thesis_title?: string; thesis_defence_date?: string;
      jee_air?: number; gate_air?: number; jam_air?: number; csir_net_rank?: number;
    }) =>
      request<AlumniProfile>(`/constituents/${constituentId}/alumni-profile`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),

    addContactMethod: (constituentId: string, payload: { contact_type: string; value: string }) =>
      request<ContactMethod>(`/constituents/${constituentId}/contact-methods`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    addAddress: (constituentId: string, payload: {
      address_type: string; line1: string; city?: string; country?: string;
    }) =>
      request<Address>(`/constituents/${constituentId}/addresses`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    setCommunicationPreferences: (constituentId: string, payload: {
      email_opt_in: boolean; whatsapp_opt_in: boolean; sms_opt_in: boolean; global_dnc: boolean;
    }) =>
      request<CommunicationPreferences>(`/constituents/${constituentId}/communication-preferences`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),

    addChildRecord: (constituentId: string, slug: string, payload: Record<string, unknown>) =>
      request<Record<string, unknown>>(`/constituents/${constituentId}/${slug}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    uploadPhotos: async (constituentId: string, files: FileList | File[]): Promise<ProfilePhoto[]> => {
      const form = new FormData();
      for (const f of Array.from(files)) form.append('files', f, f.name);
      const token = getToken();
      const res = await fetch(`${API_BASE}/constituents/${constituentId}/photos`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
      }
      return res.json();
    },

    getPhotoContent: async (constituentId: string, photoId: string): Promise<Blob> => {
      const token = getToken();
      const res = await fetch(`${API_BASE}/constituents/${constituentId}/photos/${photoId}/content`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
      }
      return res.blob();
    },

    setPhotoPrimary: (constituentId: string, photoId: string) =>
      request<ProfilePhoto>(`/constituents/${constituentId}/photos/${photoId}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_primary: true }),
      }),

    deletePhoto: async (constituentId: string, photoId: string): Promise<void> => {
      const token = getToken();
      const res = await fetch(`${API_BASE}/constituents/${constituentId}/photos/${photoId}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok && res.status !== 204) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
      }
    },

    addAffiliation: (constituentId: string, payload: {
      organisation_name_raw?: string;
      affiliation_type?: string;
      sector?: string;
      designation?: string;
      city?: string;
      state?: string;
      country?: string;
      start_date?: string;
      end_date?: string;
      is_current?: boolean;
    }) =>
      request<Affiliation>(`/constituents/${constituentId}/affiliations`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },
  admin: {
    listUsers: (params: { q?: string; page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params.q) sp.set('q', params.q);
      if (params.page) sp.set('page', String(params.page));
      if (params.page_size) sp.set('page_size', String(params.page_size));
      return request<PaginatedAdminUsers>(`/admin/users?${sp.toString()}`);
    },
    createUser: (payload: { email: string; full_name: string; role_ids?: string[]; is_superuser?: boolean }) =>
      request<AdminUser>('/admin/users', { method: 'POST', body: JSON.stringify(payload) }),
    updateUser: (id: string, payload: { full_name?: string; is_active?: boolean; is_superuser?: boolean }) =>
      request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    setUserRoles: (id: string, role_ids: string[]) =>
      request<AdminUser>(`/admin/users/${id}/roles`, { method: 'PUT', body: JSON.stringify({ role_ids }) }),
    listRoles: () => request<AdminRole[]>('/admin/roles'),
    createRole: (payload: { name: string; description?: string }) =>
      request<AdminRole>('/admin/roles', { method: 'POST', body: JSON.stringify(payload) }),
    setRolePermissions: (id: string, permission_ids: string[]) =>
      request<AdminRole>(`/admin/roles/${id}/permissions`, { method: 'PUT', body: JSON.stringify({ permission_ids }) }),
    listPermissions: () => request<AdminPermission[]>('/admin/permissions'),
    listAuditEvents: (params: { entity_type?: string; action?: string; page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params.entity_type) sp.set('entity_type', params.entity_type);
      if (params.action) sp.set('action', params.action);
      if (params.page) sp.set('page', String(params.page));
      if (params.page_size) sp.set('page_size', String(params.page_size));
      return request<PaginatedAuditEvents>(`/admin/audit-events?${sp.toString()}`);
    },
  },
};

export interface Constituent {
  id: string;
  kind: 'PERSON' | 'ORGANISATION';
  status: 'ACTIVE' | 'DECEASED' | 'LOST_CONTACT' | 'OPTED_OUT' | 'ARCHIVED';
  display_name: string;
  normalised_display_name: string;
  notes: string | null;
  profile_completeness_percent: number;
  last_substantive_profile_update_at: string | null;
  days_since_profile_update: number | null;
  created_at: string;
  updated_at: string;
}

export interface Person {
  constituent_id: string;
  first_name: string;
  full_name: string;
  gender: 'MALE' | 'FEMALE' | 'OTHER' | 'PREFER_NOT_TO_SAY' | null;
  date_of_birth: string | null;
  blood_group: string | null;
  spouse_name: string | null;
  profile_photo_file_id: string | null;
}

export interface AlumniProfile {
  constituent_id: string;
  roll_no: string;
  iitgn_email: string | null;
  programme_id: string | null;
  discipline_id: string | null;
  year_of_graduation: number | null;
  final_cpi: number | null;
  thesis_title: string | null;
  thesis_defence_date: string | null;
  thesis_supervisor_id: string | null;
  thesis_co_supervisor_id: string | null;
  jee_air: number | null;
  gate_air: number | null;
  jam_air: number | null;
  csir_net_rank: number | null;
  created_at: string;
  updated_at: string;
}

export interface DonorProfile {
  constituent_id: string;
  donor_id: string;
  pan_encrypted: string | null;
  pan_last_four: string | null;
  aadhaar_encrypted: string | null;
  created_at: string;
  updated_at: string;
}

export interface EducationRecord {
  id: string;
  constituent_id: string;
  education_stage: 'PRE_IITGN' | 'IITGN' | 'POST_IITGN';
  qualification: string;
  institution_name: string;
  board_or_university: string | null;
  field_of_study: string | null;
  start_year: number | null;
  completion_year: number | null;
  grade_or_cgpa: string | null;
  remarks: string | null;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface Affiliation {
  id: string;
  constituent_id: string;
  organisation_id: string | null;
  organisation_name_raw: string | null;
  affiliation_type: 'PRIVATE' | 'GOVERNMENT' | 'ACADEMIC' | 'STARTUP' | 'OTHER' | null;
  sector: string | null;
  designation: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  date_precision: 'DAY' | 'MONTH' | 'YEAR' | 'UNKNOWN';
  source: 'STAFF' | 'PORTAL' | 'IMPORT' | 'VERIFIED_SOURCE';
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactMethod {
  id: string;
  constituent_id: string;
  contact_type: string;
  value: string;
  normalised_value: string;
  is_primary: boolean;
  is_verified: boolean;
  whatsapp_linked: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Address {
  id: string;
  constituent_id: string;
  address_type: 'CURRENT' | 'PERMANENT';
  line1: string;
  line2: string | null;
  line3: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommunicationPreferences {
  constituent_id: string;
  email_opt_in: boolean;
  whatsapp_opt_in: boolean;
  sms_opt_in: boolean;
  global_dnc: boolean;
  consent_source: string | null;
  consent_time: string | null;
  updated_at: string;
}

export interface FileRecord {
  id: string;
  constituent_id: string;
  storage_key: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  scan_status: string;
  classification: string | null;
  uploaded_by: string | null;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  constituent_id: string | null;
  actor_id: string | null;
  actor_type: string;
  ip_address: string | null;
  request_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  before_state: string | null;
  after_state: string | null;
  created_at: string;
}

export interface ChildRecord {
  id: string;
  constituent_id: string;
  created_at: string;
}

export interface HostelHistory extends ChildRecord {
  hostel_name: string;
  room_number: string | null;
  academic_year: string | null;
  semester: string | null;
}

export interface AcademicCourse extends ChildRecord {
  programme_level: string;
  course_code: string;
  course_name: string | null;
  credits: number | null;
  year: number | null;
  semester: string | null;
  instructor: string | null;
  grade: string | null;
}

export interface SemesterPerformance extends ChildRecord {
  programme_level: string;
  year: number | null;
  semester: string | null;
  spi: number | null;
  cpi: number | null;
}

export interface GpsAssignment extends ChildRecord {
  year: number | null;
  semester: string | null;
  coordinator_name: string | null;
}

export interface AwardRecognition extends ChildRecord {
  award_type: string;
  award_date: string | null;
  agency: string | null;
  details: string | null;
  academic_year: string | null;
  semester: string | null;
}

export interface ScholarshipAid extends ChildRecord {
  aid_type: string | null;
  name: string;
  year: number | null;
  amount: number | null;
  remarks: string | null;
}

export interface Internship extends ChildRecord {
  scope: string | null;
  format: string | null;
  duration_text: string | null;
  organisation: string | null;
  year: number | null;
  funding_source: string | null;
  funding_amount: number | null;
}

export interface Placement extends ChildRecord {
  scope: string | null;
  company: string | null;
  sector: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  ctc: number | null;
  date_of_joining: string | null;
}

export interface Startup extends ChildRecord {
  startup_name: string;
  startup_type: string | null;
  incubator: string | null;
  founders: string | null;
  year: number | null;
  team_size: number | null;
  sector: string | null;
  location: string | null;
  website: string | null;
}

export interface SsacRecord extends ChildRecord {
  incident_details: string | null;
  sanction_letter_date: string | null;
  attachment_storage_key: string | null;
}

export interface PositionOfResponsibility extends ChildRecord {
  title: string;
  domain: string | null;
  academic_year: string | null;
}

export interface Publication extends ChildRecord {
  title: string;
  doi: string | null;
  pub_date: string | null;
  attachment_storage_key: string | null;
}

export interface OverseasExposure extends ChildRecord {
  organisation: string | null;
  year: number | null;
  start_date: string | null;
  end_date: string | null;
  funding_details: string | null;
  funding_amount: number | null;
}

export interface FamilyMember extends ChildRecord {
  name: string;
  relation: string | null;
  contact_number: string | null;
  email: string | null;
}

export interface ProfilePhoto {
  id: string;
  constituent_id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  position: number;
  is_primary: boolean;
  created_at: string;
}

export interface Profile360 {
  constituent: Constituent;
  person: Person | null;
  organisation: { constituent_id: string; legal_name: string; normalised_name: string; sector: string | null; website_url: string | null } | null;
  alumni_profile: AlumniProfile | null;
  donor_profile: DonorProfile | null;
  contact_methods: ContactMethod[];
  addresses: Address[];
  communication_preferences: CommunicationPreferences | null;
  education_records: EducationRecord[];
  affiliations: Affiliation[];
  files: FileRecord[];
  audit_events: AuditEvent[];
  hostel_history: HostelHistory[];
  academic_courses: AcademicCourse[];
  semester_performance: SemesterPerformance[];
  gps_assignments: GpsAssignment[];
  awards_recognition: AwardRecognition[];
  scholarships_financial_aid: ScholarshipAid[];
  internships: Internship[];
  placements: Placement[];
  startups: Startup[];
  ssac_records: SsacRecord[];
  positions_of_responsibility: PositionOfResponsibility[];
  publications: Publication[];
  overseas_exposure: OverseasExposure[];
  family_members: FamilyMember[];
  profile_photos: ProfilePhoto[];
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
}

export interface PaginatedAdminUsers {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminRole {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
  created_at: string;
}

export interface AdminPermission {
  id: string;
  name: string;
  description: string | null;
  module: string;
  action: string;
}

export interface PaginatedAuditEvents {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface OrganisationSearchResult {
  constituent_id: string;
  display_name: string;
  roll_no: string | null;
  affiliation_status: string;
  organisation_name: string;
  designation: string | null;
  start_date: string | null;
  end_date: string | null;
}