from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.routes import bind
from app.core.config import settings
from app.db.store import Store
from app.services.events import EventBus
from app.services.run_manager import RunManager

store = Store(settings.db_path)
events = EventBus(settings.run_root)
manager = RunManager(store, events)

# ensure default presets
try:
    store.upsert_preset("basic", {"spec": "off", "desc": "no speculative"})
    store.upsert_preset("ngram", {"spec_type": "ngram", "ngram_min": 3, "ngram_max": 5, "desc": "ngram speculative (free)"})
    store.upsert_preset("mtp", {"spec_type": "mtp", "desc": "MTP draft (model-provided)"})
    store.upsert_preset("dflash", {"spec_type": "draft-dflash", "desc": "DFlash draft"})
    store.upsert_preset("coding-spec-off", {"spec": "off"})
    store.upsert_preset("coding-spec-on", {"spec_type": "ngram", "desc": "coding with speculative"})
except Exception:
    pass

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(bind(store, manager, events), prefix="/api")
