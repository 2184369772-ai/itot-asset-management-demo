# itot-asset-management-demo

Public reimplementation of an IT/OT asset management system using synthetic data.

> This repository is a public reimplementation using synthetic data.
> It contains no proprietary code, internal data, confidential materials, or company-specific assets.

`itot-asset-management-demo` is a FastAPI + SQLite portfolio demo that shows how a paper / Excel-based asset ledger can be turned into a runnable IT/OT asset management system.

中文简介：
这是一个面向作品集展示的 IT/OT 资产管理系统 Demo，重点展示“纸质 / Excel 台账如何被系统化”为可运行的资产管理界面与基础业务闭环。

English summary:
This demo shows how a paper / Excel asset ledger can be reworked into a lightweight, runnable IT/OT asset management system for portfolio presentation.

## V1 scope

- Dashboard
- Asset ledger
- Create / edit / search / filter assets
- Asset categories
- Asset status management
- Location / owner
- QR code generation
- QR links to asset detail page
- Inventory records
- Simple maintenance / status history
- Excel / CSV import and export
- Synthetic seed data

## Core story

Paper / Excel  
-> Runnable IT/OT Asset Management System

## Asset fields

- Asset ID
- Asset Name
- Category
- Location
- Owner
- Status
- Last Inventory Date
- Notes

## Synthetic demo data

The demo includes only fictional examples such as:

- categories like `Laptop`, `Server`, `PLC`, `Industrial PC`, `Network Switch`, `Sensor`, `Gateway`
- statuses like `In Service`, `Maintenance`, `Retired`, `Spare`
- locations like `Factory Alpha`, `Workshop A`, `Lab B`, `Office C`
- synthetic assets, owners, lifecycle notes, and inventory records

No real device names, real IPs, real serial numbers, real asset IDs, real organization structures, or internal Excel files are included.

## Tech stack

- Python 3.11
- FastAPI
- SQLite
- Jinja2
- Tailwind CDN

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Repository safety statement

This repository is a public reimplementation using synthetic data.
It contains no proprietary code, internal data, confidential materials, or company-specific assets.
