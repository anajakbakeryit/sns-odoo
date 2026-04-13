# Spec: sns_zkteco

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_zkteco` |
| PROGRESS.md task # | 4.10 |
| Phase | 4 |
| Depends on (Odoo modules) | `hr`, `hr_attendance` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#10** (บันทึกเวลาพนักงานใช้เครื่องเวลา ZKTeco แต่ข้อมูลไม่เชื่อมกับ Payroll) |
| Solution type | Custom Integration Module |
| Status | **Spec Only — Implementation Deferred** (ต้องเช็ค ZKTeco model จริงกับลูกค้า) |

---

## 2. Business Context

**AS-IS:** พนักงานสแกนนิ้ว/บัตรที่ ZKTeco → ข้อมูลอยู่ใน zk device DB → HR export Excel ทุกเดือน → copy-paste เข้า payroll sheet → error + ช้า

**TO-BE:** Odoo pull attendance data อัตโนมัติ (cron รายวัน) → ลง `hr.attendance` → คำนวณ OT + late ได้เลย

---

## 3. Functional Requirements

### 3.1 User stories
- As **HR**, ฉันต้องการเห็น attendance ของพนักงานทุกคน real-time (หรือ lag ≤ 24hr)
- As **HR**, ฉันต้องการ auto-calc OT, late, early-leave ตามกะงาน
- As **Manager**, ฉันต้องการ dashboard: จำนวนคนมา/ขาด/ลา วันนี้

### 3.2 Acceptance criteria

```gherkin
Scenario: Daily cron pulls attendance
  Given ZKTeco device มี punch events 50 รายการเมื่อวาน
  When cron sns_zkteco_sync_cron รัน (00:30 ทุกวัน)
  Then 50 punches → 25 hr.attendance records (check-in + check-out pairing)
  And พนักงานที่ไม่มีใน Odoo → warning log + skip

Scenario: Employee mapping via barcode
  Given พนักงาน ID ในเครื่อง ZKTeco = '001'
  And hr.employee.barcode = '001'
  Then punch event → hr.attendance.employee_id ถูก match ถูกคน

Scenario: Pair punch events
  Given พนักงาน A punch 08:00 (in), 17:00 (out)
  Then 1 hr.attendance record: check_in=08:00, check_out=17:00, worked_hours=8.0

Scenario: Unpaired punch → attendance with no check_out
  Given พนักงาน B punch 08:00 (in) only
  Then hr.attendance created with check_in=08:00, check_out=False
  And วันถัดไป ถ้า B punch in ใหม่ → ไม่ overwrite เก่า (leave orphan to HR to resolve)
```

---

## 4. Technical Design

### 4.1 Integration approach

**Option A (Preferred): Pull via ZKTeco SDK (pyzk library)**
- ใช้ python package `pyzk` (open source) → TCP socket connection to device (port 4370)
- Cron runs daily, pulls attlog since last sync
- No server cost, works on LAN
- ข้อเสีย: ต้อง Odoo server อยู่ใน network เดียวกับ ZKTeco

**Option B: ZKTeco Push (if device supports)**
- ZKTeco BioTime Cloud หรือบาง model push events ผ่าน HTTP
- Odoo controller รับ POST → สร้าง hr.attendance
- ข้อเสีย: ต้องเปิด public endpoint

**Decision:** ใช้ Option A — ทำ cron pull ทุก 15 นาที

### 4.2 Files
```
addons/sns_zkteco/
├── __manifest__.py
├── models/
│   ├── sns_zkteco_device.py        # device registry (IP, port, password)
│   ├── sns_zkteco_punch.py         # raw punch log (before pair)
│   ├── hr_employee.py              # add zkteco_user_id field
│   └── hr_attendance.py            # extend if needed
├── services/
│   └── zkteco_client.py            # pyzk wrapper: connect, pull, disconnect
├── wizards/
│   └── sns_zkteco_sync_wizard.py   # manual sync button
├── security/...
├── data/
│   └── ir_cron.xml                 # every 15min sync cron
└── views/...
```

### 4.3 Key models

```python
class SnsZktecoDevice(models.Model):
    _name = 'sns.zkteco.device'
    name = fields.Char(required=True)
    ip = fields.Char(required=True)
    port = fields.Integer(default=4370)
    password = fields.Char()  # device password (stored encrypted via ir.config_parameter)
    last_sync = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True)

    def action_sync(self):
        from .services.zkteco_client import ZktecoClient
        client = ZktecoClient(self.ip, self.port, self.password)
        attlogs = client.fetch_attendance(since=self.last_sync)
        self._process_attlogs(attlogs)
        self.last_sync = fields.Datetime.now()

    def _process_attlogs(self, logs):
        # pair check-in/out per user per day
        # create hr.attendance
        ...


class SnsZktecoPunch(models.Model):
    _name = 'sns.zkteco.punch'
    _description = 'Raw ZKTeco Punch Event'
    _order = 'punch_time desc'

    device_id = fields.Many2one('sns.zkteco.device')
    zk_user_id = fields.Char(required=True, index=True)
    employee_id = fields.Many2one('hr.employee', compute='_compute_employee', store=True)
    punch_time = fields.Datetime(required=True)
    punch_type = fields.Selection([('in', 'Check-in'), ('out', 'Check-out'), ('unknown', 'Unknown')])
    attendance_id = fields.Many2one('hr.attendance')  # link once paired

    _sql_constraints = [
        ('unique_punch', 'unique(device_id, zk_user_id, punch_time)', 'Duplicate punch'),
    ]
```

### 4.4 Security
- ZKTeco device password: stored in `ir.config_parameter` with restricted read
- `hr_attendance.group_hr_attendance_user` can view, `group_hr_attendance_manager` can edit

---

## 5. Test Plan

1. Connect to demo ZKTeco (or simulator) → fetch punches ✓
2. Create 10 punches across 3 employees → pair correctly → 5 attendances ✓
3. Unknown zk_user_id → log warning, skip (don't crash) ✓
4. Duplicate punch (same device + user + time) → unique constraint prevents duplicate ✓
5. Network timeout → retry 3 times then log error (no data loss) ✓
6. Manual sync button for HR ✓

---

## 6. Definition of Done

- [ ] Daily cron works without intervention
- [ ] 2 test devices verified (biometric + RFID)
- [ ] HR can view attendance in Odoo within 15min of punch
- [ ] Error log + retry mechanism
- [ ] `/qa` + `/verify` passed
- [ ] PROGRESS.md 4.10 → ✅ Done
