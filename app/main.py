import io
from pathlib import Path

import qrcode
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import (
    CATEGORIES,
    LOCATIONS,
    STATUSES,
    asset_exists_by_code,
    asset_filters,
    create_asset,
    create_history_record,
    create_inventory_record,
    dashboard_summary,
    export_assets_csv,
    export_assets_xlsx,
    get_asset,
    import_assets,
    init_db,
    list_asset_history,
    list_assets,
    list_inventory_records,
    today_iso,
    update_asset,
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

STATUS_LABELS = {
    "In Service": "在用",
    "Maintenance": "维护中",
    "Retired": "已退役",
    "Spare": "备用",
}

INVENTORY_OUTCOME_LABELS = {
    "Matched": "已匹配",
    "Location Verified": "位置已确认",
    "Needs Review": "待复核",
}

EVENT_TYPE_LABELS = {
    "created": "新建",
    "status_change": "状态变更",
    "maintenance": "维护记录",
    "inventory": "盘点记录",
    "status_note": "状态备注",
    "note": "备注",
}

app = FastAPI(title="IT/OT Asset Management Demo")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


def render(request: Request, template_name: str, context: dict) -> HTMLResponse:
    base = {
        "request": request,
        "filters_meta": asset_filters(),
        "today": today_iso(),
        "status_labels": STATUS_LABELS,
        "inventory_outcome_labels": INVENTORY_OUTCOME_LABELS,
        "event_type_labels": EVENT_TYPE_LABELS,
    }
    base.update(context)
    return templates.TemplateResponse(template_name, base)


def validate_asset_payload(asset_id: str, asset_name: str, category: str, location: str, owner: str, status: str, last_inventory_date: str, notes: str) -> tuple[dict, list[str]]:
    payload = {
        "asset_id": asset_id.strip(),
        "asset_name": asset_name.strip(),
        "category": category.strip(),
        "location": location.strip(),
        "owner": owner.strip(),
        "status": status.strip(),
        "last_inventory_date": last_inventory_date.strip(),
        "notes": notes.strip(),
    }
    errors: list[str] = []
    for key, label in [("asset_id", "Asset ID"), ("asset_name", "Asset Name"), ("owner", "负责人"), ("notes", "备注")]:
        if not payload[key]:
            errors.append(f"{label}不能为空。")
    if payload["category"] not in CATEGORIES:
        errors.append("资产分类不合法。")
    if payload["location"] not in LOCATIONS:
        errors.append("所属位置不合法。")
    if payload["status"] not in STATUSES:
        errors.append("资产状态不合法。")
    return payload, errors


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    return render(request, "dashboard.html", {"summary": dashboard_summary()})


@app.get("/assets", response_class=HTMLResponse)
def asset_list(request: Request, q: str = "", category: str = "", status: str = "", location: str = "") -> HTMLResponse:
    filters = {"q": q, "category": category, "status": status, "location": location}
    return render(request, "assets.html", {"assets": list_assets(filters), "query": filters})


@app.get("/assets/new", response_class=HTMLResponse)
def asset_new(request: Request) -> HTMLResponse:
    return render(request, "asset_form.html", {"mode": "create", "errors": [], "form": {"last_inventory_date": today_iso(), "status": "In Service"}})


@app.post("/assets/new", response_class=HTMLResponse)
def asset_create(
    request: Request,
    asset_id: str = Form(...),
    asset_name: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    owner: str = Form(...),
    status: str = Form(...),
    last_inventory_date: str = Form(...),
    notes: str = Form(...),
) -> HTMLResponse:
    payload, errors = validate_asset_payload(asset_id, asset_name, category, location, owner, status, last_inventory_date, notes)
    if not errors and asset_exists_by_code(payload["asset_id"]):
        errors.append("Asset ID 已存在。")
    if errors:
        return render(request, "asset_form.html", {"mode": "create", "errors": errors, "form": payload})
    asset_pk = create_asset(payload)
    return RedirectResponse(url=f"/assets/{asset_pk}", status_code=303)


@app.get("/assets/{asset_pk}", response_class=HTMLResponse)
def asset_detail(request: Request, asset_pk: int) -> HTMLResponse:
    asset = get_asset(asset_pk)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return render(
        request,
        "asset_detail.html",
        {
            "asset": asset,
            "inventory_records": list_inventory_records(asset_pk),
            "history_records": list_asset_history(asset_pk),
            "asset_url": str(request.base_url).rstrip("/") + f"/assets/{asset_pk}",
        },
    )


@app.get("/assets/{asset_pk}/edit", response_class=HTMLResponse)
def asset_edit(request: Request, asset_pk: int) -> HTMLResponse:
    asset = get_asset(asset_pk)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return render(request, "asset_form.html", {"mode": "edit", "errors": [], "form": asset, "asset_pk": asset_pk})


@app.post("/assets/{asset_pk}/edit", response_class=HTMLResponse)
def asset_update(
    request: Request,
    asset_pk: int,
    asset_id: str = Form(...),
    asset_name: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    owner: str = Form(...),
    status: str = Form(...),
    last_inventory_date: str = Form(...),
    notes: str = Form(...),
) -> HTMLResponse:
    existing = get_asset(asset_pk)
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")
    payload, errors = validate_asset_payload(asset_id, asset_name, category, location, owner, status, last_inventory_date, notes)
    if not errors and asset_exists_by_code(payload["asset_id"], exclude_id=asset_pk):
        errors.append("Asset ID 已存在。")
    if errors:
        return render(request, "asset_form.html", {"mode": "edit", "errors": errors, "form": {**payload, "id": asset_pk}, "asset_pk": asset_pk})
    update_asset(asset_pk, payload, existing["status"])
    return RedirectResponse(url=f"/assets/{asset_pk}", status_code=303)


@app.get("/assets/{asset_pk}/qr")
def asset_qr(request: Request, asset_pk: int) -> Response:
    asset = get_asset(asset_pk)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    target_url = str(request.base_url).rstrip("/") + f"/assets/{asset_pk}"
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@app.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request) -> HTMLResponse:
    return render(request, "inventory.html", {"assets": list_assets({}), "inventory_records": list_inventory_records(), "messages": []})


@app.post("/inventory", response_class=HTMLResponse)
def inventory_create(
    request: Request,
    asset_pk: int = Form(...),
    inventory_date: str = Form(...),
    outcome: str = Form(...),
    counted_location: str = Form(...),
    notes: str = Form(...),
) -> HTMLResponse:
    asset = get_asset(asset_pk)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    create_inventory_record(asset_pk, inventory_date, outcome, counted_location, notes.strip())
    return RedirectResponse(url="/inventory", status_code=303)


@app.post("/assets/{asset_pk}/history", response_class=HTMLResponse)
def history_create(
    asset_pk: int,
    event_type: str = Form(...),
    notes: str = Form(...),
    event_date: str = Form(...),
) -> RedirectResponse:
    asset = get_asset(asset_pk)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    create_history_record(asset_pk, event_type, notes.strip(), event_date=event_date)
    return RedirectResponse(url=f"/assets/{asset_pk}", status_code=303)


@app.get("/import-export", response_class=HTMLResponse)
def import_export_page(request: Request) -> HTMLResponse:
    return render(request, "import_export.html", {"import_summary": None})


@app.post("/import-export/import", response_class=HTMLResponse)
async def import_assets_page(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    content = await file.read()
    try:
        summary = import_assets(file.filename or "", content)
        return render(request, "import_export.html", {"import_summary": summary})
    except ValueError as exc:
        return render(request, "import_export.html", {"import_summary": {"imported": 0, "skipped": [str(exc)]}})


@app.get("/import-export/export.csv")
def export_csv() -> StreamingResponse:
    data = export_assets_csv()
    return StreamingResponse(io.BytesIO(data), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=assets-export.csv"})


@app.get("/import-export/export.xlsx")
def export_xlsx() -> StreamingResponse:
    data = export_assets_xlsx()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=assets-export.xlsx"},
    )
