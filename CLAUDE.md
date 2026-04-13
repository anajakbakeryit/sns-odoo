# CLAUDE.md — Odoo 18 ERP | foilss.com

## Before Starting Any Work — Read These Files First

1. `PROGRESS.md` — สถานะงานและ dependencies
2. `AGENTS.md` — บทบาท agent และ workflow
3. `specs/<module>.md` — spec ของ module ที่กำลังทำ (ใช้ `specs/_TEMPLATE.md` เป็นต้นแบบ)

**กฎ:** ห้าม implement โดยไม่อ่าน spec ก่อน และห้ามแตะโค้ดนอกขอบเขตของงานปัจจุบัน

---

## Quick Commands (Slash Skills)

ใช้ slash command แทนการพิมพ์ prompt ยาวๆ:

| Command | ใช้เมื่อ |
|---------|---------|
| `/pm` | เริ่ม session ใหม่ — ดูว่าต้องทำอะไรต่อ |
| `/spec <module>` | เขียน technical spec ก่อน code |
| `/biz-validate <module>` | ตรวจ workflow ตรงกับ requirement ไหม |
| `/acc-validate <module>` | ตรวจบัญชี + ภาษีไทย (เรียกเมื่อ module เกี่ยวกับบัญชี) |
| `/dev <module>` | implement code (Backend + Frontend + Security ในครั้งเดียว) |
| `/qa <module>` | Code Review + Security + Test Plan ในครั้งเดียว |
| `/verify <module>` | ด่านสุดท้าย — ถ้าผ่านจึง mark ✅ Done |
| `/migrate <type>` | สร้าง migration plan |
| `/ba <feature>` | Business Analyst — เขียน user story |
| `/ui <report>` | UI/Report layout design |
| `/devops <task>` | Docker/deployment tasks |
| `/preflight <phase>` | ตรวจ dependencies ก่อนเริ่ม phase ใหม่ |

**Trigger keywords สำหรับ `/acc-validate`** — ถ้า module/feature มีคำเหล่านี้ต้องเรียกเสมอ:
`invoice`, `credit`, `tax`, `payment`, `accounting`, `journal`, `cost`, `vat`, `wht`, `ar`, `ap`

---

## Project Overview

Full Odoo 18 ERP implementation for a food packaging manufacturer (foil & paper for bakery).
- Client: foilss.com
- Odoo: 18 Community/Enterprise
- Users: 21–50
- Hosting: Cloud Server (local dev via Docker)

**Business details:** ดู memory files (`project_foilss_*.md`) — source of truth

---

## Project Structure

```
odoo-sns/
├── CLAUDE.md                 # ไฟล์นี้ — conventions + quick commands
├── AGENTS.md                 # agent team structure + workflow
├── PROGRESS.md               # สถานะงาน + dependencies
├── docker-compose.yml        # Odoo 18 + PostgreSQL 16
├── odoo.conf                 # Odoo runtime config (addons_path, admin pwd)
├── addons/                   # Custom modules (mounted as /mnt/extra-addons)
│   └── sns_<module>/
├── specs/                    # Technical specs และ test plans
│   ├── _TEMPLATE.md          # template สำหรับ spec ใหม่
│   ├── ba_*.md               # user stories
│   ├── ui_*.md               # UI/layout design
│   ├── testplan_*.md         # test scripts
│   ├── migration_*.md        # migration plans
│   └── <module>.md           # technical specs
└── .claude/commands/         # slash skills (/pm, /dev, /qa, ...)
```

---

## Local Development

**Start/Stop:**
```bash
cd odoo-sns
docker compose up -d                      # start
docker compose down                        # stop
docker compose logs odoo -f                # tail logs
docker compose restart odoo                # restart after Python change
docker compose exec odoo bash              # shell inside container
```

**Database:**
- Default DB name: `foilss` (set in odoo.conf via `db_filter` — edit if different)
- สร้าง DB ครั้งแรก: เข้า http://localhost:8069 แล้วกรอก admin password จาก `odoo.conf` → ตั้งชื่อ DB ให้ตรงกับ `db_filter`

**Update a module:**
```bash
# Python change → restart container ก็พอ
docker compose restart odoo

# XML change only → update จาก Settings > Apps > <module> > Upgrade
# หรือผ่าน CLI:
docker compose exec odoo odoo -u <module_name> --stop-after-init -d foilss
```

**Install new module:**
1. วางโฟลเดอร์ใน `addons/sns_<module>/`
2. `docker compose restart odoo`
3. Settings > Apps > Update Apps List
4. ค้นหาชื่อ module แล้วกด Install

---

## Custom Module Structure

```
addons/sns_<module_name>/
├── __manifest__.py          # ชื่อ, version "18.0.1.0.0", depends, data
├── __init__.py
├── models/
│   ├── __init__.py
│   └── *.py
├── views/
│   └── *.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml         # (ถ้ามี record rules)
├── data/                    # (ถ้ามี default data)
├── report/                  # (ถ้ามี QWeb report)
└── static/description/
    └── icon.png
```

**Naming convention:** prefix `sns_` ทุก custom module

---

## Custom Modules to Build

| Module | Technical Name | Phase |
|--------|---------------|-------|
| SO Duplicate Detection | `sns_sale_duplicate_check` | 2 |
| Credit Limit + Block SO | `sns_credit_limit` | 3 |
| Delivery Reports (Pick List, Packing Slip, Loading Sheet, Label) | `sns_report_delivery` | 2 |
| Sales Reports (Quotation, Invoice, PO custom layout) | `sns_report_sales` | 3 |
| Manufacturing Reports (MO custom layout) | `sns_report_mfg` | 4 |
| Thai Tax Reports (ภ.พ.30, ภ.ง.ด.3/53/50ทวิ) | `sns_thai_tax_report` | 3 |
| ZKTeco Attendance Integration | `sns_zkteco` | 4 |
| LINE Notification | `sns_line_notify` | 5 |
| Executive Dashboard | `sns_dashboard` | 5 |

---

## Odoo Development Conventions

### Python
- Follow Odoo ORM patterns: always use `self.env[...]`, never raw SQL unless justified
- Use `@api.model`, `@api.depends`, `@api.onchange`, `@api.constrains` correctly
- Inherit models with `_inherit`, never redefine core models from scratch
- Use `_sql_constraints` for DB-level uniqueness
- Never bypass Odoo security — respect `check_access_rights`

### XML Views
- Unique `id` prefixed with module name: `sns_credit_limit.view_partner_form_inherit`
- Use `<xpath>` to extend existing views — never replace
- Report templates in `report/`, registered with `ir.actions.report`

### Security
- Every model needs entry in `security/ir.model.access.csv`
- Use `ir.rule` for row-level access
- No hardcoded user IDs or groups

### Reports (QWeb)
- A4 paper size default
- Barcode: `<img t-att-src="'/report/barcode/Code128/%s' % object.name"/>`

---

## Key Business Rules (source: memory/project_foilss_workflows.md)

### Sales
- SO must pass: **Duplicate Check → Credit Check → Stock Check** before Confirm
- Pricelist locked after SO approval — sales rep cannot override without manager
- **Invoice policy = Delivered Qty** (invoice ONLY after Ship step validated)

### Inventory
- Outgoing: **3-Step** Pick → Pack → Ship (mandatory, no bypass)
- Lot removal strategy: **FIFO** (set at product category level)
- Barcode scan mandatory at Pick and Pack — wrong LOT = blocked

### Accounting
- Costing method: **FIFO** (per product category)
- Multi-currency: **THB base + USD for imports**
- Exchange rate: auto from BOT or manual override

### Credit Limit
- Block new SO if outstanding AR > credit limit
- Credit Override requires manager approval
- Follow-up emails triggered on overdue invoices

---

## Thai Localization — Specifics

### Modules to install
- `l10n_th` (Thai Chart of Accounts)
- `l10n_th_accounting` (Thai accounting extensions ถ้ามีใน Enterprise)
- Custom `sns_thai_tax_report` (ภ.พ.30, ภ.ง.ด. ต่างๆ)

### Date format
- **Printed documents: DD/MM/YYYY**
- **Era: พ.ศ.** (Thai Buddhist year — convert ค.ศ. + 543 in QWeb)
- Database: stored as ค.ศ. (ISO format)

### Document numbering
- รูปแบบ: `<PREFIX>/<BE_YEAR>/<RUNNING>` เช่น `INV/2568/00001`, `SO/2568/00042`
- BE year = พ.ศ. (ค.ศ. + 543)
- Running number: 5 หลัก, reset ทุก fiscal year
- ต่อเนื่อง ห้าม skip เลข

### Tax documents
- **ใบกำกับภาษีเต็มรูปแบบ** (default) — มีเลขประจำตัวผู้เสียภาษี 13 หลัก + สาขา
- ใบกำกับภาษีอย่างย่อ — เฉพาะขายปลีก (ถ้ามี)
- ต้องแสดง: ชื่อ+ที่อยู่ผู้ขาย, TAX ID 13 หลัก, สาขา (สำนักงานใหญ่/สาขาเลขที่), วันที่, เลขที่เอกสาร, รายการ+ราคา+VAT แยกบรรทัด

### VAT
- 7% VAT standard
- ภาษีขาย (Output tax) vs ภาษีซื้อ (Input tax) — แยก account
- ภ.พ.30 รายเดือน = output - input

### Withholding Tax (WHT)
- ค่าบริการ: **3%**
- ค่าเช่า: **5%**
- ค่าขนส่ง: **1%**
- ดอกเบี้ย: **1%**
- เงินปันผล: **10%**
- ภ.ง.ด.3: ผู้รับเป็นบุคคลธรรมดา
- ภ.ง.ด.53: ผู้รับเป็นนิติบุคคล
- ภ.ง.ด.50 ทวิ: รายปี (รวมทุกประเภท)

---

## Integration Notes

### ZKTeco
- Pull attendance via ZKTeco SDK/API → `hr.attendance`
- Map ZKTeco employee ID → Odoo `hr.employee.barcode` field

### LINE Notification
- LINE Notify API (token per channel)
- Trigger: SO/PO waiting approval, overdue invoice
- Store token in `ir.config_parameter` — **NEVER hardcode**

### Barcode Scanner
- USB/Bluetooth HID mode — no driver needed, behaves as keyboard

---

## Data Migration Checklist

Migrate from Express / CD Organizer / Excel via CSV import (ใช้ `/migrate <type>`):
- [ ] `res.partner` — Customer + Supplier
- [ ] `product.template` + `product.product` — Products + BOM
- [ ] Opening balance journal entries
- [ ] `account.move` — Outstanding AR / AP
- [ ] `stock.quant` — Stock Balance (per Location + Lot)
- [ ] `hr.employee` — Employee master data

**Rule:** Test migration on staging DB first. Never import directly to production.

---

## Testing — Before Marking Done

Via `/qa` and `/verify`:
1. ✅ ทดสอบ full business flow end-to-end (ไม่ใช่แค่ unit)
2. ✅ Edge cases: zero stock, over credit limit, duplicate SO, wrong LOT scan
3. ✅ Odoo chatter log action (audit trail)
4. ✅ Security: lower-privilege user ไม่สามารถ bypass approval

---

## Memory (Persistent Across Sessions)

Memory files อยู่ที่ `~/.claude/projects/-Users-natthawat-Desktop-APP/memory/`:
- `project_odoo_foilss.md` — project overview
- `project_foilss_business.md` — ธุรกิจ, คลัง, QC, ผลิต
- `project_foilss_painpoints.md` — 13 pain points + solution mapping
- `project_foilss_workflows.md` — TO-BE workflows + approval matrix

**กฎ:** ถ้า business rule ที่เขียนใน CLAUDE.md ขัดกับ memory → **memory ถูกต้องกว่า** (source of truth)
